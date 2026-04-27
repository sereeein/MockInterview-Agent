"""Run the full evaluation suite over pairs.yaml.

Usage:
    cd backend && env -u VIRTUAL_ENV uv run python ../eval/run_eval.py

Env vars:
    ANTHROPIC_API_KEY   — required (for the LLM-as-judge "ruler")
    MOCK_PROVIDER       — agent-under-test provider (default: anthropic)
    MOCK_API_KEY        — agent provider key (default: same as ANTHROPIC_API_KEY when MOCK_PROVIDER=anthropic)
    MOCK_MODEL          — override default model
    MOCK_BASE_URL       — override default base_url (only relevant for OpenAI-compat providers / custom)

Example for testing how the agent performs with DeepSeek:
    ANTHROPIC_API_KEY=sk-ant-...
    MOCK_PROVIDER=deepseek
    MOCK_API_KEY=sk-deepseek-...
    cd backend && env -u VIRTUAL_ENV uv run python ../eval/run_eval.py
"""
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path

import yaml
from anthropic import Anthropic
from rich.console import Console

# Allow importing backend
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "backend" / "src"))

from mockinterview.agent.question_gen import generate_questions  # noqa: E402
from mockinterview.agent.drill_eval import evaluate_and_followup  # noqa: E402
from mockinterview.agent.rubrics import load_rubric  # noqa: E402
from mockinterview.schemas.drill import TranscriptTurn  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from judges import relevance, drilling, baseline_compare  # noqa: E402
from simulators import user_simulator  # noqa: E402

console = Console()
HERE = Path(__file__).parent
DATA = HERE / "datasets"
OUT = HERE / "reports"
OUT.mkdir(exist_ok=True)


def parse_resume_text(text: str) -> dict:
    """Convert plaintext resume → structured dict via Claude.
    Reuses production prompt for apples-to-apples eval."""
    from mockinterview.agent.client import build_cached_system, call_json
    from mockinterview.agent.prompts.resume_parse import (
        RESUME_PARSE_SYSTEM,
        RESUME_PARSE_USER_TEMPLATE,
    )

    return call_json(
        system_blocks=build_cached_system([RESUME_PARSE_SYSTEM]),
        messages=[
            {"role": "user", "content": RESUME_PARSE_USER_TEMPLATE.replace("{resume_text}", text)}
        ],
        max_tokens=4096,
    )


def run_pair(client: Anthropic, pair: dict) -> dict:
    resume_text = (DATA / "resumes" / pair["resume"]).read_text(encoding="utf-8")
    jd_text = (
        (DATA / "jds" / pair["jd"]).read_text(encoding="utf-8") if pair["jd"] else None
    )

    console.print(f"[bold]→ pair {pair['id']}[/bold] (role={pair['role']}, jd={'yes' if jd_text else 'no'})")

    try:
        structured = parse_resume_text(resume_text)
    except Exception as e:
        console.print(f"  [red]parse_resume failed: {e}[/red]")
        return {
            "pair": pair["id"], "n_questions": 0, "relevance_scores": [],
            "relevance_avg": 0.0, "drill_hits": [], "drill_hit_rate": None,
            "baseline_we_won": None, "fatal_error": f"parse_resume: {e}",
        }

    try:
        qlist = generate_questions(
            role=pair["role"],
            resume_json=structured,
            jd_text=jd_text,
            company_name=None,
        )
    except Exception as e:
        console.print(f"  [red]generate_questions failed: {e}[/red]")
        return {
            "pair": pair["id"], "n_questions": 0, "relevance_scores": [],
            "relevance_avg": 0.0, "drill_hits": [], "drill_hit_rate": None,
            "baseline_we_won": None, "fatal_error": f"generate_questions: {e}",
        }

    # Relevance scoring on every question
    rel_scores = []
    for q in qlist.questions:
        try:
            s = relevance.score_question(
                client,
                resume=resume_text,
                jd=jd_text or "",
                question={"text": q.text, "category": q.category, "source": q.source},
            )
            rel_scores.append(s["score"])
        except Exception as e:
            console.print(f"  [yellow]relevance score failed: {e}[/yellow]")

    # Drilling: run 3 simulated U-loops on T1 questions, judge each followup
    t1_qs = [q for q in qlist.questions if q.category == "T1"][:3]
    drill_hits = []
    drill_total = 0
    for q in t1_qs:
        transcript: list[TranscriptTurn] = [TranscriptTurn(role="agent", text=q.text, round=0)]
        for round_i in range(2):  # 2 followups per question max
            try:
                sim_text = user_simulator.simulate_answer(
                    client,
                    resume=resume_text,
                    question=q.text,
                    transcript=[t.model_dump() for t in transcript],
                )
            except Exception as e:
                console.print(f"  [yellow]simulator failed: {e}[/yellow]")
                break
            transcript.append(TranscriptTurn(role="user", text=sim_text, round=round_i + 1))
            try:
                ev = evaluate_and_followup(
                    category=q.category,
                    question_text=q.text,
                    transcript=transcript,
                )
            except Exception as e:
                console.print(f"  [yellow]eval failed: {e}[/yellow]")
                break
            rubric = load_rubric(q.category)
            try:
                judge = drilling.judge_followup(
                    client,
                    question=q.text,
                    rubric_dims=rubric["dimensions"],
                    last_answer=sim_text,
                    followup=ev.next_followup,
                )
                drill_hits.append(1 if judge["hit_weakest"] else 0)
                drill_total += 1
            except Exception as e:
                console.print(f"  [yellow]drilling judge failed: {e}[/yellow]")
            transcript.append(
                TranscriptTurn(role="agent", text=ev.next_followup, round=round_i + 1)
            )
            if ev.total_score >= 9:
                break

    # Baseline comparison on the FIRST T1 question
    ours_won = None
    if t1_qs:
        ours_pair = {"question": t1_qs[0].text, "first_followup": ""}
        transcript_for_ours = [
            TranscriptTurn(role="agent", text=t1_qs[0].text, round=0),
            TranscriptTurn(role="user", text="<placeholder mid-quality answer>", round=1),
        ]
        try:
            ev = evaluate_and_followup(
                category=t1_qs[0].category,
                question_text=t1_qs[0].text,
                transcript=transcript_for_ours,
            )
            ours_pair["first_followup"] = ev.next_followup
            baseline = baseline_compare.baseline_pair(
                client, resume=resume_text, jd=jd_text or ""
            )
            a, b, ours_label = baseline_compare.shuffled_label_pair(ours_pair, baseline)
            verdict = baseline_compare.judge_blind(
                client, resume=resume_text, jd=jd_text or "", a_pair=a, b_pair=b
            )
            if verdict["winner"] == "tie":
                ours_won = None
            else:
                ours_won = verdict["winner"] == ours_label
        except Exception as e:
            console.print(f"  [yellow]baseline compare failed: {e}[/yellow]")

    return {
        "pair": pair["id"],
        "n_questions": len(qlist.questions),
        "relevance_scores": rel_scores,
        "relevance_avg": statistics.mean(rel_scores) if rel_scores else 0.0,
        "drill_hits": drill_hits,
        "drill_hit_rate": (sum(drill_hits) / drill_total) if drill_total else None,
        "baseline_we_won": ours_won,
    }


