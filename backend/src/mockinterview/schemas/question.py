from typing import Literal

from pydantic import BaseModel, Field

Category = Literal["T1", "T2", "T3", "T4", "T5"]
Difficulty = Literal["easy", "medium", "hard"]


class GeneratedQuestion(BaseModel):
    text: str
    category: Category
    source: str
    difficulty: Difficulty


class QuestionList(BaseModel):
    questions: list[GeneratedQuestion] = Field(default_factory=list)
