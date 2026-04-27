from pydantic import BaseModel, Field


class DrillEvalResult(BaseModel):
    scores: dict[str, int]
    total_score: int
    weakest_dimension: str
    weakness_diagnosis: str
    next_followup: str


class TranscriptTurn(BaseModel):
    role: str  # "agent" | "user"
    text: str
    round: int
    kind: str = "normal"  # normal | scenario_switch | prompt_mode | system