def write_report(results: list[dict]) -> Path:
    date = datetime.now().strftime("%Y-%m-%d")
    path = OUT / f"{date}.md"
    rel_avg = statistics.mean([r["relevance_avg"] for r in results]) if results else 0.0
    drill_rates = [r["drill_hit_rate"] for r in results if r["drill_hit_rate"] is not None]
    drill_avg = statistics.mean(drill_rates) if drill_rates else 0
    baseline = [r["baseline_we_won"] for r in results if r["baseline_we_won"] is not None]
    win_rate = (sum(1 for w in baseline if w) / len(baseline)) if baseline else 0

    lines = [
        f"# Eval Report — {date}",
        "",
        "## Summary",
        f"- Pairs run: {len(results)}",
        f"- Relevance avg: **{rel_avg:.2f} / 3** (target ≥ 2.2)",
        f"- Drilling hit rate: **{drill_avg:.0%}** (target ≥ 70%)",
        f"- Baseline win rate: **{win_rate:.0%}** (target ≥ 70%)",
        "",
        "## Per-pair detail",
        "",
        "| Pair | Relevance | Drill hits | Beat baseline? |",
        "| --- | --- | --- | --- |",
    ]
    for r in results:
        bl = "—" if r["baseline_we_won"] is None else ("✓" if r["baseline_we_won"] else "✗")
        dr = (
            "—"
            if r["drill_hit_rate"] is None
            else f"{r['drill_hit_rate']:.0%} ({sum(r['drill_hits'])}/{len(r['drill_hits'])})"
        )
        lines.append(f"| {r['pair']} | {r['relevance_avg']:.2f} | {dr} | {bl} |")
    lines.append("")
    lines.append("## Raw")
    lines.append("```json")
    lines.append(json.dumps(results, ensure_ascii=False, indent=2))
    lines.append("```")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _build_provider_from_env() -> "LLMProvider":
    """Read MOCK_PROVIDER / MOCK_API_KEY / MOCK_MODEL / MOCK_BASE_URL from env.
    Default: anthropic + ANTHROPIC_API_KEY (backward compat).
    """
    import os
    provider = os.environ.get("MOCK_PROVIDER", "anthropic")
    api_key = (
        os.environ.get("MOCK_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY", "")
    )
    if not api_key:
        raise SystemExit(
            "Set MOCK_API_KEY (or ANTHROPIC_API_KEY for default Anthropic) before running eval."
        )
    model = os.environ.get("MOCK_MODEL") or None
    base_url = os.environ.get("MOCK_BASE_URL") or None
    from mockinterview.agent.providers import make_provider
    return make_provider(provider=provider, api_key=api_key, model=model, base_url=base_url)


def main() -> None:
    from mockinterview.agent.providers import set_active
    set_active(_build_provider_from_env())

    pairs = yaml.safe_load((DATA / "pairs.yaml").read_text())["pairs"]
    # The judges/simulator still use a raw Anthropic client because their prompts are tuned for Claude.
    # Backend agent code (parse_resume_text, generate_questions, evaluate_and_followup) goes through the active provider.
    judge_client = Anthropic()  # judges still need ANTHROPIC_API_KEY for fair comparison
    results = [run_pair(judge_client, p) for p in pairs]
    path = write_report(results)
    console.print(f"[green]Report written[/green]: {path}")


if __name__ == "__main__":
    main()
