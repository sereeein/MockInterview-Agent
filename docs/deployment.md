# Deployment & Eval Guide

> User-driven steps for Tasks 4.6 (run eval), 4.7 (backend deploy), 4.8 (frontend deploy).

## Task 4.6 — Run eval

**Pre-req**: `ANTHROPIC_API_KEY` (Anthropic console).

```bash
cd /Users/evette/Documents/MockInterview_Agent
export ANTHROPIC_API_KEY=sk-ant-...
cd backend
env -u VIRTUAL_ENV uv run python ../eval/run_eval.py
```

Expect:
- 8 pairs × ~35 LLM calls = ~280 calls
- Runtime: 5-15 min
- Cost: $5-15 (with prompt caching)
- Output: `eval/reports/<YYYY-MM-DD>.md`

**If eval fails midway**: each pair is independent; partial reports still get written. Re-run = fresh report (file overwritten).

**To swap synthetic resumes/JDs with real脱敏**:
1. Replace `eval/datasets/resumes/*.txt` and `eval/datasets/jds/*.txt` with real脱敏 content (keep filenames or update `pairs.yaml`)
2. Remove `<!-- SYNTHETIC PLACEHOLDER -->` headers
3. Re-run eval

**To tune prompts**:
1. Read low-scoring pairs in the report
2. Identify which rubric / question gen / drill eval prompt seems brittle
3. Edit `backend/src/mockinterview/agent/prompts/*.py`
4. Re-run eval; compare new report to previous (commit each report so git diff helps)

## Task 4.7 — Backend deploy (Railway)

**Pre-req**: Railway account + CLI (`brew install railway`).

```bash
# Inside backend/
railway login
railway init                # creates new project
railway add                 # add a Volume mounted at /data
railway variables --set ANTHROPIC_API_KEY=sk-ant-...
railway variables --set CORS_ORIGINS='["https://<your-vercel-domain>.vercel.app"]'
railway up                  # builds + deploys via Dockerfile
```

**Backend Dockerfile** (create at `backend/Dockerfile`):

```dockerfile
FROM python:3.12-slim

# Install uv
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src ./src

ENV PATH="/app/.venv/bin:${PATH}"
ENV DB_URL="sqlite:////data/app.db"

EXPOSE 8000
CMD ["uvicorn", "mockinterview.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Backend `.dockerignore`**:

```
.venv
__pycache__
tests
.pytest_cache
data
*.log
```

**Note on `cors_origins` env**: pydantic-settings parses list types as JSON. So set:

```bash
railway variables --set CORS_ORIGINS='["https://app.vercel.app"]'
```

NOT comma-separated. If a future需求 wants comma-separated, add a `field_validator` in `config.py`.

**Verify**: `curl https://<railway-url>/health` → `{"status":"ok"}`.

## Task 4.8 — Frontend deploy (Vercel)

**Pre-req**: Vercel account + CLI (`brew install vercel`).

```bash
cd frontend
vercel login
echo "NEXT_PUBLIC_API_URL=https://<railway-url>" > .env.production.local
vercel --prod              # follow prompts; link to a new project
```

**Or via dashboard**: import repo → set `NEXT_PUBLIC_API_URL` env var → deploy.

**Update Railway CORS** to include the Vercel URL after frontend deploy:

```bash
railway variables --set CORS_ORIGINS='["https://mockinterview-agent.vercel.app"]'
```

**Verify**: open Vercel URL → upload PDF → see questions → drill → see report.

## Common pitfalls

- **Backend `data/app.db` gone after restart on Railway** — confirm Volume is attached and `DB_URL=sqlite:////data/app.db` (4 slashes = absolute path)
- **CORS errors in browser** — Railway CORS_ORIGINS must JSON-list match the frontend URL exactly (incl. https://)
- **PDF parse 500** — check ANTHROPIC_API_KEY env on Railway
- **Eval cost surprise** — verify prompt caching is hitting (Anthropic dashboard); cap eval runs to 3 pairs during prompt tuning iterations

## Cost monitoring

Anthropic dashboard: https://console.anthropic.com/usage

v1 expected costs:
- Per drill (3 followups): ~$0.05-0.10
- Full eval run (8 pairs): $5-15
- Production usage: depends on traffic; free Vercel + Railway $5/month covers low traffic
