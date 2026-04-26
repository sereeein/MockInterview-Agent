from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(__file__).parent.parent / "configs" / "rubrics"
CATEGORIES = ["T1", "T2", "T3", "T4", "T5"]


@lru_cache
def load_rubric(category: str) -> dict[str, Any]:
    if category not in CATEGORIES:
        raise ValueError(f"unknown category {category}")
    fname = {
        "T1": "t1_star.yaml",
        "T2": "t2_quant.yaml",
        "T3": "t3_jd_align.yaml",
        "T4": "t4_structured.yaml",
        "T5": "t5_motivation.yaml",
    }[category]
    return yaml.safe_load((CONFIG_DIR / fname).read_text(encoding="utf-8"))


def all_rubrics() -> dict[str, dict[str, Any]]:
    return {c: load_rubric(c) for c in CATEGORIES}
