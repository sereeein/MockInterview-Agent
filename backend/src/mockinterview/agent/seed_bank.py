from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(__file__).parent.parent / "configs" / "seed_questions"
ROLES = ["pm", "data", "ai", "other"]


@lru_cache
def load_seed_bank(role: str) -> list[dict[str, Any]]:
    if role not in ROLES:
        raise ValueError(f"unknown role {role}")
    data = yaml.safe_load((CONFIG_DIR / f"{role}.yaml").read_text(encoding="utf-8"))
    return data["questions"]
