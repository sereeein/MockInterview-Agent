"""Case loader: reads eval/datasets/pairs.yaml and surfaces filterable Case records."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

EVAL_ROOT = Path(__file__).resolve().parent.parent
DATASETS = EVAL_ROOT / "datasets"
PAIRS_YAML = DATASETS / "pairs.yaml"


@dataclass(frozen=True)
class Case:
    case_id: str
    role: str                                  # pm / data / ai / other
    resume_path: Path
    jd_path: Path | None
    metadata: dict[str, Any] = field(default_factory=dict)

    def resume_text(self) -> str:
        return self.resume_path.read_text(encoding="utf-8")

    def jd_text(self) -> str | None:
        return self.jd_path.read_text(encoding="utf-8") if self.jd_path else None


def load_cases(
    *,
    filter_ids: list[str] | None = None,
    filter_role: str | None = None,
    pairs_yaml: Path = PAIRS_YAML,
) -> list[Case]:
    """Load cases from pairs.yaml, optionally filtered by id and/or role.

    Filters compose by AND. Empty filter lists/None mean "no filter".
    Raises FileNotFoundError if pairs.yaml is missing or a referenced
    resume/jd file doesn't exist.
    """
    raw = yaml.safe_load(pairs_yaml.read_text(encoding="utf-8"))
    pairs = raw.get("pairs", []) if isinstance(raw, dict) else []

    cases: list[Case] = []
    for p in pairs:
        case_id = p["id"]
        if filter_ids and case_id not in filter_ids:
            continue
        if filter_role and p.get("role") != filter_role:
            continue

        resume_path = DATASETS / "resumes" / p["resume"]
        if not resume_path.exists():
            raise FileNotFoundError(f"resume not found: {resume_path}")

        jd_path: Path | None = None
        if p.get("jd"):
            jd_path = DATASETS / "jds" / p["jd"]
            if not jd_path.exists():
                raise FileNotFoundError(f"jd not found: {jd_path}")

        cases.append(
            Case(
                case_id=case_id,
                role=p["role"],
                resume_path=resume_path,
                jd_path=jd_path,
                metadata={
                    k: v for k, v in p.items()
                    if k not in {"id", "role", "resume", "jd"}
                },
            )
        )

    if filter_ids:
        missing = set(filter_ids) - {c.case_id for c in cases}
        if missing:
            raise ValueError(f"unknown case ids in --case filter: {sorted(missing)}")

    return cases
