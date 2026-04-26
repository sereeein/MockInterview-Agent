# MockInterview Agent v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, evaluate, and deploy a vertical PM/数据/AI 面试演练 agent (resume-driven question generation + 多轮追问 with场景切换 UX) in 4 weeks by 1 person.

**Architecture:** Mono repo with Python FastAPI backend (Anthropic SDK Claude 4.7 Opus, SQLModel + SQLite, hand-rolled state machine) and Next.js 16 frontend (App Router + shadcn/ui + Recharts). Backend deploys to Railway, frontend to Vercel.

**Tech Stack:** Python 3.12 + FastAPI + Anthropic SDK + SQLModel + pdfplumber + pytest / Next.js 16 + TypeScript + shadcn/ui + Tailwind + Recharts / SQLite + YAML configs / Vercel + Railway.

**Source spec:** `docs/superpowers/specs/2026-04-27-mock-interview-agent-v1-design.md`

---

## File Structure

```
MockInterview_Agent/
├── PROJECT.md
├── .gitignore
├── README.md                       # Week 4 deliverable
├── docs/superpowers/specs/         # spec lives here
├── plans/                          # this plan
├── backend/
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── .python-version             # 3.12
│   ├── Dockerfile                  # Week 4
│   ├── data/                       # SQLite file (gitignored)
│   ├── src/mockinterview/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI entry
│   │   ├── config.py               # env / settings
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── models.py           # 4 SQLModel tables
│   │   │   └── session.py          # engine + session
│   │   ├── agent/
│   │   │   ├── __init__.py
│   │   │   ├── client.py           # Anthropic client + caching
│   │   │   ├── resume_parser.py
│   │   │   ├── question_gen.py
│   │   │   ├── drill_loop.py       # state machine
│   │   │   ├── drill_eval.py       # rubric scoring + followup
│   │   │   ├── exemplar.py         # exemplar answer synth
│   │   │   ├── user_signals.py     # classify user input
│   │   │   └── prompts/
│   │   │       ├── __init__.py
│   │   │       ├── resume_parse.py
│   │   │       ├── question_gen.py
│   │   │       ├── drill_eval.py
│   │   │       ├── scenario_switch.py
│   │   │       ├── prompt_mode.py
│   │   │       ├── exemplar.py
│   │   │       └── user_signals.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── resume.py
│   │   │   ├── questions.py
│   │   │   ├── drill.py
│   │   │   ├── mock.py             # 整套面试模式
│   │   │   └── reports.py
│   │   ├── schemas/                # Pydantic API schemas
│   │   │   ├── __init__.py
│   │   │   ├── resume.py
│   │   │   ├── question.py
│   │   │   ├── drill.py
│   │   │   └── report.py
│   │   └── configs/
│   │       ├── rubrics/
│   │       │   ├── t1_star.yaml
│   │       │   ├── t2_quant.yaml
│   │       │   ├── t3_jd_align.yaml
│   │       │   ├── t4_structured.yaml
│   │       │   └── t5_motivation.yaml
│   │       └── seed_questions/
│   │           ├── pm.yaml
│   │           ├── data.yaml
│   │           ├── ai.yaml
│   │           └── other.yaml
│   └── tests/
│       ├── conftest.py
│       ├── test_resume_parser.py
│       ├── test_question_gen.py
│       ├── test_drill_eval.py
│       ├── test_drill_loop.py
│       ├── test_exemplar.py
│       ├── test_user_signals.py
│       ├── test_routes_*.py
│       └── fixtures/
│           ├── sample_resume.pdf
│           └── sample_jd.txt
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── components.json             # shadcn
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── globals.css
│   │   │   ├── page.tsx            # 首页 / 简历上传
│   │   │   ├── library/page.tsx    # 题库
│   │   │   ├── drill/[id]/page.tsx # 单题演练
│   │   │   ├── report/[id]/page.tsx# 单题报告
│   │   │   ├── mock/page.tsx       # 整套面试入口
│   │   │   └── mock/[id]/page.tsx  # 整套面试演练
│   │   ├── components/
│   │   │   ├── upload-zone.tsx
│   │   │   ├── role-selector.tsx
│   │   │   ├── question-card.tsx
│   │   │   ├── chat-interface.tsx
│   │   │   ├── radar-chart.tsx
│   │   │   ├── score-bar-chart.tsx
│   │   │   ├── transcript-view.tsx
│   │   │   ├── library-stats-bar.tsx
│   │   │   └── ui/                 # shadcn primitives
│   │   └── lib/
│   │       ├── api.ts              # fetch wrappers
│   │       └── types.ts            # TS types matching backend schemas
│   └── public/
└── eval/
    ├── pyproject.toml
    ├── datasets/
    │   ├── resumes/
    │   ├── jds/
    │   └── pairs.yaml
    ├── judges/
    │   ├── __init__.py
    │   ├── relevance.py
    │   ├── drilling.py
    │   └── baseline_compare.py
    ├── simulators/
    │   └── user_simulator.py       # LLM 模拟"中等质量"用户
    ├── run_eval.py
    └── reports/                    # gitignored
```

---

## Test Strategy

- **Backend unit tests (pytest)**: mock Anthropic client at module boundary; test state machine logic, prompt construction, DB persistence in isolation. Fast, deterministic.
- **Backend integration tests (pytest, marked `@pytest.mark.live`)**: a few representative tests hit live Claude API with `cassettes` (vcr.py) or marked `live_only` and skipped by default; run manually before commits that change prompts.
- **Frontend**: no unit tests in v1 (tight schedule). Manual e2e through full flow in Week 3 Friday.
- **Eval set as regression**: `python eval/run_eval.py` is the prompt quality gate. Run after any prompt change; compare to previous baseline report.

**Commit cadence**: every passing task = a commit. No "WIP" commits. Branches optional (single dev → commit straight to main is fine).

---

## Phase 1 / Week 1 — 基础设施 + 出题引擎

**Phase Goal**: 跑通"传 PDF 简历 → 智能解析 → 生成 12 道带元数据的题入题库"完整后端链路（无前端）。

**Phase Deliverable**: `curl -F file=@resume.pdf POST /resume` + `POST /questions/generate` 能产出题库；4 张表持久化正常。

---

### Task 1.1: Initialize backend project skeleton

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.python-version`
- Create: `backend/src/mockinterview/__init__.py`
- Create: `backend/src/mockinterview/main.py`
- Create: `backend/src/mockinterview/config.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Create pyproject.toml with uv**

```bash
cd backend
echo "3.12" > .python-version
uv init --package mockinterview --no-readme
```

Then edit `backend/pyproject.toml`:

```toml
[project]
name = "mockinterview"
version = "0.1.0"
description = "Vertical interview prep agent — backend"
requires-python = ">=3.12"
dependencies = [
  "fastapi[standard]>=0.115",
  "uvicorn>=0.32",
  "sqlmodel>=0.0.22",
  "anthropic>=0.40",
  "pdfplumber>=0.11",
  "pyyaml>=6.0",
  "python-multipart>=0.0.12",
  "pydantic-settings>=2.6",
]

[dependency-groups]
dev = [
  "pytest>=8.3",
  "pytest-asyncio>=0.24",
  "httpx>=0.28",
  "pytest-mock>=3.14",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["live: hits real Claude API (skipped by default)"]
addopts = "-v -m 'not live'"
```

- [ ] **Step 2: Write minimal main.py**

`backend/src/mockinterview/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mockinterview.config import get_settings

settings = get_settings()
app = FastAPI(title="MockInterview Agent", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

`backend/src/mockinterview/config.py`:

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    db_url: str = "sqlite:///./data/app.db"
    cors_origins: list[str] = ["http://localhost:3000"]
    claude_model: str = "claude-opus-4-7"
    seed_user_id: int = 1


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 3: conftest with TestClient**

`backend/tests/conftest.py`:

```python
import pytest
from fastapi.testclient import TestClient

from mockinterview.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
```

- [ ] **Step 4: Health test**

`backend/tests/test_health.py`:

```python
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

- [ ] **Step 5: Install + run**

```bash
cd backend
uv sync
uv run pytest tests/test_health.py
```
Expected: `1 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat(backend): scaffold FastAPI app with health endpoint"
```

---

### Task 1.2: Database models (4 tables) + session

**Files:**
- Create: `backend/src/mockinterview/db/__init__.py`
- Create: `backend/src/mockinterview/db/models.py`
- Create: `backend/src/mockinterview/db/session.py`
- Create: `backend/tests/test_db_models.py`

Schema reference: spec §10. Status enum and exit_type values are fixed.

- [ ] **Step 1: Write failing test for ResumeSession round-trip**

`backend/tests/test_db_models.py`:

```python
from datetime import datetime

from sqlmodel import Session, SQLModel, create_engine

from mockinterview.db.models import (
    DrillAttempt,
    Question,
    Report,
    ResumeSession,
    QuestionStatus,
    ExitType,
)


def test_resume_session_round_trip():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        rs = ResumeSession(
            user_id=1,
            resume_json={"basic": {"name": "Alice"}},
            jd_text="PM at ByteDance",
            company_name="ByteDance",
            role_type="pm",
        )
        s.add(rs)
        s.commit()
        s.refresh(rs)
        assert rs.id is not None
        assert rs.created_at is not None


def test_question_default_status_is_not_practiced():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        rs = ResumeSession(user_id=1, resume_json={}, role_type="pm")
        s.add(rs)
        s.commit()
        s.refresh(rs)
        q = Question(
            resume_session_id=rs.id,
            category="T1",
            text="Why this design?",
            source="反推自 项目 X",
            difficulty="medium",
        )
        s.add(q)
        s.commit()
        s.refresh(q)
        assert q.status == QuestionStatus.NOT_PRACTICED
        assert q.best_score is None


def test_drill_attempt_persists_transcript_and_scores():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        rs = ResumeSession(user_id=1, resume_json={}, role_type="pm")
        s.add(rs)
        s.commit()
        q = Question(
            resume_session_id=rs.id,
            category="T1",
            text="Q",
            source="x",
            difficulty="medium",
        )
        s.add(q)
        s.commit()
        s.refresh(q)
        d = DrillAttempt(
            question_id=q.id,
            transcript_json=[
                {"role": "agent", "text": "Q?", "round": 0},
                {"role": "user", "text": "A", "round": 1},
            ],
            rubric_scores_json={"S": 2, "T": 2, "A": 3, "R": 2},
            total_score=9,
            exit_type=ExitType.SOFT,
            scenario_switch_count=0,
            prompt_mode_count=0,
            followup_rounds=1,
            exemplar_answer="Sample answer",
            improvement_suggestions=["a", "b", "c"],
            ended_at=datetime.utcnow(),
        )
        s.add(d)
        s.commit()
        s.refresh(d)
        assert d.id is not None
        assert d.total_score == 9
```

- [ ] **Step 2: Run test (expect import errors)**

```bash
uv run pytest tests/test_db_models.py
```
Expected: ImportError on `mockinterview.db.models`.

- [ ] **Step 3: Write models**

`backend/src/mockinterview/db/models.py`:

```python
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import Column, JSON
from sqlmodel import Field, Relationship, SQLModel


class QuestionStatus(str, Enum):
    NOT_PRACTICED = "not_practiced"
    PRACTICED = "practiced"
    NEEDS_REDO = "needs_redo"
    IMPROVED = "improved"
    SKIPPED = "skipped"


class ExitType(str, Enum):
    SOFT = "soft"
    HARD_LIMIT = "hard_limit"
    USER_END = "user_end"
    SKIP = "skip"


class ResumeSession(SQLModel, table=True):
    __tablename__ = "resume_session"
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(default=1, index=True)
    resume_json: dict[str, Any] = Field(sa_column=Column(JSON))
    jd_text: str | None = None
    company_name: str | None = None
    role_type: str = Field(index=True)  # pm / data / ai / other
    created_at: datetime = Field(default_factory=datetime.utcnow)

    questions: list["Question"] = Relationship(back_populates="session")
    reports: list["Report"] = Relationship(back_populates="session")


class Question(SQLModel, table=True):
    __tablename__ = "question"
    id: int | None = Field(default=None, primary_key=True)
    resume_session_id: int = Field(foreign_key="resume_session.id", index=True)
    category: str  # T1..T5
    text: str
    source: str
    difficulty: str  # easy/medium/hard
    status: QuestionStatus = Field(default=QuestionStatus.NOT_PRACTICED, index=True)
    best_score: int | None = None
    last_attempt_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    session: ResumeSession | None = Relationship(back_populates="questions")
    attempts: list["DrillAttempt"] = Relationship(back_populates="question")


class DrillAttempt(SQLModel, table=True):
    __tablename__ = "drill_attempt"
    id: int | None = Field(default=None, primary_key=True)
    question_id: int = Field(foreign_key="question.id", index=True)
    transcript_json: list[dict[str, Any]] = Field(sa_column=Column(JSON))
    rubric_scores_json: dict[str, int] = Field(sa_column=Column(JSON))
    total_score: int
    exit_type: ExitType
    scenario_switch_count: int = 0
    prompt_mode_count: int = 0
    followup_rounds: int = 0
    exemplar_answer: str
    improvement_suggestions: list[str] = Field(sa_column=Column(JSON))
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: datetime | None = None

    question: Question | None = Relationship(back_populates="attempts")


class Report(SQLModel, table=True):
    __tablename__ = "report"
    id: int | None = Field(default=None, primary_key=True)
    resume_session_id: int = Field(foreign_key="resume_session.id", index=True)
    drill_attempt_ids: list[int] = Field(sa_column=Column(JSON))
    total_avg_score: float
    category_avg_scores: dict[str, float] = Field(sa_column=Column(JSON))
    highlights: list[dict[str, Any]] = Field(sa_column=Column(JSON))
    weaknesses: list[dict[str, Any]] = Field(sa_column=Column(JSON))
    next_steps: list[str] = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)

    session: ResumeSession | None = Relationship(back_populates="reports")
```

- [ ] **Step 4: Write session.py**

`backend/src/mockinterview/db/session.py`:

```python
from collections.abc import Iterator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from mockinterview.config import get_settings

_settings = get_settings()
Path("data").mkdir(exist_ok=True)
engine = create_engine(_settings.db_url, echo=False)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as s:
        yield s
```

- [ ] **Step 5: Wire init_db into main.py startup**

Edit `backend/src/mockinterview/main.py`, replace existing content:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mockinterview.config import get_settings
from mockinterview.db.session import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


settings = get_settings()
app = FastAPI(title="MockInterview Agent", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 6: Run all tests**

```bash
uv run pytest
```
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat(backend): SQLModel schema for resume_session/question/drill_attempt/report"
```

---

### Task 1.3: Frontend skeleton (Next.js 16 + shadcn)

**Files:**
- Create: `frontend/` (Next.js scaffold)
- Modify: `frontend/src/app/page.tsx`
- Create: `frontend/src/lib/api.ts`

- [ ] **Step 1: Bootstrap Next.js**

```bash
cd /Users/evette/Documents/MockInterview_Agent
pnpm dlx create-next-app@latest frontend \
  --typescript --tailwind --app --no-src-dir=false \
  --import-alias "@/*" --turbopack --no-eslint --use-pnpm
```

(If `--no-src-dir=false` is rejected by version, use `--src-dir`.)

- [ ] **Step 2: Init shadcn**

```bash
cd frontend
pnpm dlx shadcn@latest init -d
pnpm dlx shadcn@latest add button card input textarea label badge progress tabs dialog
```

- [ ] **Step 3: Replace homepage with placeholder**

`frontend/src/app/page.tsx`:

```tsx
export default function Home() {
  return (
    <main className="container mx-auto py-12">
      <h1 className="text-3xl font-bold">MockInterview Agent</h1>
      <p className="mt-2 text-muted-foreground">
        垂直岗位 AI 面试演练 · 简历反向挖题 · 多轮追问
      </p>
      <p className="mt-8 text-sm">
        Skeleton up. Upload page lands in Week 3.
      </p>
    </main>
  );
}
```

- [ ] **Step 4: API client stub**

`frontend/src/lib/api.ts`:

```ts
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json() as Promise<T>;
}

export async function health(): Promise<{ status: string }> {
  return api("/health");
}
```

- [ ] **Step 5: Smoke test**

```bash
# Terminal 1
cd backend && uv run uvicorn mockinterview.main:app --reload
# Terminal 2
cd frontend && pnpm dev
```
Open http://localhost:3000 — should show heading. Open http://localhost:8000/health — should show `{"status":"ok"}`.

- [ ] **Step 6: Commit**

```bash
git add frontend/ .gitignore
git commit -m "feat(frontend): Next.js 16 + shadcn scaffold + API client stub"
```

---

### Task 1.4: Anthropic client wrapper with prompt caching

**Files:**
- Create: `backend/src/mockinterview/agent/__init__.py`
- Create: `backend/src/mockinterview/agent/client.py`
- Create: `backend/tests/test_agent_client.py`

Spec §7.2 mandates prompt caching. Centralize the client so every call site benefits.

- [ ] **Step 1: Failing test for cached system prompt structure**

`backend/tests/test_agent_client.py`:

```python
from mockinterview.agent.client import build_cached_system, parse_json_response


def test_build_cached_system_marks_cache_control():
    blocks = build_cached_system(["你是面试官", "rubric: ..."])
    assert blocks[0]["type"] == "text"
    assert "你是面试官" in blocks[0]["text"]
    assert blocks[-1].get("cache_control") == {"type": "ephemeral"}


def test_parse_json_response_extracts_json_block():
    fake = '```json\n{"a": 1}\n```'
    assert parse_json_response(fake) == {"a": 1}


def test_parse_json_response_handles_raw_json():
    assert parse_json_response('{"a": 1}') == {"a": 1}
```

- [ ] **Step 2: Implement client.py**

`backend/src/mockinterview/agent/client.py`:

```python
from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from anthropic import Anthropic

from mockinterview.config import get_settings

_JSON_FENCE = re.compile(r"```(?:json)?\s*(.+?)\s*```", re.DOTALL)


@lru_cache
def get_client() -> Anthropic:
    return Anthropic(api_key=get_settings().anthropic_api_key)


def build_cached_system(parts: list[str]) -> list[dict[str, Any]]:
    """Construct a system prompt as a list of text blocks where the LAST block
    carries cache_control. This puts the static rubric/prompt context in cache
    while still allowing per-call dynamic prefixes."""
    blocks: list[dict[str, Any]] = [{"type": "text", "text": p} for p in parts]
    if blocks:
        blocks[-1]["cache_control"] = {"type": "ephemeral"}
    return blocks


def parse_json_response(text: str) -> dict[str, Any]:
    m = _JSON_FENCE.search(text)
    payload = m.group(1) if m else text
    return json.loads(payload)


def call_json(
    system_blocks: list[dict[str, Any]],
    messages: list[dict[str, Any]],
    max_tokens: int = 4096,
    model: str | None = None,
) -> dict[str, Any]:
    client = get_client()
    resp = client.messages.create(
        model=model or get_settings().claude_model,
        system=system_blocks,
        messages=messages,
        max_tokens=max_tokens,
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    return parse_json_response(text)
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest tests/test_agent_client.py
```
Expected: 3 passed.

- [ ] **Step 4: Commit**

```bash
git add backend/
git commit -m "feat(agent): Anthropic client wrapper with prompt-caching system blocks"
```

---

### Task 1.5: Resume parser (PDF → structured JSON)

**Files:**
- Create: `backend/src/mockinterview/agent/prompts/__init__.py`
- Create: `backend/src/mockinterview/agent/prompts/resume_parse.py`
- Create: `backend/src/mockinterview/agent/resume_parser.py`
- Create: `backend/src/mockinterview/schemas/__init__.py`
- Create: `backend/src/mockinterview/schemas/resume.py`
- Create: `backend/tests/test_resume_parser.py`
- Create: `backend/tests/fixtures/sample_resume.pdf` (use the developer's own resume scrubbed; for now, placeholder text PDF)

Spec §3 schema is the contract.

- [ ] **Step 1: Pydantic schemas matching spec §3**

`backend/src/mockinterview/schemas/resume.py`:

```python
from pydantic import BaseModel, Field


class Education(BaseModel):
    school: str
    degree: str
    major: str
    graduation: str


class Basic(BaseModel):
    name: str
    education: list[Education] = []


class ResumeProject(BaseModel):
    title: str
    period: str
    role: str = ""
    description: str
    outcomes: str = ""


class WorkExperience(BaseModel):
    company: str
    title: str
    period: str
    responsibilities: str
    outcomes: str = ""


class ResumeStructured(BaseModel):
    basic: Basic
    projects: list[ResumeProject] = Field(default_factory=list)
    work_experience: list[WorkExperience] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
```

- [ ] **Step 2: Resume parsing prompt**

`backend/src/mockinterview/agent/prompts/resume_parse.py`:

```python
RESUME_PARSE_SYSTEM = """你是一个简历结构化解析器。
你会收到一份简历的原始文本（可能由 PDF 抽取，含杂乱排版）。
你的任务：抽取以下 4 类字段，输出 JSON。

字段 schema：
{
  "basic": {
    "name": string,
    "education": [{"school", "degree", "major", "graduation"}]
  },
  "projects": [{"title", "period", "role", "description", "outcomes"}],
  "work_experience": [{"company", "title", "period", "responsibilities", "outcomes"}],
  "skills": [string]
}

规则：
1. 只抽取上述 4 类，不要包含证书 / 奖项 / 论文 / 语言 / 兴趣 / 推荐人
2. projects 和 work_experience 必须包含 description / responsibilities 和 outcomes 两子字段
3. 如果原简历某条经历缺 outcomes，填空字符串 ""，不要编造
4. 所有时间用原文格式，不归一化
5. 输出严格 JSON，用 ```json 代码块包裹。不要任何其他文字。"""

RESUME_PARSE_USER_TEMPLATE = """以下是简历原文：

---
{resume_text}
---

请输出结构化 JSON。"""
```

- [ ] **Step 3: Resume parser**

`backend/src/mockinterview/agent/resume_parser.py`:

```python
from io import BytesIO

import pdfplumber

from mockinterview.agent.client import build_cached_system, call_json
from mockinterview.agent.prompts.resume_parse import (
    RESUME_PARSE_SYSTEM,
    RESUME_PARSE_USER_TEMPLATE,
)
from mockinterview.schemas.resume import ResumeStructured


def extract_pdf_text(pdf_bytes: bytes) -> str:
    parts: list[str] = []
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if text:
                parts.append(text)
    return "\n\n".join(parts)


def parse_resume(pdf_bytes: bytes) -> ResumeStructured:
    text = extract_pdf_text(pdf_bytes)
    if not text.strip():
        raise ValueError("PDF text extraction returned empty")
    system = build_cached_system([RESUME_PARSE_SYSTEM])
    payload = call_json(
        system_blocks=system,
        messages=[
            {
                "role": "user",
                "content": RESUME_PARSE_USER_TEMPLATE.format(resume_text=text),
            }
        ],
        max_tokens=4096,
    )
    return ResumeStructured.model_validate(payload)
```

- [ ] **Step 4: Test with mocked client**

`backend/tests/test_resume_parser.py`:

```python
from unittest.mock import patch

import pytest

from mockinterview.agent import resume_parser
from mockinterview.schemas.resume import ResumeStructured


FAKE_RESPONSE = {
    "basic": {
        "name": "Alice Wu",
        "education": [
            {
                "school": "ABC Univ",
                "degree": "MS",
                "major": "Data Science",
                "graduation": "2025",
            }
        ],
    },
    "projects": [
        {
            "title": "User segmentation",
            "period": "2024",
            "role": "Lead",
            "description": "K-means on 10M users",
            "outcomes": "AUC 0.85",
        }
    ],
    "work_experience": [],
    "skills": ["Python", "SQL"],
}


def test_parse_resume_returns_structured(monkeypatch):
    def fake_extract(_):
        return "fake resume text"

    monkeypatch.setattr(resume_parser, "extract_pdf_text", fake_extract)
    with patch("mockinterview.agent.resume_parser.call_json", return_value=FAKE_RESPONSE):
        result = resume_parser.parse_resume(b"PDFBYTES")
    assert isinstance(result, ResumeStructured)
    assert result.basic.name == "Alice Wu"
    assert result.projects[0].outcomes == "AUC 0.85"


def test_parse_resume_empty_text_raises(monkeypatch):
    monkeypatch.setattr(resume_parser, "extract_pdf_text", lambda _: "")
    with pytest.raises(ValueError, match="empty"):
        resume_parser.parse_resume(b"PDFBYTES")
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/test_resume_parser.py
```
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat(agent): resume parser (PDF → structured JSON via Claude)"
```

---

### Task 1.6: POST /resume endpoint

**Files:**
- Create: `backend/src/mockinterview/routes/__init__.py`
- Create: `backend/src/mockinterview/routes/resume.py`
- Modify: `backend/src/mockinterview/main.py` (register router)
- Create: `backend/tests/test_routes_resume.py`

- [ ] **Step 1: Failing test**

`backend/tests/test_routes_resume.py`:

```python
import io
from unittest.mock import patch

from sqlmodel import Session, select

from mockinterview.db.models import ResumeSession
from mockinterview.db.session import engine
from mockinterview.schemas.resume import ResumeStructured

PARSED = ResumeStructured.model_validate(
    {
        "basic": {"name": "Alice", "education": []},
        "projects": [],
        "work_experience": [],
        "skills": [],
    }
)


def test_post_resume_creates_session(client):
    with patch("mockinterview.routes.resume.parse_resume", return_value=PARSED):
        r = client.post(
            "/resume",
            files={"file": ("r.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
            data={"role_type": "pm", "jd_text": "PM at X", "company_name": "X"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["role_type"] == "pm"
    assert body["resume_json"]["basic"]["name"] == "Alice"
    with Session(engine) as s:
        rows = s.exec(select(ResumeSession)).all()
    assert len(rows) >= 1
```

- [ ] **Step 2: Write router**

`backend/src/mockinterview/routes/resume.py`:

```python
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session

from mockinterview.agent.resume_parser import parse_resume
from mockinterview.config import get_settings
from mockinterview.db.models import ResumeSession
from mockinterview.db.session import get_session

router = APIRouter(prefix="/resume", tags=["resume"])

ALLOWED_ROLES = {"pm", "data", "ai", "other"}


@router.post("")
def upload_resume(
    file: UploadFile = File(...),
    role_type: str = Form(...),
    jd_text: str | None = Form(None),
    company_name: str | None = Form(None),
    db: Session = Depends(get_session),
) -> dict:
    if role_type not in ALLOWED_ROLES:
        raise HTTPException(400, f"role_type must be one of {ALLOWED_ROLES}")
    pdf_bytes = file.file.read()
    if not pdf_bytes:
        raise HTTPException(400, "empty file")
    parsed = parse_resume(pdf_bytes)
    rs = ResumeSession(
        user_id=get_settings().seed_user_id,
        resume_json=parsed.model_dump(),
        jd_text=jd_text,
        company_name=company_name,
        role_type=role_type,
    )
    db.add(rs)
    db.commit()
    db.refresh(rs)
    return {
        "id": rs.id,
        "role_type": rs.role_type,
        "resume_json": rs.resume_json,
        "jd_text": rs.jd_text,
        "company_name": rs.company_name,
    }
```

- [ ] **Step 3: Register router in main.py**

Add at top of `main.py`:

```python
from mockinterview.routes import resume as resume_routes
```

Add after `app = FastAPI(...)`:

```python
app.include_router(resume_routes.router)
```

- [ ] **Step 4: Run test**

```bash
uv run pytest tests/test_routes_resume.py
```
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/
git commit -m "feat(api): POST /resume — upload PDF, parse, persist ResumeSession"
```

---

### Task 1.7: 5 Rubric YAML configs

**Files:**
- Create: `backend/src/mockinterview/configs/rubrics/t1_star.yaml`
- Create: `backend/src/mockinterview/configs/rubrics/t2_quant.yaml`
- Create: `backend/src/mockinterview/configs/rubrics/t3_jd_align.yaml`
- Create: `backend/src/mockinterview/configs/rubrics/t4_structured.yaml`
- Create: `backend/src/mockinterview/configs/rubrics/t5_motivation.yaml`
- Create: `backend/src/mockinterview/agent/rubrics.py` (loader)
- Create: `backend/tests/test_rubrics.py`

Spec §5.1 lists each rubric's 4 dimensions.

- [ ] **Step 1: Write all 5 YAML files**

`backend/src/mockinterview/configs/rubrics/t1_star.yaml`:

```yaml
category: T1
name: STAR
description: 项目深挖类题目，按 STAR 框架评估完整度
dimensions:
  - key: situation
    label: Situation 情境
    description: 是否清晰交代项目背景、约束、问题来源
  - key: task
    label: Task 任务目标
    description: 是否明确具体目标、交付物、成功标准
  - key: action
    label: Action 行动
    description: 候选人具体做了什么、为什么这么做、考虑了哪些 trade-off
  - key: result
    label: Result 结果
    description: 量化结果、归因清晰度、复盘视角
score_levels:
  0: 完全缺失或答非所问
  1: 提及但模糊、不可落地
  2: 合格、可被理解
  3: 出色、有洞察或量化支撑
threshold_complete: 9
```

`backend/src/mockinterview/configs/rubrics/t2_quant.yaml`:

```yaml
category: T2
name: 量化严谨度
description: outcomes 追问类，考察候选人对自己声称数字的严谨程度
dimensions:
  - key: baseline
    label: Baseline 明确
    description: 是否说清对照基线（同期/历史均值/未做该改动情况）
  - key: attribution
    label: 归因清晰
    description: 把结果归因到自己的工作而非外部因素，能识别混淆变量
  - key: significance
    label: 显著性意识
    description: 提及样本量、置信度、统计或业务显著性
  - key: business_meaning
    label: 业务意义
    description: 数字翻译成业务影响（GMV、留存、决策）
score_levels:
  0: 完全缺失或答非所问
  1: 提及但模糊、不可落地
  2: 合格、可被理解
  3: 出色、有洞察或量化支撑
threshold_complete: 9
```

`backend/src/mockinterview/configs/rubrics/t3_jd_align.yaml`:

```yaml
category: T3
name: STAR + 框架
description: JD 能力对齐题，要求结合 STAR 案例与岗位框架化思考
dimensions:
  - key: case_support
    label: 案例支撑
    description: 用具体项目/经历做支撑，不空谈
  - key: framework
    label: 框架化思考
    description: 拆解维度合理、用结构化语言表达
  - key: feasibility
    label: 落地可行性
    description: 提到资源、时间、风险、依赖等约束
  - key: reflection
    label: 复盘视角
    description: 提及"如果重做会改什么"、"局限是什么"
score_levels:
  0: 完全缺失或答非所问
  1: 提及但模糊、不可落地
  2: 合格、可被理解
  3: 出色、有洞察或量化支撑
threshold_complete: 9
```

`backend/src/mockinterview/configs/rubrics/t4_structured.yaml`:

```yaml
category: T4
name: 结构化思考
description: 岗位通用题（思路题、case 题），考察结构化拆解能力
dimensions:
  - key: dimensions
    label: 拆解维度完整
    description: 拆解角度覆盖关键维度，不遗漏大块
  - key: priority
    label: 优先级合理
    description: 在多个维度间能给出优先级排序及理由
  - key: edge_cases
    label: 风险与边界
    description: 主动提及边界、异常、风险、滥用
  - key: falsifiable
    label: 可证伪
    description: 假设/结论可验证，给出验证方式
score_levels:
  0: 完全缺失或答非所问
  1: 提及但模糊、不可落地
  2: 合格、可被理解
  3: 出色、有洞察或量化支撑
threshold_complete: 9
```

`backend/src/mockinterview/configs/rubrics/t5_motivation.yaml`:

```yaml
category: T5
name: 自洽 + 真诚
description: 行为/动机题，考察自洽与真实度
dimensions:
  - key: specificity
    label: 动机具体
    description: 动机指向具体细节，不是宽泛形容词
  - key: coherence
    label: 与履历自洽
    description: 与简历、过往选择一致，不矛盾
  - key: non_cliche
    label: 非套话
    description: 不堆砌"成长机会、平台优秀"类模板
  - key: reflection
    label: 包含反思
    description: 体现自我认知或复盘
score_levels:
  0: 完全缺失或答非所问
  1: 提及但模糊、不可落地
  2: 合格、可被理解
  3: 出色、有洞察或量化支撑
threshold_complete: 9
```

- [ ] **Step 2: Loader**

`backend/src/mockinterview/agent/rubrics.py`:

```python
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
```

- [ ] **Step 3: Tests**

`backend/tests/test_rubrics.py`:

```python
from mockinterview.agent.rubrics import CATEGORIES, all_rubrics, load_rubric


def test_load_each_rubric_has_4_dimensions():
    for c in CATEGORIES:
        r = load_rubric(c)
        assert r["category"] == c
        assert len(r["dimensions"]) == 4
        assert r["threshold_complete"] == 9


def test_all_rubrics_returns_5():
    assert len(all_rubrics()) == 5
```

- [ ] **Step 4: Run + commit**

```bash
uv run pytest tests/test_rubrics.py
git add backend/
git commit -m "feat(agent): 5 rubric YAML configs (T1 STAR / T2 quant / T3 align / T4 structured / T5 motivation)"
```

---

### Task 1.8: Seed question banks (PM / 数据 / AI)

**Files:**
- Create: `backend/src/mockinterview/configs/seed_questions/pm.yaml`
- Create: `backend/src/mockinterview/configs/seed_questions/data.yaml`
- Create: `backend/src/mockinterview/configs/seed_questions/ai.yaml`
- Create: `backend/src/mockinterview/configs/seed_questions/other.yaml`
- Create: `backend/src/mockinterview/agent/seed_bank.py`
- Create: `backend/tests/test_seed_bank.py`

Each role file: ~30 questions. v1 content can be drafted by Claude itself (run `python scripts/draft_seed.py` once → curate). For now, plan defines structure + ~6 examples per role; the actual 30 each is a curation task that fits in Wed's afternoon.

- [ ] **Step 1: Define schema + first 6 PM questions**

`backend/src/mockinterview/configs/seed_questions/pm.yaml`:

```yaml
role: pm
description: PM / AI 产品类岗位通用 T4 题库种子（北极星指标、case、决策框架）
questions:
  - text: 如果让你为小红书 App 的"日活"定义北极星指标，你会怎么定？为什么？
    angle: 北极星指标定义
    difficulty: medium
  - text: 一个新功能上线后留存涨了 5%，但 GMV 跌了 3%，你怎么决策是否继续推全？
    angle: trade-off 决策
    difficulty: hard
  - text: 设计一个评估"通知推送质量"的指标体系，至少 5 个层次。
    angle: 指标体系拆解
    difficulty: medium
  - text: 用户提需求"加一个 X 按钮"，你怎么判断是否要做？给出完整决策流程。
    angle: 需求评估
    difficulty: easy
  - text: 描述一次你拒绝了高 priority 需求方的请求的经历——理由、过程、结果。
    angle: trade-off 决策 + 沟通
    difficulty: medium
  - text: 如果让你做一款给老年人的视频 App，第一个版本你会保留 / 砍掉哪 3 个功能？理由？
    angle: 用户洞察 + MVP 决策
    difficulty: hard
  # — Wed afternoon: curate to 30 total —
  # 维度覆盖：北极星 / 用户洞察 / 决策框架 / 指标拆解 / case 题 / 沟通 trade-off / MVP / GTM
```

`backend/src/mockinterview/configs/seed_questions/data.yaml`:

```yaml
role: data
description: 数据科学 / 数据分析 / ML 工程类岗位通用 T4 题库种子
questions:
  - text: 你想验证"新推荐策略提升了用户停留时长"，A/B 实验怎么设计？样本量怎么估？
    angle: 实验设计
    difficulty: medium
  - text: 一个分类模型 AUC 0.85 但线上 CTR 只升了 0.3%，可能的原因有哪些？
    angle: 模型业务对齐
    difficulty: hard
  - text: 给你一张订单表，怎么用 SQL 算"过去 30 天连续下单 3 天的用户数"？
    angle: SQL 思路
    difficulty: medium
  - text: 用户分群项目里你选 K-means，为什么不选 DBSCAN？分群质量怎么验证？
    angle: 方法选择 + 验证
    difficulty: medium
  - text: 一个 metric 在某天突然下跌 20%，你的排查流程是什么？
    angle: 异常归因
    difficulty: medium
  - text: 给"用户流失预测模型"设计监控告警，至少 5 个维度。
    angle: 模型监控
    difficulty: hard
  # — 30 total，覆盖 实验 / SQL / metric 设计 / 模型评估 / 监控 / 异常归因 —
```

`backend/src/mockinterview/configs/seed_questions/ai.yaml`:

```yaml
role: ai
description: AI 产品 / AI 工程岗 T4 题库种子
questions:
  - text: 你怎么评估一个 LLM-based 客服 agent 的"是否好用"？给出指标体系。
    angle: AI 产品评估
    difficulty: hard
  - text: 一个 RAG 系统在测试集上 recall 0.9，上线后用户反馈"答非所问" 30% 案例，可能的原因？
    angle: hallucination & 评估对齐
    difficulty: hard
  - text: 给你一个文档问答场景，你会怎么决定用 fine-tune 还是 RAG 还是 prompt engineering？
    angle: 方案选择
    difficulty: medium
  - text: 设计一个 LLM agent 的安全护栏，至少 5 个层次。
    angle: 安全 & 风险
    difficulty: hard
  - text: 数据规模化是 AI 产品最大坑之一。你做过哪个 AI 产品时遇到了数据规模化挑战？
    angle: 数据规模化
    difficulty: medium
  - text: 一个 AI 写作助手的 retention 不行，你会从哪 5 个角度排查？
    angle: AI 产品 retention
    difficulty: medium
  # — 30 total —
```

`backend/src/mockinterview/configs/seed_questions/other.yaml`:

```yaml
role: other
description: 通用兜底（非核心岗位走通用 STAR + 行为题）
questions:
  - text: 描述一次你在团队中体现领导力的经历。
    angle: 行为题
    difficulty: easy
  - text: 你最有成就感的项目是什么？为什么？
    angle: 行为题
    difficulty: easy
  - text: 描述一次你做过的最艰难的决策。
    angle: 决策 + 反思
    difficulty: medium
```

- [ ] **Step 2: Loader**

`backend/src/mockinterview/agent/seed_bank.py`:

```python
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
```

- [ ] **Step 3: Tests**

`backend/tests/test_seed_bank.py`:

```python
import pytest

from mockinterview.agent.seed_bank import ROLES, load_seed_bank


@pytest.mark.parametrize("role", ROLES)
def test_seed_bank_loads(role):
    qs = load_seed_bank(role)
    assert isinstance(qs, list)
    assert len(qs) >= 1
    assert "text" in qs[0] and "angle" in qs[0] and "difficulty" in qs[0]


def test_seed_bank_unknown_role():
    with pytest.raises(ValueError):
        load_seed_bank("biz")
```

- [ ] **Step 4: Curation note**

Add a comment at the top of each role YAML stating "curate to 30 questions before generation engine ships" — Wed afternoon's task. Acceptance criterion: each of pm/data/ai has ≥ 30 questions covering at least 6 distinct `angle` tags.

- [ ] **Step 5: Commit**

```bash
uv run pytest tests/test_seed_bank.py
git add backend/
git commit -m "feat(agent): seed question banks (pm/data/ai/other) with starter content"
```

---

### Task 1.9: Question generation engine

**Files:**
- Create: `backend/src/mockinterview/agent/prompts/question_gen.py`
- Create: `backend/src/mockinterview/agent/question_gen.py`
- Create: `backend/src/mockinterview/schemas/question.py`
- Create: `backend/tests/test_question_gen.py`

Spec §4 contract: 12 questions total, distribution {T1:4, T2:2, T3:3, T4:2, T5:1}; if no JD, T3:0 and T1+1, T2+1.

- [ ] **Step 1: Pydantic schema for generated question**

`backend/src/mockinterview/schemas/question.py`:

```python
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
```

- [ ] **Step 2: Question generation prompt**

`backend/src/mockinterview/agent/prompts/question_gen.py`:

```python
QUESTION_GEN_SYSTEM = """你是一名资深面试官 + 出题专家，专门为「{role_label}」岗位的求职者出面试题。

你的工作是基于以下 4 类素材出 {total} 道面试题：
1. 求职者简历（结构化字段：projects / work_experience / skills / education）
2. JD（如有，反推岗位关键能力）
3. 岗位类型 ({role}) 对应的种子题库（T4 通用题来源）
4. 5 类题型分布要求

题型分布：
- T1 项目深挖：{n_t1} 道（来源：projects 或 work_experience.description；考察决策依据 / trade-off / 设计动机）
- T2 outcomes 追问：{n_t2} 道（来源：work_experience.outcomes 或 projects.outcomes 的量化数据；考察 baseline / 归因 / 显著性 / 业务意义）
- T3 JD 能力对齐：{n_t3} 道（来源：JD 关键词 ✕ 简历项目；要求"以你 X 项目为例谈谈 Y 能力"）
- T4 岗位通用题：{n_t4} 道（从种子题库中精选，结合简历做轻度个性化改写）
- T5 行为/动机：{n_t5} 道（"为什么投这家"、"职业规划"等）

岗位挖题角度（{role}）：
{role_angle}

种子题库（T4 候选池）：
{seed_questions}

输出要求：严格 JSON，{total} 道题。每道题包含：
- text: 题面（中文，自然问法，不要太学术）
- category: T1/T2/T3/T4/T5
- source: 来源说明（"反推自项目 [项目名]" / "对齐 JD 关键词 [...]" / "{role} 通用题：[angle]" / 等）
- difficulty: easy/medium/hard

重要规则：
1. 题面必须具体、贴合简历，不能是"请介绍一下你的项目"这种通用问法
2. T2 题必须引用简历 outcomes 里的具体数字
3. 如果某条简历经历缺 outcomes，可出"如果让你重新写这条简历，你会怎么把结果量化？"作为 T2
4. T1 题必须挑简历中至少 4 个不同项目（避免反复挖同一项目）
5. T3 题如果 JD 缺失则不出（数量已在分布中归零）
6. 输出格式：
```json
{{"questions": [...]}}
```
"""

QUESTION_GEN_USER_TEMPLATE = """简历结构化数据：
{resume_json}

JD：
{jd_block}

公司：{company}

请按上述分布出 {total} 道题。"""


ROLE_LABEL = {
    "pm": "产品经理 / 产品运营 / AI 产品",
    "data": "数据分析 / 数据科学 / ML 工程",
    "ai": "AI 产品 / AI 工程",
    "other": "通用岗位",
}

ROLE_ANGLE = {
    "pm": "决策依据 / 北极星指标 / 用户洞察 / trade-off / GTM",
    "data": "方法严谨度 / 量化与归因 / 可解释性 / 实验设计 / SQL",
    "ai": "评估指标 / 数据规模化 / hallucination & 安全 / RAG vs fine-tune",
    "other": "通用 STAR 框架 / 行为题",
}
```

- [ ] **Step 3: Generation engine**

`backend/src/mockinterview/agent/question_gen.py`:

```python
import json

from mockinterview.agent.client import build_cached_system, call_json
from mockinterview.agent.prompts.question_gen import (
    QUESTION_GEN_SYSTEM,
    QUESTION_GEN_USER_TEMPLATE,
    ROLE_ANGLE,
    ROLE_LABEL,
)
from mockinterview.agent.seed_bank import load_seed_bank
from mockinterview.schemas.question import QuestionList


def _distribution(has_jd: bool) -> dict[str, int]:
    if has_jd:
        return {"T1": 4, "T2": 2, "T3": 3, "T4": 2, "T5": 1}
    return {"T1": 5, "T2": 3, "T3": 0, "T4": 2, "T5": 1}


def _format_seeds(role: str, n: int) -> str:
    bank = load_seed_bank(role)
    sample = bank[: max(n * 5, 12)]  # give the model >= 12 candidates to choose from
    return "\n".join(f"- ({q['angle']}, {q['difficulty']}) {q['text']}" for q in sample)


def generate_questions(
    *,
    role: str,
    resume_json: dict,
    jd_text: str | None,
    company_name: str | None,
) -> QuestionList:
    has_jd = bool(jd_text and jd_text.strip())
    dist = _distribution(has_jd)
    total = sum(dist.values())
    system = QUESTION_GEN_SYSTEM.format(
        role=role,
        role_label=ROLE_LABEL[role],
        role_angle=ROLE_ANGLE[role],
        total=total,
        n_t1=dist["T1"],
        n_t2=dist["T2"],
        n_t3=dist["T3"],
        n_t4=dist["T4"],
        n_t5=dist["T5"],
        seed_questions=_format_seeds(role, dist["T4"]),
    )
    user = QUESTION_GEN_USER_TEMPLATE.format(
        resume_json=json.dumps(resume_json, ensure_ascii=False, indent=2),
        jd_block=(jd_text or "（未提供）"),
        company=company_name or "（未提供）",
        total=total,
    )
    payload = call_json(
        system_blocks=build_cached_system([system]),
        messages=[{"role": "user", "content": user}],
        max_tokens=4096,
    )
    return QuestionList.model_validate(payload)
```

- [ ] **Step 4: Tests with mocked LLM**

`backend/tests/test_question_gen.py`:

```python
from unittest.mock import patch

from mockinterview.agent import question_gen


FAKE_PAYLOAD = {
    "questions": [
        {"text": f"Q{i}", "category": cat, "source": "x", "difficulty": "medium"}
        for i, cat in enumerate(
            ["T1"] * 4 + ["T2"] * 2 + ["T3"] * 3 + ["T4"] * 2 + ["T5"]
        )
    ]
}


def test_generate_questions_with_jd_returns_12():
    with patch.object(question_gen, "call_json", return_value=FAKE_PAYLOAD):
        out = question_gen.generate_questions(
            role="pm",
            resume_json={"basic": {"name": "A"}},
            jd_text="PM at X",
            company_name="X",
        )
    assert len(out.questions) == 12
    cats = [q.category for q in out.questions]
    assert cats.count("T1") == 4
    assert cats.count("T3") == 3


def test_generate_questions_without_jd_redistributes():
    dist = question_gen._distribution(has_jd=False)
    assert dist["T3"] == 0
    assert dist["T1"] == 5
    assert sum(dist.values()) == 11
```

- [ ] **Step 5: Run + commit**

```bash
uv run pytest tests/test_question_gen.py
git add backend/
git commit -m "feat(agent): question generation engine — single LLM call, 5-category distribution"
```

---

### Task 1.10: POST /questions/generate + question CRUD endpoints

**Files:**
- Create: `backend/src/mockinterview/routes/questions.py`
- Create: `backend/src/mockinterview/schemas/api.py`
- Modify: `backend/src/mockinterview/main.py`
- Create: `backend/tests/test_routes_questions.py`

- [ ] **Step 1: API schemas**

`backend/src/mockinterview/schemas/api.py`:

```python
from datetime import datetime

from pydantic import BaseModel

from mockinterview.db.models import QuestionStatus


class QuestionRead(BaseModel):
    id: int
    resume_session_id: int
    category: str
    text: str
    source: str
    difficulty: str
    status: QuestionStatus
    best_score: int | None
    last_attempt_at: datetime | None
    created_at: datetime


class GenerateRequest(BaseModel):
    resume_session_id: int


class QuestionStatusUpdate(BaseModel):
    status: QuestionStatus
```

- [ ] **Step 2: Router**

`backend/src/mockinterview/routes/questions.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from mockinterview.agent.question_gen import generate_questions
from mockinterview.db.models import Question, QuestionStatus, ResumeSession
from mockinterview.db.session import get_session
from mockinterview.schemas.api import GenerateRequest, QuestionRead, QuestionStatusUpdate

router = APIRouter(prefix="/questions", tags=["questions"])


@router.post("/generate", response_model=list[QuestionRead])
def generate(req: GenerateRequest, db: Session = Depends(get_session)):
    rs = db.get(ResumeSession, req.resume_session_id)
    if not rs:
        raise HTTPException(404, "resume_session not found")
    qlist = generate_questions(
        role=rs.role_type,
        resume_json=rs.resume_json,
        jd_text=rs.jd_text,
        company_name=rs.company_name,
    )
    rows: list[Question] = []
    for gq in qlist.questions:
        q = Question(
            resume_session_id=rs.id,
            category=gq.category,
            text=gq.text,
            source=gq.source,
            difficulty=gq.difficulty,
        )
        db.add(q)
        rows.append(q)
    db.commit()
    for q in rows:
        db.refresh(q)
    return rows


@router.get("", response_model=list[QuestionRead])
def list_questions(
    resume_session_id: int,
    category: str | None = None,
    status: QuestionStatus | None = None,
    db: Session = Depends(get_session),
):
    stmt = select(Question).where(Question.resume_session_id == resume_session_id)
    if category:
        stmt = stmt.where(Question.category == category)
    if status:
        stmt = stmt.where(Question.status == status)
    return db.exec(stmt).all()


@router.get("/{question_id}", response_model=QuestionRead)
def get_question(question_id: int, db: Session = Depends(get_session)):
    q = db.get(Question, question_id)
    if not q:
        raise HTTPException(404, "not found")
    return q


@router.patch("/{question_id}/status", response_model=QuestionRead)
def patch_status(
    question_id: int,
    body: QuestionStatusUpdate,
    db: Session = Depends(get_session),
):
    q = db.get(Question, question_id)
    if not q:
        raise HTTPException(404, "not found")
    q.status = body.status
    db.add(q)
    db.commit()
    db.refresh(q)
    return q
```

- [ ] **Step 3: Wire into main.py**

```python
from mockinterview.routes import questions as questions_routes
app.include_router(questions_routes.router)
```

- [ ] **Step 4: Test**

`backend/tests/test_routes_questions.py`:

```python
from unittest.mock import patch

from sqlmodel import Session

from mockinterview.db.models import ResumeSession
from mockinterview.db.session import engine
from mockinterview.schemas.question import QuestionList


FAKE_QLIST = QuestionList.model_validate(
    {
        "questions": [
            {"text": f"Q{i}", "category": c, "source": "x", "difficulty": "medium"}
            for i, c in enumerate(["T1"] * 4 + ["T2"] * 2 + ["T3"] * 3 + ["T4"] * 2 + ["T5"])
        ]
    }
)


def _seed_session(role="pm", jd="PM at X"):
    with Session(engine) as s:
        rs = ResumeSession(
            user_id=1, resume_json={"basic": {"name": "A"}}, jd_text=jd, role_type=role
        )
        s.add(rs)
        s.commit()
        s.refresh(rs)
        return rs.id


def test_generate_persists_12_questions(client):
    sid = _seed_session()
    with patch("mockinterview.routes.questions.generate_questions", return_value=FAKE_QLIST):
        r = client.post("/questions/generate", json={"resume_session_id": sid})
    assert r.status_code == 200
    assert len(r.json()) == 12


def test_list_filters_by_category(client):
    sid = _seed_session()
    with patch("mockinterview.routes.questions.generate_questions", return_value=FAKE_QLIST):
        client.post("/questions/generate", json={"resume_session_id": sid})
    r = client.get(f"/questions?resume_session_id={sid}&category=T1")
    assert len(r.json()) == 4


def test_patch_status_updates(client):
    sid = _seed_session()
    with patch("mockinterview.routes.questions.generate_questions", return_value=FAKE_QLIST):
        ids = [q["id"] for q in client.post("/questions/generate", json={"resume_session_id": sid}).json()]
    qid = ids[0]
    r = client.patch(f"/questions/{qid}/status", json={"status": "needs_redo"})
    assert r.json()["status"] == "needs_redo"
```

- [ ] **Step 5: Run + commit**

```bash
uv run pytest tests/test_routes_questions.py
git add backend/
git commit -m "feat(api): question generation + CRUD + status state machine"
```

---

### Phase 1 Wrap-up

- [ ] **End-to-end Week 1 smoke test**

```bash
# Manually:
uv run uvicorn mockinterview.main:app --reload
# In another shell:
curl -F "file=@tests/fixtures/sample_resume.pdf" \
     -F "role_type=pm" \
     -F "jd_text=PM at ByteDance" \
     -F "company_name=ByteDance" \
     http://localhost:8000/resume
# Take resume_session_id from response, then:
curl -X POST http://localhost:8000/questions/generate \
     -H "Content-Type: application/json" \
     -d '{"resume_session_id": 1}'
```
Expected: 12 questions returned, persisted, listable.

- [ ] **W1 deliverable commit (tag)**

```bash
git tag -a w1-done -m "Week 1: backend resume → question pipeline ready"
```

---

## Phase 2 / Week 2 — U-loop 单题核心

**Phase Goal**: 一道题从开题到出报告完整跑通，支持全部 6 个出口/重定向（软退出 / 硬上限 / 主动结束 / 跳过 / 卡壳提示 / 场景切换 ×2）。

**Phase Deliverable**: `POST /drill` 起会话 + `POST /drill/{id}/answer` 推进 + `GET /drill/{id}/report` 出单题报告，6 种出口都有测试覆盖。

---

### Task 2.1: User signal classifier

**Files:**
- Create: `backend/src/mockinterview/agent/prompts/user_signals.py`
- Create: `backend/src/mockinterview/agent/user_signals.py`
- Create: `backend/tests/test_user_signals.py`

User can signal: `END`（"我答完了"）/ `SKIP`（"跳过"）/ `STUCK`（"不知道、给点提示"）/ `SWITCH_SCENARIO`（"换一个例子"）/ `ANSWER`（一切正常作答）。Heuristic-first classifier with regex fallback to keep cost down; LLM call only on ambiguous matches.

- [ ] **Step 1: Tests**

`backend/tests/test_user_signals.py`:

```python
from mockinterview.agent.user_signals import UserSignal, classify


def test_explicit_end():
    assert classify("我答完了") == UserSignal.END
    assert classify("下一题") == UserSignal.END
    assert classify("answered, next") == UserSignal.END


def test_skip():
    assert classify("跳过") == UserSignal.SKIP
    assert classify("这题我不会，跳过") == UserSignal.SKIP


def test_stuck():
    assert classify("我没思路") == UserSignal.STUCK
    assert classify("能给点提示吗") == UserSignal.STUCK
    assert classify("hint please") == UserSignal.STUCK


def test_switch_scenario():
    assert classify("能换一个例子吗") == UserSignal.SWITCH_SCENARIO
    assert classify("这个例子太薄弱了，换一个") == UserSignal.SWITCH_SCENARIO


def test_normal_answer():
    assert classify("我在 X 项目里负责……") == UserSignal.ANSWER
```

- [ ] **Step 2: Implement**

`backend/src/mockinterview/agent/user_signals.py`:

```python
import re
from enum import Enum


class UserSignal(str, Enum):
    ANSWER = "answer"
    END = "end"
    SKIP = "skip"
    STUCK = "stuck"
    SWITCH_SCENARIO = "switch_scenario"


_PATTERNS = [
    (UserSignal.SKIP, [r"跳过", r"\bskip\b", r"这题不会", r"这道.*不会"]),
    (UserSignal.STUCK, [
        r"没思路", r"不知道(?:怎么|该|从).*?(?:答|说|讲)",
        r"给.*提示", r"\bhint\b", r"\bclue\b",
        r"我.*想不到", r"我.*想不出",
    ]),
    (UserSignal.SWITCH_SCENARIO, [
        r"换.*?例子", r"换.*?场景",
        r"例子.*?(?:薄弱|不行|不够|太弱)",
        r"举不出", r"想不出.*?例子",
    ]),
    (UserSignal.END, [
        r"^我答完了\.?$", r"^答完了\.?$", r"^下一题\.?$",
        r"^answered\b", r"^done\b", r"^next\b",
    ]),
]


def classify(text: str) -> UserSignal:
    t = text.strip().lower()
    for signal, patterns in _PATTERNS:
        for p in patterns:
            if re.search(p, t, re.IGNORECASE):
                return signal
    return UserSignal.ANSWER
```

- [ ] **Step 3: Run + commit**

```bash
uv run pytest tests/test_user_signals.py
git add backend/
git commit -m "feat(agent): user signal classifier (end/skip/stuck/switch/answer)"
```

---

### Task 2.2: Drill eval prompt (rubric scoring + weakest + followup, single call)

**Files:**
- Create: `backend/src/mockinterview/agent/prompts/drill_eval.py`
- Create: `backend/src/mockinterview/agent/drill_eval.py`
- Create: `backend/src/mockinterview/schemas/drill.py`
- Create: `backend/tests/test_drill_eval.py`

Spec §5.2 — one LLM call returns `{scores, weakest_dimension, weakness_diagnosis, next_followup}`.

- [ ] **Step 1: Schemas**

`backend/src/mockinterview/schemas/drill.py`:

```python
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
```

- [ ] **Step 2: Eval prompt**

`backend/src/mockinterview/agent/prompts/drill_eval.py`:

```python
DRILL_EVAL_SYSTEM = """你是一个面试评估官 + 教练。
你会收到：题面、本题 rubric（4 个维度 + 评分指引）、题目类别（T1-T5）、本题之前的完整对话 transcript。
你的任务（一次性输出）：
1. 按 rubric 每维度打 0-3 分（0=完全缺失/答非所问 1=模糊 2=合格 3=出色）
2. 给出 total_score（0-12）
3. 找最弱的一个维度（如果多个并列最弱，选对答题质量影响最大的那个）
4. 一句话诊断为什么这个维度弱
5. 写一句下一轮要问的追问，必须针对最弱维度，且不重复之前 transcript 的问法

严格按以下 JSON schema 输出（用 ```json 代码块）：
{{
  "scores": {{"<dim_key1>": int, "<dim_key2>": int, "<dim_key3>": int, "<dim_key4>": int}},
  "total_score": int,
  "weakest_dimension": "<dim_key>",
  "weakness_diagnosis": "<一句话>",
  "next_followup": "<一句问题>"
}}

scores 的 key 必须用 rubric 提供的 dimension key（不是 label）。
不输出任何 JSON 外的文字。"""


DRILL_EVAL_USER_TEMPLATE = """题目类别：{category}
题面：{question_text}

Rubric：
{rubric_block}

对话 transcript（按时间顺序）：
{transcript_block}

请评分并给出下一轮追问。"""
```

- [ ] **Step 3: Eval module**

`backend/src/mockinterview/agent/drill_eval.py`:

```python
from typing import Any

from mockinterview.agent.client import build_cached_system, call_json
from mockinterview.agent.prompts.drill_eval import DRILL_EVAL_SYSTEM, DRILL_EVAL_USER_TEMPLATE
from mockinterview.agent.rubrics import load_rubric
from mockinterview.schemas.drill import DrillEvalResult, TranscriptTurn


def _format_rubric(rubric: dict[str, Any]) -> str:
    lines = []
    for d in rubric["dimensions"]:
        lines.append(f"- {d['key']} ({d['label']}): {d['description']}")
    lines.append("")
    lines.append("评分级别：")
    for level, desc in rubric["score_levels"].items():
        lines.append(f"  {level}: {desc}")
    return "\n".join(lines)


def _format_transcript(turns: list[TranscriptTurn]) -> str:
    lines = []
    for t in turns:
        prefix = {"agent": "面试官", "user": "候选人"}[t.role]
        tag = "" if t.kind == "normal" else f" [{t.kind}]"
        lines.append(f"[{t.round}] {prefix}{tag}: {t.text}")
    return "\n".join(lines)


def evaluate_and_followup(
    *,
    category: str,
    question_text: str,
    transcript: list[TranscriptTurn],
) -> DrillEvalResult:
    rubric = load_rubric(category)
    system = build_cached_system([DRILL_EVAL_SYSTEM])
    user = DRILL_EVAL_USER_TEMPLATE.format(
        category=category,
        question_text=question_text,
        rubric_block=_format_rubric(rubric),
        transcript_block=_format_transcript(transcript),
    )
    payload = call_json(
        system_blocks=system,
        messages=[{"role": "user", "content": user}],
        max_tokens=1024,
    )
    return DrillEvalResult.model_validate(payload)
```

- [ ] **Step 4: Tests**

`backend/tests/test_drill_eval.py`:

```python
from unittest.mock import patch

from mockinterview.agent import drill_eval
from mockinterview.schemas.drill import TranscriptTurn


FAKE = {
    "scores": {"situation": 2, "task": 2, "action": 2, "result": 1},
    "total_score": 7,
    "weakest_dimension": "result",
    "weakness_diagnosis": "结果数字没有 baseline",
    "next_followup": "你说留存涨了 5%，baseline 是同期还是上月？",
}


def test_evaluate_returns_parsed_result():
    transcript = [
        TranscriptTurn(role="agent", text="Q?", round=0),
        TranscriptTurn(role="user", text="我做了 X 项目，留存涨了 5%。", round=1),
    ]
    with patch.object(drill_eval, "call_json", return_value=FAKE):
        result = drill_eval.evaluate_and_followup(
            category="T1",
            question_text="X 项目你怎么决策的？",
            transcript=transcript,
        )
    assert result.total_score == 7
    assert result.weakest_dimension == "result"
    assert "baseline" in result.next_followup
```

- [ ] **Step 5: Run + commit**

```bash
uv run pytest tests/test_drill_eval.py
git add backend/
git commit -m "feat(agent): drill eval (single LLM call → scores + weakest + followup)"
```

---

### Task 2.3: Scenario switch prompt + helper

**Files:**
- Create: `backend/src/mockinterview/agent/prompts/scenario_switch.py`
- Modify: `backend/src/mockinterview/agent/drill_eval.py` (add `propose_scenario_switch`)
- Create: `backend/tests/test_scenario_switch.py`

Spec §5.3 #6 — agent 主动 OR 用户被动触发。Two functions:
- `propose_scenario_switch(question, transcript)` — 当 agent 主动检测用户例子薄弱时输出"换场景"提示语
- `relax_intent(question, transcript)` — 当用户连考察意图都没料时进一步松绑到相邻意图

- [ ] **Step 1: Prompt**

`backend/src/mockinterview/agent/prompts/scenario_switch.py`:

```python
SCENARIO_SWITCH_SYSTEM = """你是面试官。你判断到候选人当前给的例子撑不住考察意图（例如题问"实习中的领导力"，候选人答"帮组里同事改 PPT"）。
你需要主动给台阶——不放弃考察意图，但允许从其他场景找例子。

规则：
1. 释放场景维度（实习/项目/校园活动/课外/生活），保留考察意图
2. 用真实面试官的口吻，先肯定一句"这个例子可能不够典型"，再问"你有没有在 X / Y / Z 场景类似的事？"
3. 如果连考察意图本身都没料（比如真没领导经验），给意图相邻的备选（"主动推动事情发生" 也算同维度证据）
4. 输出严格 JSON：
```json
{"prompt": "<给候选人的话>"}
```
"""

SCENARIO_SWITCH_USER_TEMPLATE = """题目：{question_text}
原考察意图：{original_intent}

候选人当前给的例子（最后一轮）：
{last_user_answer}

之前已切换场景次数：{prior_switches}

请输出主动让路的提示语。"""
```

- [ ] **Step 2: Add to drill_eval.py**

Append to `backend/src/mockinterview/agent/drill_eval.py`:

```python
from mockinterview.agent.prompts.scenario_switch import (
    SCENARIO_SWITCH_SYSTEM,
    SCENARIO_SWITCH_USER_TEMPLATE,
)


def propose_scenario_switch(
    *,
    question_text: str,
    original_intent: str,
    last_user_answer: str,
    prior_switches: int,
) -> str:
    system = build_cached_system([SCENARIO_SWITCH_SYSTEM])
    user = SCENARIO_SWITCH_USER_TEMPLATE.format(
        question_text=question_text,
        original_intent=original_intent,
        last_user_answer=last_user_answer,
        prior_switches=prior_switches,
    )
    payload = call_json(
        system_blocks=system,
        messages=[{"role": "user", "content": user}],
        max_tokens=512,
    )
    return payload["prompt"]
```

- [ ] **Step 3: Test**

`backend/tests/test_scenario_switch.py`:

```python
from unittest.mock import patch

from mockinterview.agent import drill_eval


def test_propose_scenario_switch():
    with patch.object(drill_eval, "call_json", return_value={"prompt": "这个例子可能不够典型，要不你说说项目里类似的经历？"}):
        out = drill_eval.propose_scenario_switch(
            question_text="举一个实习中体现领导力的例子",
            original_intent="领导力",
            last_user_answer="我帮同事改了 PPT",
            prior_switches=0,
        )
    assert "不够典型" in out
```

- [ ] **Step 4: Run + commit**

```bash
uv run pytest tests/test_scenario_switch.py
git add backend/
git commit -m "feat(agent): scenario switch helper (主动让路 prompt)"
```

---

### Task 2.4: Prompt mode (思考框架) helper

**Files:**
- Create: `backend/src/mockinterview/agent/prompts/prompt_mode.py`
- Modify: `backend/src/mockinterview/agent/drill_eval.py` (add `give_thinking_framework`)
- Create: `backend/tests/test_prompt_mode.py`

Spec §5.3 #5 — 卡壳时给思考框架（不追问）。

- [ ] **Step 1: Prompt**

`backend/src/mockinterview/agent/prompts/prompt_mode.py`:

```python
PROMPT_MODE_SYSTEM = """你是面试官 + 教练。候选人卡壳了（说"不知道、没思路、给点提示"）。
你不能追问、不能给答案，只能给一个思考框架（3-4 个切入角度），让候选人重新组织答案。

规则：
1. 用本题 rubric 的 4 个维度倒推 3-4 个切入问题
2. 用平实口吻，不要写"框架一二三"这种生硬结构
3. 结尾鼓励候选人按这些角度再答一次
4. 输出严格 JSON：
```json
{"hint": "<给候选人的提示语>"}
```
"""

PROMPT_MODE_USER_TEMPLATE = """题目：{question_text}
本题 rubric 维度：{dimensions}

候选人最后一句话：{last_user_text}

请给一个思考框架。"""
```

- [ ] **Step 2: Helper function**

Append to `backend/src/mockinterview/agent/drill_eval.py`:

```python
from mockinterview.agent.prompts.prompt_mode import PROMPT_MODE_SYSTEM, PROMPT_MODE_USER_TEMPLATE


def give_thinking_framework(
    *,
    category: str,
    question_text: str,
    last_user_text: str,
) -> str:
    rubric = load_rubric(category)
    dims = ", ".join(d["label"] for d in rubric["dimensions"])
    system = build_cached_system([PROMPT_MODE_SYSTEM])
    user = PROMPT_MODE_USER_TEMPLATE.format(
        question_text=question_text,
        dimensions=dims,
        last_user_text=last_user_text,
    )
    payload = call_json(
        system_blocks=system,
        messages=[{"role": "user", "content": user}],
        max_tokens=512,
    )
    return payload["hint"]
```

- [ ] **Step 3: Test**

`backend/tests/test_prompt_mode.py`:

```python
from unittest.mock import patch

from mockinterview.agent import drill_eval


def test_thinking_framework():
    with patch.object(drill_eval, "call_json", return_value={"hint": "试试从用户场景、决策依据、量化结果三个角度切入。"}):
        out = drill_eval.give_thinking_framework(
            category="T1",
            question_text="X 项目你怎么决策的？",
            last_user_text="我没思路",
        )
    assert "用户场景" in out or "决策依据" in out
```

- [ ] **Step 4: Run + commit**

```bash
uv run pytest tests/test_prompt_mode.py
git add backend/
git commit -m "feat(agent): prompt mode (给思考框架，不追问)"
```

---

### Task 2.5: Exemplar answer synthesizer

**Files:**
- Create: `backend/src/mockinterview/agent/prompts/exemplar.py`
- Create: `backend/src/mockinterview/agent/exemplar.py`
- Create: `backend/tests/test_exemplar.py`

Spec §5.4 — 题目结束时合成"如果按 rubric 高分作答可以这样说"参考答案。

- [ ] **Step 1: Prompt**

`backend/src/mockinterview/agent/prompts/exemplar.py`:

```python
EXEMPLAR_SYSTEM = """你是资深面试官。基于：
- 题面
- 本题 rubric（4 维度 + 评分指引）
- 候选人简历（结构化数据）
- 候选人本题对话 transcript（看出 ta 真实经历）

合成一份"rubric 高分版本"的范例答案——必须用候选人简历里实际有的项目/经历做素材，不能编造。
如果简历里没合适素材，写"假设你做过 X 项目，可以这样说……"。

输出严格 JSON：
```json
{
  "exemplar": "<范例答案，4-8 句话，对应 rubric 4 维度>",
  "improvement_suggestions": ["<建议1>", "<建议2>", "<建议3>"]
}
```

improvement_suggestions 必须是 3 条具体可操作的建议，不写"加强结构化思维"这种废话。"""

EXEMPLAR_USER_TEMPLATE = """题目：{question_text}
类别：{category}
Rubric 维度：{dimensions}

简历结构化数据：
{resume_json}

候选人本题对话 transcript：
{transcript_block}

请合成范例答案 + 3 条改进建议。"""
```

- [ ] **Step 2: Module**

`backend/src/mockinterview/agent/exemplar.py`:

```python
import json
from typing import Any

from mockinterview.agent.client import build_cached_system, call_json
from mockinterview.agent.prompts.exemplar import EXEMPLAR_SYSTEM, EXEMPLAR_USER_TEMPLATE
from mockinterview.agent.rubrics import load_rubric
from mockinterview.schemas.drill import TranscriptTurn


def synthesize_exemplar(
    *,
    category: str,
    question_text: str,
    resume_json: dict[str, Any],
    transcript: list[TranscriptTurn],
) -> tuple[str, list[str]]:
    rubric = load_rubric(category)
    dims = ", ".join(f"{d['label']} ({d['description']})" for d in rubric["dimensions"])
    system = build_cached_system([EXEMPLAR_SYSTEM])
    transcript_block = "\n".join(
        f"[{t.round}] {'面试官' if t.role == 'agent' else '候选人'}: {t.text}"
        for t in transcript
    )
    user = EXEMPLAR_USER_TEMPLATE.format(
        question_text=question_text,
        category=category,
        dimensions=dims,
        resume_json=json.dumps(resume_json, ensure_ascii=False, indent=2),
        transcript_block=transcript_block,
    )
    payload = call_json(
        system_blocks=system,
        messages=[{"role": "user", "content": user}],
        max_tokens=1024,
    )
    return payload["exemplar"], payload["improvement_suggestions"]
```

- [ ] **Step 3: Test**

`backend/tests/test_exemplar.py`:

```python
from unittest.mock import patch

from mockinterview.agent import exemplar
from mockinterview.schemas.drill import TranscriptTurn


def test_synthesize_returns_tuple():
    fake = {
        "exemplar": "在用户分群项目中，我先定义 baseline 为...",
        "improvement_suggestions": ["明确 baseline", "补充归因方法", "量化业务影响"],
    }
    with patch.object(exemplar, "call_json", return_value=fake):
        ex, sugs = exemplar.synthesize_exemplar(
            category="T1",
            question_text="Q?",
            resume_json={"basic": {"name": "A"}, "projects": []},
            transcript=[TranscriptTurn(role="agent", text="Q?", round=0)],
        )
    assert "baseline" in ex
    assert len(sugs) == 3
```

- [ ] **Step 4: Run + commit**

```bash
uv run pytest tests/test_exemplar.py
git add backend/
git commit -m "feat(agent): exemplar answer synthesizer + 3 改进建议"
```

---

### Task 2.6: Drill state machine

**Files:**
- Create: `backend/src/mockinterview/agent/drill_loop.py`
- Create: `backend/tests/test_drill_loop.py`

Pure logic module — orchestrates 6 exits. Stateless functions; takes current state + user input → returns new state + agent response. Persistence comes in Task 2.7.

State shape (in-memory; session row holds JSON snapshot):

```python
@dataclass
class DrillState:
    question_id: int
    question_text: str
    category: str            # T1..T5
    transcript: list[TranscriptTurn]
    followup_rounds: int     # number of follow-ups asked so far
    scenario_switch_count: int
    prompt_mode_count: int
    last_eval: DrillEvalResult | None  # most recent evaluation
    status: DrillStatus      # ACTIVE | ENDED
    exit_type: ExitType | None
```

- [ ] **Step 1: Tests defining behavior of each exit**

`backend/tests/test_drill_loop.py`:

```python
from unittest.mock import patch

import pytest

from mockinterview.agent.drill_loop import DrillState, DrillStatus, advance, start_drill
from mockinterview.agent.user_signals import UserSignal
from mockinterview.db.models import ExitType
from mockinterview.schemas.drill import DrillEvalResult, TranscriptTurn


def _state(**overrides):
    base = dict(
        question_id=1,
        question_text="说说你做的 X 项目",
        category="T1",
        original_intent="项目深挖",
        resume_json={"basic": {"name": "A"}, "projects": []},
        transcript=[TranscriptTurn(role="agent", text="说说你做的 X 项目", round=0)],
        followup_rounds=0,
        scenario_switch_count=0,
        prompt_mode_count=0,
        last_eval=None,
        status=DrillStatus.ACTIVE,
        exit_type=None,
    )
    base.update(overrides)
    return DrillState(**base)


def test_start_drill_returns_initial_state():
    s = start_drill(
        question_id=1,
        question_text="Q?",
        category="T1",
        resume_json={"basic": {"name": "A"}},
        original_intent="X",
    )
    assert s.status == DrillStatus.ACTIVE
    assert len(s.transcript) == 1
    assert s.transcript[0].role == "agent"


def test_advance_user_end_signal_triggers_user_end_exit():
    state = _state()
    out = advance(state, "我答完了")
    assert out.status == DrillStatus.ENDED
    assert out.exit_type == ExitType.USER_END


def test_advance_user_skip_signal_triggers_skip_exit():
    state = _state()
    out = advance(state, "跳过")
    assert out.status == DrillStatus.ENDED
    assert out.exit_type == ExitType.SKIP


def test_advance_user_stuck_triggers_prompt_mode_no_round_increment():
    state = _state()
    with patch("mockinterview.agent.drill_loop.give_thinking_framework", return_value="试试 X / Y / Z 三个角度。"):
        out = advance(state, "我没思路")
    assert out.status == DrillStatus.ACTIVE
    assert out.followup_rounds == 0  # not incremented
    assert out.prompt_mode_count == 1
    assert out.transcript[-1].kind == "prompt_mode"


def test_advance_switch_scenario_consumes_budget_and_resets_round():
    state = _state(followup_rounds=2)
    with patch("mockinterview.agent.drill_loop.propose_scenario_switch", return_value="换个项目里的例子？"):
        out = advance(state, "能换一个吗")
    assert out.status == DrillStatus.ACTIVE
    assert out.scenario_switch_count == 1
    assert out.followup_rounds == 0  # reset
    assert out.transcript[-1].kind == "scenario_switch"


def test_advance_switch_scenario_caps_at_2_then_hard_limit():
    state = _state(scenario_switch_count=2, followup_rounds=2)
    out = advance(state, "再换一个")
    # 3rd switch attempt should not consume; falls through to normal answer eval
    # because we've capped budget
    assert out.scenario_switch_count == 2


def test_advance_normal_answer_runs_eval():
    state = _state()
    fake_eval = DrillEvalResult(
        scores={"situation": 2, "task": 2, "action": 2, "result": 2},
        total_score=8,
        weakest_dimension="result",
        weakness_diagnosis="缺 baseline",
        next_followup="baseline 怎么定的？",
    )
    with patch("mockinterview.agent.drill_loop.evaluate_and_followup", return_value=fake_eval):
        out = advance(state, "我做了 X 项目，结果还行。")
    assert out.followup_rounds == 1
    assert out.status == DrillStatus.ACTIVE
    assert out.transcript[-2].role == "user"
    assert out.transcript[-1].text == "baseline 怎么定的？"


def test_advance_high_score_triggers_soft_exit():
    state = _state()
    fake_eval = DrillEvalResult(
        scores={"situation": 3, "task": 3, "action": 2, "result": 1},
        total_score=9,
        weakest_dimension="result",
        weakness_diagnosis="ok",
        next_followup="N/A",
    )
    with patch("mockinterview.agent.drill_loop.evaluate_and_followup", return_value=fake_eval):
        out = advance(state, "我答得很完整。")
    assert out.status == DrillStatus.ENDED
    assert out.exit_type == ExitType.SOFT


def test_advance_hits_hard_limit_at_3_followups():
    state = _state(followup_rounds=2)  # 第 3 轮提交后强制结束
    fake_eval = DrillEvalResult(
        scores={"situation": 1, "task": 1, "action": 1, "result": 1},
        total_score=4,
        weakest_dimension="action",
        weakness_diagnosis="弱",
        next_followup="再追一问？",
    )
    with patch("mockinterview.agent.drill_loop.evaluate_and_followup", return_value=fake_eval):
        out = advance(state, "再答一次")
    assert out.followup_rounds == 3
    assert out.status == DrillStatus.ENDED
    assert out.exit_type == ExitType.HARD_LIMIT
```

- [ ] **Step 2: Implementation**

`backend/src/mockinterview/agent/drill_loop.py`:

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from mockinterview.agent.drill_eval import (
    evaluate_and_followup,
    give_thinking_framework,
    propose_scenario_switch,
)
from mockinterview.agent.user_signals import UserSignal, classify
from mockinterview.db.models import ExitType
from mockinterview.schemas.drill import DrillEvalResult, TranscriptTurn

MAX_FOLLOWUPS = 3
MAX_SWITCHES = 2
SOFT_THRESHOLD = 9


class DrillStatus(str, Enum):
    ACTIVE = "active"
    ENDED = "ended"


@dataclass
class DrillState:
    question_id: int
    question_text: str
    category: str
    original_intent: str
    resume_json: dict[str, Any]
    transcript: list[TranscriptTurn] = field(default_factory=list)
    followup_rounds: int = 0
    scenario_switch_count: int = 0
    prompt_mode_count: int = 0
    last_eval: DrillEvalResult | None = None
    status: DrillStatus = DrillStatus.ACTIVE
    exit_type: ExitType | None = None


def start_drill(
    *,
    question_id: int,
    question_text: str,
    category: str,
    resume_json: dict[str, Any],
    original_intent: str,
) -> DrillState:
    return DrillState(
        question_id=question_id,
        question_text=question_text,
        category=category,
        original_intent=original_intent,
        resume_json=resume_json,
        transcript=[TranscriptTurn(role="agent", text=question_text, round=0)],
    )


def _next_round(state: DrillState) -> int:
    return state.followup_rounds + 1


def _append_user(state: DrillState, text: str) -> None:
    state.transcript.append(
        TranscriptTurn(role="user", text=text, round=state.followup_rounds)
    )


def advance(state: DrillState, user_text: str) -> DrillState:
    if state.status == DrillStatus.ENDED:
        return state

    signal = classify(user_text)

    # End-class signals
    if signal == UserSignal.END:
        _append_user(state, user_text)
        state.status = DrillStatus.ENDED
        state.exit_type = ExitType.USER_END
        return state
    if signal == UserSignal.SKIP:
        _append_user(state, user_text)
        state.status = DrillStatus.ENDED
        state.exit_type = ExitType.SKIP
        return state

    # Redirect-class: stuck → prompt mode
    if signal == UserSignal.STUCK:
        _append_user(state, user_text)
        hint = give_thinking_framework(
            category=state.category,
            question_text=state.question_text,
            last_user_text=user_text,
        )
        state.transcript.append(
            TranscriptTurn(
                role="agent",
                text=hint,
                round=state.followup_rounds,
                kind="prompt_mode",
            )
        )
        state.prompt_mode_count += 1
        return state

    # Redirect-class: scenario switch (only if budget left)
    if signal == UserSignal.SWITCH_SCENARIO and state.scenario_switch_count < MAX_SWITCHES:
        _append_user(state, user_text)
        switch_msg = propose_scenario_switch(
            question_text=state.question_text,
            original_intent=state.original_intent,
            last_user_answer=user_text,
            prior_switches=state.scenario_switch_count,
        )
        state.scenario_switch_count += 1
        state.followup_rounds = 0  # reset budget
        state.transcript.append(
            TranscriptTurn(
                role="agent",
                text=switch_msg,
                round=0,
                kind="scenario_switch",
            )
        )
        return state

    # Normal answer (or scenario switch attempted past budget) → evaluate
    _append_user(state, user_text)
    state.followup_rounds += 1
    eval_result = evaluate_and_followup(
        category=state.category,
        question_text=state.question_text,
        transcript=state.transcript,
    )
    state.last_eval = eval_result

    if eval_result.total_score >= SOFT_THRESHOLD:
        state.status = DrillStatus.ENDED
        state.exit_type = ExitType.SOFT
        return state

    if state.followup_rounds >= MAX_FOLLOWUPS:
        state.status = DrillStatus.ENDED
        state.exit_type = ExitType.HARD_LIMIT
        return state

    # Continue: agent emits the followup
    state.transcript.append(
        TranscriptTurn(
            role="agent",
            text=eval_result.next_followup,
            round=state.followup_rounds,
        )
    )
    return state
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest tests/test_drill_loop.py
```
Expected: all green.

- [ ] **Step 4: Commit**

```bash
git add backend/
git commit -m "feat(agent): drill state machine — 6 exits + 2 redirects + budget caps"
```

---

### Task 2.7: Drill API endpoints + persistence

**Files:**
- Create: `backend/src/mockinterview/routes/drill.py`
- Create: `backend/src/mockinterview/agent/drill_storage.py`
- Modify: `backend/src/mockinterview/db/models.py` (add `state_snapshot` JSON to DrillAttempt)
- Modify: `backend/src/mockinterview/main.py`
- Create: `backend/tests/test_routes_drill.py`

Strategy: each `DrillAttempt` row holds the full snapshot of `DrillState` after each `advance` call. Rebuild from snapshot on every API call (stateless server).

- [ ] **Step 1: Add state_snapshot column**

Modify `DrillAttempt` in `models.py` — add field:

```python
    state_snapshot: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
```

(Keep old fields; this is additive.)

- [ ] **Step 2: Storage helper**

`backend/src/mockinterview/agent/drill_storage.py`:

```python
from dataclasses import asdict
from typing import Any

from mockinterview.agent.drill_loop import DrillState, DrillStatus
from mockinterview.db.models import ExitType
from mockinterview.schemas.drill import DrillEvalResult, TranscriptTurn


def to_snapshot(state: DrillState) -> dict[str, Any]:
    return {
        "question_id": state.question_id,
        "question_text": state.question_text,
        "category": state.category,
        "original_intent": state.original_intent,
        "resume_json": state.resume_json,
        "transcript": [t.model_dump() for t in state.transcript],
        "followup_rounds": state.followup_rounds,
        "scenario_switch_count": state.scenario_switch_count,
        "prompt_mode_count": state.prompt_mode_count,
        "last_eval": state.last_eval.model_dump() if state.last_eval else None,
        "status": state.status.value,
        "exit_type": state.exit_type.value if state.exit_type else None,
    }


def from_snapshot(snap: dict[str, Any]) -> DrillState:
    return DrillState(
        question_id=snap["question_id"],
        question_text=snap["question_text"],
        category=snap["category"],
        original_intent=snap["original_intent"],
        resume_json=snap["resume_json"],
        transcript=[TranscriptTurn.model_validate(t) for t in snap["transcript"]],
        followup_rounds=snap["followup_rounds"],
        scenario_switch_count=snap["scenario_switch_count"],
        prompt_mode_count=snap["prompt_mode_count"],
        last_eval=(
            DrillEvalResult.model_validate(snap["last_eval"]) if snap["last_eval"] else None
        ),
        status=DrillStatus(snap["status"]),
        exit_type=ExitType(snap["exit_type"]) if snap["exit_type"] else None,
    )
```

- [ ] **Step 3: Routes**

`backend/src/mockinterview/routes/drill.py`:

```python
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from mockinterview.agent.drill_loop import DrillStatus, advance, start_drill
from mockinterview.agent.drill_storage import from_snapshot, to_snapshot
from mockinterview.agent.exemplar import synthesize_exemplar
from mockinterview.db.models import DrillAttempt, Question, QuestionStatus, ResumeSession
from mockinterview.db.session import get_session

router = APIRouter(prefix="/drill", tags=["drill"])


class StartDrillBody(BaseModel):
    question_id: int


class AnswerBody(BaseModel):
    text: str


class DrillResponse(BaseModel):
    drill_id: int
    status: str
    transcript: list[dict]
    last_agent_text: str
    exit_type: str | None
    rubric_scores: dict[str, int] | None
    total_score: int | None


def _serialize(d: DrillAttempt) -> DrillResponse:
    snap = d.state_snapshot or {}
    transcript = snap.get("transcript", [])
    last_agent = next(
        (t["text"] for t in reversed(transcript) if t["role"] == "agent"),
        "",
    )
    last_eval = snap.get("last_eval")
    return DrillResponse(
        drill_id=d.id,
        status=snap.get("status", "active"),
        transcript=transcript,
        last_agent_text=last_agent,
        exit_type=snap.get("exit_type"),
        rubric_scores=last_eval["scores"] if last_eval else None,
        total_score=last_eval["total_score"] if last_eval else None,
    )


@router.post("", response_model=DrillResponse)
def start(body: StartDrillBody, db: Session = Depends(get_session)):
    q = db.get(Question, body.question_id)
    if not q:
        raise HTTPException(404, "question not found")
    rs = db.get(ResumeSession, q.resume_session_id)
    if not rs:
        raise HTTPException(404, "resume_session not found")
    state = start_drill(
        question_id=q.id,
        question_text=q.text,
        category=q.category,
        resume_json=rs.resume_json,
        original_intent=q.source,
    )
    d = DrillAttempt(
        question_id=q.id,
        transcript_json=[t.model_dump() for t in state.transcript],
        rubric_scores_json={},
        total_score=0,
        exit_type="soft",  # placeholder, overwritten on end
        scenario_switch_count=0,
        prompt_mode_count=0,
        followup_rounds=0,
        exemplar_answer="",
        improvement_suggestions=[],
        state_snapshot=to_snapshot(state),
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return _serialize(d)


@router.post("/{drill_id}/answer", response_model=DrillResponse)
def answer(drill_id: int, body: AnswerBody, db: Session = Depends(get_session)):
    d = db.get(DrillAttempt, drill_id)
    if not d:
        raise HTTPException(404, "drill not found")
    if not d.state_snapshot:
        raise HTTPException(400, "drill has no state")
    state = from_snapshot(d.state_snapshot)
    state = advance(state, body.text)

    d.state_snapshot = to_snapshot(state)
    d.transcript_json = [t.model_dump() for t in state.transcript]
    d.followup_rounds = state.followup_rounds
    d.scenario_switch_count = state.scenario_switch_count
    d.prompt_mode_count = state.prompt_mode_count

    if state.status == DrillStatus.ENDED:
        # finalize
        scores = state.last_eval.scores if state.last_eval else {}
        total = state.last_eval.total_score if state.last_eval else 0
        d.rubric_scores_json = scores
        d.total_score = total
        d.exit_type = state.exit_type or "user_end"
        d.ended_at = datetime.utcnow()
        # only synthesize exemplar for non-skip exits
        if state.exit_type and state.exit_type.value != "skip":
            exemplar, suggestions = synthesize_exemplar(
                category=state.category,
                question_text=state.question_text,
                resume_json=state.resume_json,
                transcript=state.transcript,
            )
            d.exemplar_answer = exemplar
            d.improvement_suggestions = suggestions
        # update Question.status + best_score
        q = db.get(Question, state.question_id)
        if q:
            if state.exit_type and state.exit_type.value == "skip":
                q.status = QuestionStatus.SKIPPED
            elif total >= 9:
                q.status = QuestionStatus.IMPROVED if (q.best_score or 0) >= 9 else QuestionStatus.PRACTICED
            else:
                q.status = QuestionStatus.NEEDS_REDO
            q.best_score = max(q.best_score or 0, total)
            q.last_attempt_at = datetime.utcnow()
            db.add(q)

    db.add(d)
    db.commit()
    db.refresh(d)
    return _serialize(d)


@router.get("/{drill_id}", response_model=DrillResponse)
def get_drill(drill_id: int, db: Session = Depends(get_session)):
    d = db.get(DrillAttempt, drill_id)
    if not d:
        raise HTTPException(404, "not found")
    return _serialize(d)
```

- [ ] **Step 4: Wire into main.py**

```python
from mockinterview.routes import drill as drill_routes
app.include_router(drill_routes.router)
```

- [ ] **Step 5: Tests**

`backend/tests/test_routes_drill.py`:

```python
from unittest.mock import patch

from sqlmodel import Session

from mockinterview.db.models import Question, ResumeSession
from mockinterview.db.session import engine
from mockinterview.schemas.drill import DrillEvalResult


def _seed_question():
    with Session(engine) as s:
        rs = ResumeSession(user_id=1, resume_json={}, role_type="pm")
        s.add(rs)
        s.commit()
        s.refresh(rs)
        q = Question(
            resume_session_id=rs.id,
            category="T1",
            text="说说 X 项目",
            source="反推自项目 X",
            difficulty="medium",
        )
        s.add(q)
        s.commit()
        s.refresh(q)
        return q.id


def test_start_drill_creates_attempt(client):
    qid = _seed_question()
    r = client.post("/drill", json={"question_id": qid})
    assert r.status_code == 200
    assert r.json()["status"] == "active"
    assert "X 项目" in r.json()["last_agent_text"]


def test_advance_with_skip_ends_drill(client):
    qid = _seed_question()
    drill_id = client.post("/drill", json={"question_id": qid}).json()["drill_id"]
    r = client.post(f"/drill/{drill_id}/answer", json={"text": "跳过"})
    assert r.json()["status"] == "ended"
    assert r.json()["exit_type"] == "skip"


def test_advance_with_high_score_soft_exits(client):
    qid = _seed_question()
    drill_id = client.post("/drill", json={"question_id": qid}).json()["drill_id"]
    fake_eval = DrillEvalResult(
        scores={"situation": 3, "task": 3, "action": 2, "result": 1},
        total_score=9,
        weakest_dimension="result",
        weakness_diagnosis="ok",
        next_followup="N/A",
    )
    with (
        patch("mockinterview.agent.drill_loop.evaluate_and_followup", return_value=fake_eval),
        patch(
            "mockinterview.routes.drill.synthesize_exemplar",
            return_value=("exemplar text", ["a", "b", "c"]),
        ),
    ):
        r = client.post(
            f"/drill/{drill_id}/answer",
            json={"text": "完整答案 with baseline 同期 + 归因 + 量化"},
        )
    assert r.json()["exit_type"] == "soft"
    assert r.json()["total_score"] == 9
```

- [ ] **Step 6: Run + commit**

```bash
uv run pytest tests/test_routes_drill.py
git add backend/
git commit -m "feat(api): drill endpoints (start/answer/get) + state persistence + question status update"
```

---

### Task 2.8: Single-question report endpoint

**Files:**
- Create: `backend/src/mockinterview/routes/reports.py`
- Modify: `backend/src/mockinterview/main.py`
- Create: `backend/tests/test_routes_reports.py`

- [ ] **Step 1: Routes**

`backend/src/mockinterview/routes/reports.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from mockinterview.agent.rubrics import load_rubric
from mockinterview.db.models import DrillAttempt, Question
from mockinterview.db.session import get_session

router = APIRouter(prefix="/reports", tags=["reports"])


class SingleReport(BaseModel):
    drill_id: int
    question_id: int
    question_text: str
    category: str
    transcript: list[dict]
    rubric: dict
    rubric_scores: dict[str, int]
    total_score: int
    exit_type: str
    scenario_switch_count: int
    prompt_mode_count: int
    followup_rounds: int
    exemplar_answer: str
    improvement_suggestions: list[str]


@router.get("/drill/{drill_id}", response_model=SingleReport)
def drill_report(drill_id: int, db: Session = Depends(get_session)):
    d = db.get(DrillAttempt, drill_id)
    if not d:
        raise HTTPException(404, "drill not found")
    q = db.get(Question, d.question_id)
    rubric = load_rubric(q.category)
    return SingleReport(
        drill_id=d.id,
        question_id=q.id,
        question_text=q.text,
        category=q.category,
        transcript=d.transcript_json,
        rubric=rubric,
        rubric_scores=d.rubric_scores_json,
        total_score=d.total_score,
        exit_type=d.exit_type.value if hasattr(d.exit_type, "value") else d.exit_type,
        scenario_switch_count=d.scenario_switch_count,
        prompt_mode_count=d.prompt_mode_count,
        followup_rounds=d.followup_rounds,
        exemplar_answer=d.exemplar_answer,
        improvement_suggestions=d.improvement_suggestions,
    )
```

- [ ] **Step 2: Wire + test**

`backend/tests/test_routes_reports.py`:

```python
from unittest.mock import patch

from mockinterview.schemas.drill import DrillEvalResult
from sqlmodel import Session

from mockinterview.db.models import Question, ResumeSession
from mockinterview.db.session import engine


def _seed():
    with Session(engine) as s:
        rs = ResumeSession(user_id=1, resume_json={}, role_type="pm")
        s.add(rs)
        s.commit()
        s.refresh(rs)
        q = Question(
            resume_session_id=rs.id,
            category="T1",
            text="Q",
            source="x",
            difficulty="medium",
        )
        s.add(q)
        s.commit()
        s.refresh(q)
        return q.id


def test_report_returns_full_data(client):
    qid = _seed()
    drill_id = client.post("/drill", json={"question_id": qid}).json()["drill_id"]
    fake = DrillEvalResult(
        scores={"situation": 3, "task": 3, "action": 2, "result": 1},
        total_score=9,
        weakest_dimension="result",
        weakness_diagnosis="ok",
        next_followup="N/A",
    )
    with (
        patch("mockinterview.agent.drill_loop.evaluate_and_followup", return_value=fake),
        patch(
            "mockinterview.routes.drill.synthesize_exemplar",
            return_value=("exemplar text", ["a", "b", "c"]),
        ),
    ):
        client.post(f"/drill/{drill_id}/answer", json={"text": "好答案"})
    r = client.get(f"/reports/drill/{drill_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["total_score"] == 9
    assert body["exemplar_answer"] == "exemplar text"
    assert len(body["improvement_suggestions"]) == 3
    assert body["rubric"]["category"] == "T1"
```

- [ ] **Step 3: Run + commit**

```bash
uv run pytest tests/test_routes_reports.py
git add backend/
git commit -m "feat(api): GET /reports/drill/{id} — single-question report"
```

---

### Phase 2 Wrap-up

- [ ] **W2 deliverable smoke test**

```bash
# Start server, then:
# 1) Use a real ResumeSession + Question seeded from W1 e2e
# 2) POST /drill → confirm state begins
# 3) POST /drill/{id}/answer with various texts:
#    - "跳过" → exit_type=skip
#    - "我没思路，给点提示" → prompt_mode_count=1, status=active
#    - "能换一个例子吗" → scenario_switch_count=1
#    - "我答完了" → exit_type=user_end
#    - 完整 STAR 答案（live Claude eval） → soft exit
# 4) GET /reports/drill/{id} → 完整报告
```

- [ ] **W2 tag**

```bash
git tag -a w2-done -m "Week 2: U-loop core complete (6 exits, all tested)"
```

---

## Phase 3 / Week 3 — 前端 + 报告

**Phase Goal**: 本地完整跑通——上传简历 → 题库 → 单题演练 → 单题报告 → 整套面试 → 整套报告。

**Phase Deliverable**: `pnpm dev` + `uv run uvicorn` 双开能走完整流程，每个页面渲染对应的 backend 数据。

> 前端测试策略：v1 不写单元测试（节奏紧张）。每个 task 末尾用真实浏览器手动验证 + 截图。

---

### Task 3.1: TS types + API client (full surface)

**Files:**
- Create: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Types matching backend schemas**

`frontend/src/lib/types.ts`:

```ts
export type Category = "T1" | "T2" | "T3" | "T4" | "T5";
export type Difficulty = "easy" | "medium" | "hard";
export type RoleType = "pm" | "data" | "ai" | "other";
export type QuestionStatus =
  | "not_practiced"
  | "practiced"
  | "needs_redo"
  | "improved"
  | "skipped";
export type ExitType = "soft" | "hard_limit" | "user_end" | "skip";

export interface ResumeUploadResponse {
  id: number;
  role_type: RoleType;
  resume_json: Record<string, unknown>;
  jd_text: string | null;
  company_name: string | null;
}

export interface Question {
  id: number;
  resume_session_id: number;
  category: Category;
  text: string;
  source: string;
  difficulty: Difficulty;
  status: QuestionStatus;
  best_score: number | null;
  last_attempt_at: string | null;
  created_at: string;
}

export interface TranscriptTurn {
  role: "agent" | "user";
  text: string;
  round: number;
  kind?: "normal" | "scenario_switch" | "prompt_mode" | "system";
}

export interface DrillResponse {
  drill_id: number;
  status: "active" | "ended";
  transcript: TranscriptTurn[];
  last_agent_text: string;
  exit_type: ExitType | null;
  rubric_scores: Record<string, number> | null;
  total_score: number | null;
}

export interface RubricDimension {
  key: string;
  label: string;
  description: string;
}

export interface Rubric {
  category: Category;
  name: string;
  description: string;
  dimensions: RubricDimension[];
  threshold_complete: number;
}

export interface SingleReport {
  drill_id: number;
  question_id: number;
  question_text: string;
  category: Category;
  transcript: TranscriptTurn[];
  rubric: Rubric;
  rubric_scores: Record<string, number>;
  total_score: number;
  exit_type: ExitType;
  scenario_switch_count: number;
  prompt_mode_count: number;
  followup_rounds: number;
  exemplar_answer: string;
  improvement_suggestions: string[];
}

export interface MockSession {
  id: number;
  resume_session_id: number;
  question_ids: number[];
  current_index: number;
  drill_attempt_ids: number[];
  status: "active" | "ended";
}

export interface MockReport {
  mock_session_id: number;
  total_avg_score: number;
  category_avg_scores: Record<string, number>;
  highlights: { question_id: number; question_text: string; score: number }[];
  weaknesses: { dimension: string; avg: number; from_categories: Category[] }[];
  next_steps: string[];
  drill_summaries: {
    drill_id: number;
    question_id: number;
    question_text: string;
    category: Category;
    total_score: number;
  }[];
}
```

- [ ] **Step 2: API client methods**

Replace `frontend/src/lib/api.ts`:

```ts
import type {
  DrillResponse,
  MockReport,
  MockSession,
  Question,
  ResumeUploadResponse,
  SingleReport,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function jsonRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json() as Promise<T>;
}

export async function uploadResume(
  file: File,
  role_type: string,
  jd_text?: string,
  company_name?: string
): Promise<ResumeUploadResponse> {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("role_type", role_type);
  if (jd_text) fd.append("jd_text", jd_text);
  if (company_name) fd.append("company_name", company_name);
  const r = await fetch(`${BASE}/resume`, { method: "POST", body: fd });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}

export async function generateQuestions(resume_session_id: number): Promise<Question[]> {
  return jsonRequest("/questions/generate", {
    method: "POST",
    body: JSON.stringify({ resume_session_id }),
  });
}

export async function listQuestions(
  resume_session_id: number,
  filters?: { category?: string; status?: string }
): Promise<Question[]> {
  const p = new URLSearchParams({ resume_session_id: String(resume_session_id) });
  if (filters?.category) p.set("category", filters.category);
  if (filters?.status) p.set("status", filters.status);
  return jsonRequest(`/questions?${p.toString()}`);
}

export async function startDrill(question_id: number): Promise<DrillResponse> {
  return jsonRequest("/drill", {
    method: "POST",
    body: JSON.stringify({ question_id }),
  });
}

export async function answerDrill(drill_id: number, text: string): Promise<DrillResponse> {
  return jsonRequest(`/drill/${drill_id}/answer`, {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

export async function getDrillReport(drill_id: number): Promise<SingleReport> {
  return jsonRequest(`/reports/drill/${drill_id}`);
}

export async function startMock(resume_session_id: number): Promise<MockSession> {
  return jsonRequest("/mock", {
    method: "POST",
    body: JSON.stringify({ resume_session_id }),
  });
}

export async function getMock(mock_id: number): Promise<MockSession> {
  return jsonRequest(`/mock/${mock_id}`);
}

export async function getMockReport(mock_id: number): Promise<MockReport> {
  return jsonRequest(`/reports/mock/${mock_id}`);
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): TS types + complete API client surface"
```

---

### Task 3.2: Upload page

**Files:**
- Modify: `frontend/src/app/page.tsx`
- Create: `frontend/src/components/upload-zone.tsx`
- Create: `frontend/src/components/role-selector.tsx`

- [ ] **Step 1: RoleSelector component**

`frontend/src/components/role-selector.tsx`:

```tsx
"use client";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import type { RoleType } from "@/lib/types";

const ROLES: { value: RoleType; label: string; tagline: string }[] = [
  { value: "pm", label: "产品", tagline: "PM / 产品运营 / AI 产品" },
  { value: "data", label: "数据", tagline: "数据分析 / DS / ML" },
  { value: "ai", label: "AI", tagline: "AI 产品 / AI 工程" },
  { value: "other", label: "其他岗位", tagline: "通用兜底" },
];

export function RoleSelector({
  value,
  onChange,
}: {
  value: RoleType | null;
  onChange: (v: RoleType) => void;
}) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {ROLES.map((r) => (
        <Button
          key={r.value}
          variant={value === r.value ? "default" : "outline"}
          className={cn("h-auto flex flex-col items-start py-4 px-4", value === r.value && "ring-2 ring-primary")}
          onClick={() => onChange(r.value)}
        >
          <span className="font-semibold">{r.label}</span>
          <span className="text-xs text-muted-foreground mt-1">{r.tagline}</span>
        </Button>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: UploadZone component**

`frontend/src/components/upload-zone.tsx`:

```tsx
"use client";
import { useState } from "react";
import { cn } from "@/lib/utils";

export function UploadZone({ onFile }: { onFile: (file: File) => void }) {
  const [dragOver, setDragOver] = useState(false);

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        const f = e.dataTransfer.files?.[0];
        if (f && f.type === "application/pdf") onFile(f);
      }}
      className={cn(
        "border-2 border-dashed rounded-lg p-10 text-center transition cursor-pointer",
        dragOver ? "border-primary bg-primary/5" : "border-border"
      )}
    >
      <input
        type="file"
        accept="application/pdf"
        id="resume-file"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onFile(f);
        }}
      />
      <label htmlFor="resume-file" className="cursor-pointer block">
        <p className="font-medium">拖入简历 PDF 或点击上传</p>
        <p className="text-xs text-muted-foreground mt-2">
          系统会智能解析项目 / 工作经历，反向挖出面试题
        </p>
      </label>
    </div>
  );
}
```

- [ ] **Step 3: Upload page**

Replace `frontend/src/app/page.tsx`:

```tsx
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { RoleSelector } from "@/components/role-selector";
import { UploadZone } from "@/components/upload-zone";
import { generateQuestions, uploadResume } from "@/lib/api";
import type { RoleType } from "@/lib/types";

export default function Home() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [role, setRole] = useState<RoleType | null>(null);
  const [jd, setJD] = useState("");
  const [company, setCompany] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function start() {
    if (!file || !role) {
      setError("请上传简历并选择岗位");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const rs = await uploadResume(file, role, jd || undefined, company || undefined);
      await generateQuestions(rs.id);
      router.push(`/library?session=${rs.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="container max-w-3xl mx-auto py-12 space-y-8">
      <div>
        <h1 className="text-3xl font-bold">MockInterview Agent</h1>
        <p className="mt-2 text-muted-foreground">
          垂直岗位 AI 面试演练 · 简历反向挖题 · 多轮追问
        </p>
      </div>

      <section className="space-y-3">
        <Label>1. 上传简历 (PDF)</Label>
        <UploadZone onFile={setFile} />
        {file && <p className="text-sm text-muted-foreground">已选择：{file.name}</p>}
      </section>

      <section className="space-y-3">
        <Label>2. 目标岗位</Label>
        <RoleSelector value={role} onChange={setRole} />
      </section>

      <section className="space-y-3">
        <Label htmlFor="jd">3. JD（可选，提供则出题更精准）</Label>
        <Textarea
          id="jd"
          rows={5}
          placeholder="粘贴 JD 文本……"
          value={jd}
          onChange={(e) => setJD(e.target.value)}
        />
      </section>

      <section className="space-y-3">
        <Label htmlFor="company">4. 公司名（可选）</Label>
        <Input
          id="company"
          placeholder="字节跳动 / Shopee / ……"
          value={company}
          onChange={(e) => setCompany(e.target.value)}
        />
      </section>

      {error && <p className="text-destructive text-sm">{error}</p>}

      <Button size="lg" onClick={start} disabled={busy || !file || !role}>
        {busy ? "解析中…可能需要 30-60 秒" : "开始挖题"}
      </Button>
    </main>
  );
}
```

- [ ] **Step 4: Manual test**

```bash
# Backend running on :8000, frontend on :3000.
# Drag a PDF, pick role, optionally JD, click "开始挖题".
# Expected: redirect to /library?session=<id> (404 for now — OK, library page next task).
```

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): upload page (resume + role + JD + company)"
```

---

### Task 3.3: Library page (题库总览)

**Files:**
- Create: `frontend/src/app/library/page.tsx`
- Create: `frontend/src/components/question-card.tsx`
- Create: `frontend/src/components/library-stats-bar.tsx`

- [ ] **Step 1: QuestionCard**

`frontend/src/components/question-card.tsx`:

```tsx
"use client";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import type { Question } from "@/lib/types";

const STATUS_LABEL: Record<Question["status"], string> = {
  not_practiced: "未练",
  practiced: "已练",
  needs_redo: "待重练",
  improved: "已改进",
  skipped: "已跳过",
};

const STATUS_VARIANT: Record<Question["status"], "default" | "secondary" | "destructive" | "outline"> = {
  not_practiced: "outline",
  practiced: "default",
  needs_redo: "destructive",
  improved: "default",
  skipped: "secondary",
};

export function QuestionCard({ q }: { q: Question }) {
  return (
    <Link href={`/drill/${q.id}`} className="block">
      <Card className="hover:border-primary transition cursor-pointer h-full">
        <CardHeader className="space-y-2">
          <div className="flex gap-2">
            <Badge variant="secondary">{q.category}</Badge>
            <Badge variant="outline">{q.difficulty}</Badge>
            <Badge variant={STATUS_VARIANT[q.status]}>{STATUS_LABEL[q.status]}</Badge>
          </div>
          <p className="font-medium leading-snug line-clamp-3">{q.text}</p>
        </CardHeader>
        <CardContent className="text-xs text-muted-foreground line-clamp-2">{q.source}</CardContent>
        <CardFooter className="text-xs text-muted-foreground flex justify-between">
          <span>最高分 {q.best_score ?? "—"} / 12</span>
          <span>{q.last_attempt_at ? new Date(q.last_attempt_at).toLocaleDateString() : "未练习"}</span>
        </CardFooter>
      </Card>
    </Link>
  );
}
```

- [ ] **Step 2: Stats bar**

`frontend/src/components/library-stats-bar.tsx`:

```tsx
import type { Question } from "@/lib/types";
import { Card } from "@/components/ui/card";

export function LibraryStatsBar({ questions }: { questions: Question[] }) {
  const total = questions.length;
  const notPracticed = questions.filter((q) => q.status === "not_practiced").length;
  const practiced = questions.filter((q) => q.status === "practiced" || q.status === "improved").length;
  const needsRedo = questions.filter((q) => q.status === "needs_redo").length;
  return (
    <Card className="p-4">
      <div className="flex gap-6 text-sm">
        <div>
          <div className="text-2xl font-bold">{total}</div>
          <div className="text-muted-foreground">题库</div>
        </div>
        <div>
          <div className="text-2xl font-bold">{notPracticed}</div>
          <div className="text-muted-foreground">未练</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-green-600">{practiced}</div>
          <div className="text-muted-foreground">已练</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-destructive">{needsRedo}</div>
          <div className="text-muted-foreground">待重练</div>
        </div>
      </div>
    </Card>
  );
}
```

- [ ] **Step 3: Library page**

`frontend/src/app/library/page.tsx`:

```tsx
"use client";
import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { LibraryStatsBar } from "@/components/library-stats-bar";
import { QuestionCard } from "@/components/question-card";
import { listQuestions } from "@/lib/api";
import type { Question } from "@/lib/types";

const CATS = ["T1", "T2", "T3", "T4", "T5"] as const;

export default function LibraryPage() {
  const sp = useSearchParams();
  const router = useRouter();
  const sessionId = Number(sp.get("session"));
  const [questions, setQuestions] = useState<Question[]>([]);
  const [filter, setFilter] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!sessionId) return;
    listQuestions(sessionId).then((qs) => {
      setQuestions(qs);
      setLoading(false);
    });
  }, [sessionId]);

  const visible = filter ? questions.filter((q) => q.category === filter) : questions;

  return (
    <main className="container max-w-6xl mx-auto py-8 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">我的题库</h1>
        <Button onClick={() => router.push(`/mock?session=${sessionId}`)}>开始模拟面试</Button>
      </div>

      <LibraryStatsBar questions={questions} />

      <div className="flex gap-2">
        <Button variant={filter === null ? "default" : "outline"} size="sm" onClick={() => setFilter(null)}>
          全部
        </Button>
        {CATS.map((c) => (
          <Button
            key={c}
            variant={filter === c ? "default" : "outline"}
            size="sm"
            onClick={() => setFilter(c)}
          >
            {c}
          </Button>
        ))}
      </div>

      {loading ? (
        <p className="text-muted-foreground">加载题库……</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {visible.map((q) => (
            <QuestionCard key={q.id} q={q} />
          ))}
        </div>
      )}
    </main>
  );
}
```

- [ ] **Step 4: Manual test + commit**

```bash
# Verify: upload → library shows 12 cards, filter by T1 → 4 cards.
git add frontend/
git commit -m "feat(frontend): library page with stats bar + category filter"
```

---

### Task 3.4: Drill page (chat UI)

**Files:**
- Create: `frontend/src/app/drill/[id]/page.tsx`
- Create: `frontend/src/components/chat-interface.tsx`

- [ ] **Step 1: ChatInterface component**

`frontend/src/components/chat-interface.tsx`:

```tsx
"use client";
import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import type { TranscriptTurn } from "@/lib/types";

export function ChatInterface({ transcript }: { transcript: TranscriptTurn[] }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.scrollTo({ top: ref.current.scrollHeight, behavior: "smooth" });
  }, [transcript]);

  return (
    <div ref={ref} className="flex-1 overflow-y-auto space-y-3 p-4 border rounded-lg max-h-[60vh]">
      {transcript.map((t, i) => (
        <div key={i} className={cn("flex", t.role === "user" ? "justify-end" : "justify-start")}>
          <div
            className={cn(
              "max-w-[80%] rounded-lg px-4 py-2 text-sm whitespace-pre-wrap",
              t.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted",
              t.kind === "scenario_switch" && "ring-2 ring-amber-400/60",
              t.kind === "prompt_mode" && "ring-2 ring-blue-400/60"
            )}
          >
            {t.kind === "scenario_switch" && (
              <div className="text-xs font-semibold opacity-70 mb-1">↔ 换场景</div>
            )}
            {t.kind === "prompt_mode" && (
              <div className="text-xs font-semibold opacity-70 mb-1">💡 思考框架</div>
            )}
            {t.text}
          </div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Drill page**

`frontend/src/app/drill/[id]/page.tsx`:

```tsx
"use client";
import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ChatInterface } from "@/components/chat-interface";
import { answerDrill, startDrill } from "@/lib/api";
import type { DrillResponse } from "@/lib/types";

export default function DrillPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const questionId = Number(id);
  const router = useRouter();
  const [drill, setDrill] = useState<DrillResponse | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    startDrill(questionId).then(setDrill);
  }, [questionId]);

  async function send() {
    if (!drill || !input.trim()) return;
    setBusy(true);
    try {
      const next = await answerDrill(drill.drill_id, input);
      setDrill(next);
      setInput("");
      if (next.status === "ended") {
        setTimeout(() => router.push(`/report/${next.drill_id}`), 1200);
      }
    } finally {
      setBusy(false);
    }
  }

  if (!drill) {
    return <main className="container py-12">起题中……</main>;
  }

  return (
    <main className="container max-w-3xl mx-auto py-8 space-y-4 flex flex-col h-[90vh]">
      <h1 className="text-lg font-bold">单题演练</h1>
      <ChatInterface transcript={drill.transcript} />
      <div className="space-y-2">
        <Textarea
          rows={4}
          placeholder="作答……（可输入 跳过 / 我答完了 / 没思路 / 换个例子）"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={busy || drill.status === "ended"}
        />
        <div className="flex gap-2 justify-between">
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={() => setInput("跳过")}>跳过</Button>
            <Button size="sm" variant="outline" onClick={() => setInput("能换个例子吗")}>换场景</Button>
            <Button size="sm" variant="outline" onClick={() => setInput("没思路，给点提示")}>求提示</Button>
            <Button size="sm" variant="outline" onClick={() => setInput("我答完了")}>结束</Button>
          </div>
          <Button onClick={send} disabled={busy || drill.status === "ended"}>
            {busy ? "评估中…" : "发送"}
          </Button>
        </div>
      </div>
      {drill.status === "ended" && (
        <p className="text-sm text-muted-foreground">本题结束，即将跳转报告……</p>
      )}
    </main>
  );
}
```

- [ ] **Step 3: Manual test + commit**

```bash
# Pick a question from library → drill page renders, send normal answer + "跳过" + "换个例子" + "我答完了"
git add frontend/
git commit -m "feat(frontend): drill page with chat UI + quick actions (跳过/换场景/提示/结束)"
```

---

### Task 3.5: Single-question report page (radar chart)

**Files:**
- Create: `frontend/src/app/report/[id]/page.tsx`
- Create: `frontend/src/components/radar-chart.tsx`
- Create: `frontend/src/components/transcript-view.tsx`
- Modify: `frontend/package.json` (add `recharts`)

- [ ] **Step 1: Install recharts**

```bash
cd frontend
pnpm add recharts
```

- [ ] **Step 2: Radar chart component**

`frontend/src/components/radar-chart.tsx`:

```tsx
"use client";
import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart as ReRadar,
  ResponsiveContainer,
} from "recharts";
import type { Rubric } from "@/lib/types";

export function RadarChart({
  rubric,
  scores,
}: {
  rubric: Rubric;
  scores: Record<string, number>;
}) {
  const data = rubric.dimensions.map((d) => ({
    dim: d.label,
    score: scores[d.key] ?? 0,
    fullMark: 3,
  }));
  return (
    <ResponsiveContainer width="100%" height={280}>
      <ReRadar data={data}>
        <PolarGrid />
        <PolarAngleAxis dataKey="dim" />
        <PolarRadiusAxis angle={90} domain={[0, 3]} />
        <Radar name="得分" dataKey="score" fillOpacity={0.5} />
      </ReRadar>
    </ResponsiveContainer>
  );
}
```

- [ ] **Step 3: Transcript view**

`frontend/src/components/transcript-view.tsx`:

```tsx
import { ChatInterface } from "@/components/chat-interface";
import type { TranscriptTurn } from "@/lib/types";

export function TranscriptView({ transcript }: { transcript: TranscriptTurn[] }) {
  return (
    <div className="border rounded-lg">
      <ChatInterface transcript={transcript} />
    </div>
  );
}
```

- [ ] **Step 4: Report page**

`frontend/src/app/report/[id]/page.tsx`:

```tsx
"use client";
import { use, useEffect, useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { RadarChart } from "@/components/radar-chart";
import { TranscriptView } from "@/components/transcript-view";
import { getDrillReport } from "@/lib/api";
import type { SingleReport } from "@/lib/types";

const RATING = (score: number) => {
  if (score >= 11) return "优秀";
  if (score >= 9) return "良好";
  if (score >= 6) return "合格";
  return "需改进";
};

export default function ReportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const drillId = Number(id);
  const [report, setReport] = useState<SingleReport | null>(null);

  useEffect(() => {
    getDrillReport(drillId).then(setReport);
  }, [drillId]);

  if (!report) return <main className="container py-12">加载报告……</main>;

  return (
    <main className="container max-w-4xl mx-auto py-8 space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <Badge variant="secondary">{report.category}</Badge>
          <h1 className="text-xl font-bold mt-2">{report.question_text}</h1>
          <p className="text-xs text-muted-foreground mt-1">
            退出方式: {report.exit_type} · 追问 {report.followup_rounds} 轮
            {report.scenario_switch_count > 0 && ` · 场景切换 ${report.scenario_switch_count} 次`}
            {report.prompt_mode_count > 0 && ` · 求提示 ${report.prompt_mode_count} 次`}
          </p>
        </div>
        <Link href="/library">
          <Button variant="outline">返回题库</Button>
        </Link>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <h2 className="font-semibold">Rubric 评分</h2>
            <p className="text-2xl font-bold">
              {report.total_score} / 12 · {RATING(report.total_score)}
            </p>
          </CardHeader>
          <CardContent>
            <RadarChart rubric={report.rubric} scores={report.rubric_scores} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <h2 className="font-semibold">改进建议</h2>
          </CardHeader>
          <CardContent>
            <ol className="list-decimal pl-5 space-y-2 text-sm">
              {report.improvement_suggestions.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ol>
          </CardContent>
        </Card>
      </div>

      {report.exemplar_answer && (
        <Card>
          <CardHeader>
            <h2 className="font-semibold">范例答案（rubric 高分版本）</h2>
          </CardHeader>
          <CardContent className="text-sm whitespace-pre-wrap">{report.exemplar_answer}</CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <h2 className="font-semibold">完整对话</h2>
        </CardHeader>
        <CardContent>
          <TranscriptView transcript={report.transcript} />
        </CardContent>
      </Card>
    </main>
  );
}
```

- [ ] **Step 5: Manual test + commit**

```bash
# Drill 一道完整题 → 自动跳转 /report/{id} → 看雷达图、改进建议、范例答案、transcript
git add frontend/
git commit -m "feat(frontend): single-question report page with radar chart + transcript"
```

---

### Task 3.6: Mock interview mode (5 题串联)

**Files:**
- Create: `backend/src/mockinterview/db/models.py` (add `MockSession` table)
- Create: `backend/src/mockinterview/routes/mock.py`
- Create: `backend/src/mockinterview/agent/mock_aggregator.py`
- Create: `backend/tests/test_routes_mock.py`
- Create: `frontend/src/app/mock/page.tsx`
- Create: `frontend/src/app/mock/[id]/page.tsx`

Spec §1.1 / §6.3 — A 模式：从题库挑 5 道未练题串联，结束后聚合报告。

- [ ] **Step 1: Add MockSession SQLModel**

Append to `backend/src/mockinterview/db/models.py`:

```python
class MockSession(SQLModel, table=True):
    __tablename__ = "mock_session"
    id: int | None = Field(default=None, primary_key=True)
    resume_session_id: int = Field(foreign_key="resume_session.id", index=True)
    question_ids: list[int] = Field(sa_column=Column(JSON))
    drill_attempt_ids: list[int] = Field(default_factory=list, sa_column=Column(JSON))
    current_index: int = 0
    status: str = "active"  # active | ended
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: datetime | None = None
```

- [ ] **Step 2: Aggregator module**

`backend/src/mockinterview/agent/mock_aggregator.py`:

```python
from collections import defaultdict
from typing import Any

from sqlmodel import Session, select

from mockinterview.agent.rubrics import load_rubric
from mockinterview.db.models import DrillAttempt, MockSession, Question


def aggregate_mock(db: Session, mock_id: int) -> dict[str, Any]:
    ms = db.get(MockSession, mock_id)
    if not ms:
        raise ValueError("mock session not found")
    drills = db.exec(
        select(DrillAttempt).where(DrillAttempt.id.in_(ms.drill_attempt_ids))
    ).all()
    drill_summaries: list[dict[str, Any]] = []
    cat_scores: dict[str, list[int]] = defaultdict(list)
    dim_scores: dict[str, list[int]] = defaultdict(list)
    dim_to_cat: dict[str, set[str]] = defaultdict(set)
    highlights: list[dict[str, Any]] = []
    total_scores: list[int] = []

    for d in drills:
        q = db.get(Question, d.question_id)
        drill_summaries.append(
            {
                "drill_id": d.id,
                "question_id": q.id,
                "question_text": q.text,
                "category": q.category,
                "total_score": d.total_score,
            }
        )
        cat_scores[q.category].append(d.total_score)
        total_scores.append(d.total_score)
        if d.total_score >= 9:
            highlights.append(
                {"question_id": q.id, "question_text": q.text, "score": d.total_score}
            )
        for dim_key, score in (d.rubric_scores_json or {}).items():
            dim_scores[dim_key].append(score)
            dim_to_cat[dim_key].add(q.category)

    weaknesses = [
        {
            "dimension": k,
            "avg": sum(v) / len(v),
            "from_categories": sorted(dim_to_cat[k]),
        }
        for k, v in dim_scores.items()
        if v and (sum(v) / len(v)) < 2.0
    ]
    weaknesses.sort(key=lambda w: w["avg"])

    next_steps: list[str] = []
    for w in weaknesses[:3]:
        next_steps.append(
            f"重点重练 {', '.join(w['from_categories'])} 题型中维度 「{w['dimension']}」（当前均值 {w['avg']:.1f}/3）"
        )
    if not next_steps:
        next_steps = ["整体表现良好，可挑战更难类目（T2 / T3 / T4）"]

    return {
        "mock_session_id": mock_id,
        "total_avg_score": sum(total_scores) / len(total_scores) if total_scores else 0.0,
        "category_avg_scores": {k: sum(v) / len(v) for k, v in cat_scores.items()},
        "highlights": highlights,
        "weaknesses": weaknesses[:5],
        "next_steps": next_steps,
        "drill_summaries": drill_summaries,
    }
```

- [ ] **Step 3: Mock routes**

`backend/src/mockinterview/routes/mock.py`:

```python
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from mockinterview.agent.mock_aggregator import aggregate_mock
from mockinterview.db.models import (
    DrillAttempt,
    MockSession,
    Question,
    QuestionStatus,
    ResumeSession,
)
from mockinterview.db.session import get_session

router = APIRouter(prefix="/mock", tags=["mock"])

MOCK_SIZE = 5


class StartBody(BaseModel):
    resume_session_id: int


@router.post("")
def start_mock(body: StartBody, db: Session = Depends(get_session)):
    rs = db.get(ResumeSession, body.resume_session_id)
    if not rs:
        raise HTTPException(404, "resume_session not found")
    # Pick 5 distinct categories preferring not-yet-practiced
    qs = db.exec(
        select(Question).where(Question.resume_session_id == rs.id).order_by(
            Question.status, Question.id
        )
    ).all()
    chosen: list[Question] = []
    seen_cats: set[str] = set()
    for q in qs:
        if len(chosen) >= MOCK_SIZE:
            break
        if q.category not in seen_cats:
            chosen.append(q)
            seen_cats.add(q.category)
    while len(chosen) < MOCK_SIZE and len(chosen) < len(qs):
        for q in qs:
            if q not in chosen:
                chosen.append(q)
                if len(chosen) == MOCK_SIZE:
                    break
    ms = MockSession(
        resume_session_id=rs.id,
        question_ids=[q.id for q in chosen],
    )
    db.add(ms)
    db.commit()
    db.refresh(ms)
    return ms


@router.get("/{mock_id}")
def get_mock(mock_id: int, db: Session = Depends(get_session)):
    ms = db.get(MockSession, mock_id)
    if not ms:
        raise HTTPException(404, "not found")
    return ms


class AdvanceBody(BaseModel):
    drill_attempt_id: int


@router.post("/{mock_id}/advance")
def advance_mock(mock_id: int, body: AdvanceBody, db: Session = Depends(get_session)):
    ms = db.get(MockSession, mock_id)
    if not ms:
        raise HTTPException(404, "not found")
    if ms.status == "ended":
        return ms
    d = db.get(DrillAttempt, body.drill_attempt_id)
    if not d:
        raise HTTPException(404, "drill_attempt not found")
    if body.drill_attempt_id not in ms.drill_attempt_ids:
        ms.drill_attempt_ids = ms.drill_attempt_ids + [body.drill_attempt_id]
    ms.current_index = ms.current_index + 1
    if ms.current_index >= len(ms.question_ids):
        ms.status = "ended"
        ms.ended_at = datetime.utcnow()
    db.add(ms)
    db.commit()
    db.refresh(ms)
    return ms


@router.get("/{mock_id}/report")
def mock_report(mock_id: int, db: Session = Depends(get_session)):
    ms = db.get(MockSession, mock_id)
    if not ms:
        raise HTTPException(404, "not found")
    return aggregate_mock(db, mock_id)
```

Also add a corresponding `/reports/mock/{mock_id}` alias by adding to `reports.py`:

```python
@router.get("/mock/{mock_id}")
def mock_report_alias(mock_id: int, db: Session = Depends(get_session)):
    return aggregate_mock(db, mock_id)
```

(With import: `from mockinterview.agent.mock_aggregator import aggregate_mock`.)

- [ ] **Step 4: Wire into main + tests**

```python
from mockinterview.routes import mock as mock_routes
app.include_router(mock_routes.router)
```

`backend/tests/test_routes_mock.py`:

```python
from sqlmodel import Session

from mockinterview.db.models import Question, ResumeSession
from mockinterview.db.session import engine


def _seed_with_questions():
    with Session(engine) as s:
        rs = ResumeSession(user_id=1, resume_json={}, role_type="pm")
        s.add(rs)
        s.commit()
        s.refresh(rs)
        for i, c in enumerate(["T1", "T2", "T3", "T4", "T5", "T1", "T2"]):
            s.add(
                Question(
                    resume_session_id=rs.id,
                    category=c,
                    text=f"Q{i}",
                    source="x",
                    difficulty="medium",
                )
            )
        s.commit()
        return rs.id


def test_start_mock_picks_5_distinct_categories(client):
    sid = _seed_with_questions()
    r = client.post("/mock", json={"resume_session_id": sid})
    body = r.json()
    assert len(body["question_ids"]) == 5


def test_advance_increments(client):
    sid = _seed_with_questions()
    mid = client.post("/mock", json={"resume_session_id": sid}).json()["id"]
    # Use a drill attempt id of 1 (synthetic — works because we just need the link, not eval)
    # First create a drill attempt to satisfy FK
    from sqlmodel import Session
    from mockinterview.db.models import DrillAttempt, ExitType
    from mockinterview.db.session import engine
    with Session(engine) as s:
        d = DrillAttempt(
            question_id=1,
            transcript_json=[],
            rubric_scores_json={"a": 1},
            total_score=4,
            exit_type=ExitType.SOFT,
            exemplar_answer="",
            improvement_suggestions=[],
        )
        s.add(d)
        s.commit()
        s.refresh(d)
        did = d.id
    r = client.post(f"/mock/{mid}/advance", json={"drill_attempt_id": did})
    assert r.json()["current_index"] == 1
```

- [ ] **Step 5: Frontend mock pages**

`frontend/src/app/mock/page.tsx` (entry — pick session, start mock, redirect):

```tsx
"use client";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { startMock } from "@/lib/api";

export default function MockEntry() {
  const sp = useSearchParams();
  const router = useRouter();
  const sessionId = Number(sp.get("session"));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) {
      setError("缺少 session 参数");
      return;
    }
    startMock(sessionId)
      .then((ms) => router.push(`/mock/${ms.id}`))
      .catch((e) => setError(String(e)));
  }, [sessionId, router]);

  return <main className="container py-12">{error ?? "起会话中……"}</main>;
}
```

`frontend/src/app/mock/[id]/page.tsx` (driver: walk through 5 questions, after each drill, advance + go to next; at end, go to mock report):

```tsx
"use client";
import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ChatInterface } from "@/components/chat-interface";
import { answerDrill, getMock, startDrill } from "@/lib/api";
import type { DrillResponse, MockSession } from "@/lib/types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function advanceMock(mockId: number, drillAttemptId: number): Promise<MockSession> {
  const r = await fetch(`${BASE}/mock/${mockId}/advance`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ drill_attempt_id: drillAttemptId }),
  });
  return r.json();
}

export default function MockPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const mockId = Number(id);
  const router = useRouter();
  const [mock, setMock] = useState<MockSession | null>(null);
  const [drill, setDrill] = useState<DrillResponse | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getMock(mockId).then(setMock);
  }, [mockId]);

  useEffect(() => {
    if (!mock) return;
    if (mock.status === "ended") {
      router.push(`/mock/${mockId}/report`);
      return;
    }
    const qid = mock.question_ids[mock.current_index];
    startDrill(qid).then(setDrill);
  }, [mock, mockId, router]);

  async function send() {
    if (!drill || !mock || !input.trim()) return;
    setBusy(true);
    try {
      const next = await answerDrill(drill.drill_id, input);
      setDrill(next);
      setInput("");
      if (next.status === "ended") {
        const updated = await advanceMock(mockId, next.drill_id);
        setMock(updated);
        setDrill(null);
      }
    } finally {
      setBusy(false);
    }
  }

  if (!mock) return <main className="container py-12">加载……</main>;

  return (
    <main className="container max-w-3xl mx-auto py-8 space-y-4 flex flex-col h-[90vh]">
      <h1 className="text-lg font-bold">
        模拟面试 · 题 {mock.current_index + 1} / {mock.question_ids.length}
      </h1>
      {drill ? (
        <>
          <ChatInterface transcript={drill.transcript} />
          <Textarea
            rows={4}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={busy || drill.status === "ended"}
            placeholder="作答……"
          />
          <Button onClick={send} disabled={busy || drill.status === "ended"}>
            {busy ? "评估中…" : "发送"}
          </Button>
        </>
      ) : (
        <p>下一题加载中……</p>
      )}
    </main>
  );
}
```

- [ ] **Step 6: Manual test + commit**

```bash
uv run pytest tests/test_routes_mock.py
git add backend/ frontend/
git commit -m "feat: mock interview mode (5 题串联) + aggregator"
```

---

### Task 3.7: Mock report page

**Files:**
- Create: `frontend/src/app/mock/[id]/report/page.tsx`
- Create: `frontend/src/components/score-bar-chart.tsx`

- [ ] **Step 1: Bar chart**

`frontend/src/components/score-bar-chart.tsx`:

```tsx
"use client";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export function ScoreBarChart({
  data,
}: {
  data: { label: string; score: number }[];
}) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="label" tick={{ fontSize: 11 }} />
        <YAxis domain={[0, 12]} />
        <Tooltip />
        <Bar dataKey="score" />
      </BarChart>
    </ResponsiveContainer>
  );
}
```

- [ ] **Step 2: Mock report page**

`frontend/src/app/mock/[id]/report/page.tsx`:

```tsx
"use client";
import { use, useEffect, useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { ScoreBarChart } from "@/components/score-bar-chart";
import { getMockReport } from "@/lib/api";
import type { MockReport } from "@/lib/types";

export default function MockReportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const mockId = Number(id);
  const [report, setReport] = useState<MockReport | null>(null);

  useEffect(() => {
    getMockReport(mockId).then(setReport);
  }, [mockId]);

  if (!report) return <main className="container py-12">加载……</main>;

  const barData = report.drill_summaries.map((s) => ({
    label: `${s.category}·#${s.question_id}`,
    score: s.total_score,
  }));

  return (
    <main className="container max-w-4xl mx-auto py-8 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">整套面试报告</h1>
          <p className="text-muted-foreground mt-1">
            平均分 {report.total_avg_score.toFixed(1)} / 12
          </p>
        </div>
        <Link href="/library">
          <Button variant="outline">返回题库</Button>
        </Link>
      </div>

      <Card>
        <CardHeader>
          <h2 className="font-semibold">每题得分</h2>
        </CardHeader>
        <CardContent>
          <ScoreBarChart data={barData} />
        </CardContent>
      </Card>

      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <h2 className="font-semibold">高光时刻</h2>
          </CardHeader>
          <CardContent className="space-y-2">
            {report.highlights.length === 0 ? (
              <p className="text-sm text-muted-foreground">本场没有满分题——下次冲刺！</p>
            ) : (
              report.highlights.map((h) => (
                <div key={h.question_id} className="text-sm">
                  <Badge>{h.score}/12</Badge>
                  <span className="ml-2">{h.question_text}</span>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <h2 className="font-semibold">短板维度</h2>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {report.weaknesses.length === 0 ? (
              <p className="text-muted-foreground">无明显短板</p>
            ) : (
              report.weaknesses.map((w) => (
                <div key={w.dimension}>
                  <span className="font-medium">{w.dimension}</span>
                  <span className="text-muted-foreground"> · {w.avg.toFixed(1)} / 3 · 来自 {w.from_categories.join(", ")}</span>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <h2 className="font-semibold">下一步建议</h2>
        </CardHeader>
        <CardContent>
          <ul className="list-disc pl-5 space-y-1 text-sm">
            {report.next_steps.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="font-semibold">逐题汇总</h2>
        </CardHeader>
        <CardContent className="space-y-2">
          {report.drill_summaries.map((s) => (
            <Link key={s.drill_id} href={`/report/${s.drill_id}`} className="block">
              <div className="flex justify-between items-center border rounded p-3 hover:bg-muted text-sm">
                <span>
                  <Badge variant="secondary">{s.category}</Badge>{" "}
                  {s.question_text}
                </span>
                <span className="font-bold">{s.total_score} / 12</span>
              </div>
            </Link>
          ))}
        </CardContent>
      </Card>
    </main>
  );
}
```

- [ ] **Step 3: Manual test + commit**

```bash
git add frontend/
git commit -m "feat(frontend): mock interview report page with bar chart + highlights/weaknesses"
```

---

### Phase 3 Wrap-up

- [ ] **W3 deliverable: full local e2e walkthrough**

```bash
# Backend: uv run uvicorn mockinterview.main:app --reload
# Frontend: cd frontend && pnpm dev
# Browser: http://localhost:3000
# Walk:
#   1. Upload PDF + select role + paste JD → 题库
#   2. Click 一道 T1 题 → drill page → 完整作答 → soft exit → 报告页（雷达图）
#   3. 回题库 → 点"开始模拟面试" → 5 题连答 → 整套报告页（bar chart + 短板）
```

- [ ] **W3 tag**

```bash
git tag -a w3-done -m "Week 3: full local UI flow complete"
```

---

## Phase 4 / Week 4 — 评估 + 部署 + 收尾

**Phase Goal**: 评估证明垂直化价值（vs 裸 Claude 胜率）、部署上线、产出简历金句和小红书素材。

**Phase Deliverable**: 生产环境可访问 URL、`eval/reports/<date>.md` 评估报告、README 完整、简历金句一份、小红书 4 条进度内容齐备。

---

### Task 4.1: Eval dataset curation

**Files:**
- Create: `eval/pyproject.toml`
- Create: `eval/datasets/resumes/<name>.txt`（5 份脱敏简历，纯文本即可，不需 PDF）
- Create: `eval/datasets/jds/<role>.txt`（3 份 JD）
- Create: `eval/datasets/pairs.yaml`

简历可用：本人 1 + 朋友 PM 1 + 朋友数据 1 + 网上脱敏 AI 1 + 网上脱敏其他 1。脱敏 = 替换姓名/学校/公司具体名为占位符。

- [ ] **Step 1: Set up eval pyproject**

`eval/pyproject.toml`:

```toml
[project]
name = "eval"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "anthropic>=0.40",
  "pyyaml>=6.0",
  "pydantic>=2.9",
  "rich>=13.9",
]
```

```bash
cd eval && uv sync
```

- [ ] **Step 2: Pairs config**

`eval/datasets/pairs.yaml`:

```yaml
pairs:
  - id: pm_bytedance
    resume: self_pm.txt
    jd: pm_bytedance.txt
    role: pm
  - id: pm_no_jd
    resume: friend_pm.txt
    jd: null
    role: pm
  - id: data_shopee
    resume: friend_data.txt
    jd: data_shopee.txt
    role: data
  - id: ai_no_jd
    resume: anon_ai.txt
    jd: null
    role: ai
  - id: data_alpha
    resume: friend_data.txt
    jd: data_alpha.txt
    role: data
  - id: pm_alpha
    resume: self_pm.txt
    jd: pm_alpha.txt
    role: pm
  - id: ai_alpha
    resume: anon_ai.txt
    jd: ai_alpha.txt
    role: ai
  - id: other_no_jd
    resume: anon_other.txt
    jd: null
    role: other
```

- [ ] **Step 3: Place resume + JD files**

For each item in `pairs.yaml`, create the corresponding `.txt` file in `eval/datasets/resumes/` or `eval/datasets/jds/`. Use real (脱敏) content — mock content compromises eval validity.

- [ ] **Step 4: Commit datasets (脱敏后)**

```bash
git add eval/
git commit -m "eval: dataset curation (5 resumes × 3 JDs × 8 pairs)"
```

---

### Task 4.2: Relevance judge

**Files:**
- Create: `eval/judges/__init__.py`
- Create: `eval/judges/relevance.py`

Judge LLM 给每道生成的题打 0-3 分（与简历 + JD 的契合度）。

- [ ] **Step 1: Implement**

`eval/judges/relevance.py`:

```python
import json
from typing import Any

from anthropic import Anthropic

JUDGE_SYSTEM = """你是面试题评分员。
你会收到：
- 简历摘要
- JD 摘要（可能为空）
- 一道生成的面试题（含题面 + category + source）

按 0-3 分打分（"题与候选人简历 + JD 的契合度"）：
0 = 完全无关 / 答非所问 / 任何候选人都能答
1 = 牵强 / 浅层关联
2 = 相关 / 能用上简历素材
3 = 精准 / 引用了具体项目 outcomes 或 JD 关键能力

严格输出 JSON：
```json
{"score": int, "rationale": "<1 句"}
```
"""


def score_question(client: Anthropic, *, resume: str, jd: str, question: dict[str, Any]) -> dict:
    user = f"""简历：
{resume[:2000]}

JD：
{jd[:1200] if jd else "（未提供）"}

题：
- text: {question['text']}
- category: {question['category']}
- source: {question['source']}

请打分。"""
    resp = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=256,
        system=[{"type": "text", "text": JUDGE_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    payload = text[text.find("{") : text.rfind("}") + 1]
    return json.loads(payload)
```

- [ ] **Step 2: Commit**

```bash
git add eval/
git commit -m "eval: relevance judge (0-3 score per question)"
```

---

### Task 4.3: User simulator + drilling judge

**Files:**
- Create: `eval/simulators/__init__.py`
- Create: `eval/simulators/user_simulator.py`
- Create: `eval/judges/drilling.py`

The drilling judge requires running U-loop over a simulated "中等质量" user, then judging whether each followup hit the weakest dimension.

- [ ] **Step 1: User simulator prompt**

`eval/simulators/user_simulator.py`:

```python
import json
from typing import Any

from anthropic import Anthropic

SIM_SYSTEM = """你是一个面试中"中等质量"的求职者，扮演候选人作答。
你的特征：
- 项目经历真实（按收到的简历素材展开）
- 答题完整度大概 5-7/12 分（rubric 上）
- 偶尔遗漏 baseline / 量化归因 / 业务意义等关键维度
- 不卡壳、不主动结束、不要求换场景，老实作答（这样才能测出 agent 的追问质量）

输出严格 JSON：
```json
{"answer": "<候选人本轮回复，1-3 句>"}
```
"""


def simulate_answer(
    client: Anthropic,
    *,
    resume: str,
    question: str,
    transcript: list[dict[str, Any]],
) -> str:
    transcript_block = "\n".join(
        f"[{t['role']}] {t['text']}" for t in transcript
    )
    user = f"""你的简历素材：
{resume[:2000]}

当前对话 transcript：
{transcript_block}

请作答下一轮。"""
    resp = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=512,
        system=[{"type": "text", "text": SIM_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    payload = text[text.find("{") : text.rfind("}") + 1]
    return json.loads(payload)["answer"]
```

- [ ] **Step 2: Drilling judge**

`eval/judges/drilling.py`:

```python
import json
from typing import Any

from anthropic import Anthropic

DRILL_JUDGE_SYSTEM = """你是面试官评估官。
对一段「面试官-候选人」交互，判断面试官的某一轮追问是否击中了候选人答案最弱维度。

输入：
- 题目 + rubric 4 维度
- 上一轮候选人回答
- 面试官本轮追问

输出：
```json
{"hit_weakest": bool, "rationale": "<1 句>"}
```
"""


def judge_followup(
    client: Anthropic,
    *,
    question: str,
    rubric_dims: list[dict[str, str]],
    last_answer: str,
    followup: str,
) -> dict[str, Any]:
    dims_block = "\n".join(f"- {d['key']} ({d['label']}): {d['description']}" for d in rubric_dims)
    user = f"""题目：{question}

Rubric 维度：
{dims_block}

候选人上一轮回答：
{last_answer}

面试官本轮追问：
{followup}

请判断追问是否击中最弱维度。"""
    resp = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=256,
        system=[{"type": "text", "text": DRILL_JUDGE_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    payload = text[text.find("{") : text.rfind("}") + 1]
    return json.loads(payload)
```

- [ ] **Step 3: Commit**

```bash
git add eval/
git commit -m "eval: user simulator + drilling judge (击中最弱维度比例)"
```

---

### Task 4.4: Baseline comparison judge

**Files:**
- Create: `eval/judges/baseline_compare.py`

Same input, two outputs: (a) MockInterview Agent 出题 + 第一轮追问；(b) 裸 Claude 用通用 prompt 出题 + 第一轮追问。Judge 盲评二选一。

- [ ] **Step 1: Implement**

`eval/judges/baseline_compare.py`:

```python
import json
import random
from typing import Any

from anthropic import Anthropic

BASELINE_INTERVIEWER_SYSTEM = """你是一名面试官。基于候选人简历 + JD，向候选人提一道开放问题并准备追问。
输出严格 JSON：
```json
{"question": "<题面>", "first_followup": "<针对一个普通中等回答的追问>"}
```
"""

JUDGE_SYSTEM = """你是面试评估官，盲评两位面试官在同样输入下的表现。
评判标准：哪个面试官的题更像真实面试？哪个的追问更深、更精准？
输出严格 JSON：
```json
{"winner": "A" | "B" | "tie", "rationale": "<1-2 句>"}
```
"""


def baseline_pair(
    client: Anthropic, *, resume: str, jd: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    """生成 (baseline_pair = 裸 Claude, our_pair = MockInterview Agent) 的双输出。
    本函数只生成 baseline 部分；MockInterview Agent 部分由 run_eval.py 调用现有 backend 模块得到。"""
    user = f"""简历：
{resume[:2000]}
JD：
{jd[:1200] if jd else "（未提供）"}

请按要求输出。"""
    resp = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=512,
        system=[{"type": "text", "text": BASELINE_INTERVIEWER_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    payload = text[text.find("{") : text.rfind("}") + 1]
    return json.loads(payload)


def judge_blind(
    client: Anthropic,
    *,
    resume: str,
    jd: str,
    a_pair: dict[str, Any],
    b_pair: dict[str, Any],
) -> dict[str, Any]:
    user = f"""简历：
{resume[:1500]}
JD：
{jd[:1000] if jd else "（未提供）"}

面试官 A：
- 题：{a_pair['question']}
- 第一轮追问：{a_pair['first_followup']}

面试官 B：
- 题：{b_pair['question']}
- 第一轮追问：{b_pair['first_followup']}

请盲评谁更像真实面试官。"""
    resp = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=256,
        system=[{"type": "text", "text": JUDGE_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    payload = text[text.find("{") : text.rfind("}") + 1]
    return json.loads(payload)


def shuffled_label_pair(ours: dict[str, Any], baseline: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Returns (a_pair, b_pair, ours_label) where ours_label is 'A' or 'B' randomly."""
    if random.random() < 0.5:
        return ours, baseline, "A"
    return baseline, ours, "B"
```

- [ ] **Step 2: Commit**

```bash
git add eval/
git commit -m "eval: baseline comparison judge (vs 裸 Claude blind eval)"
```

---

### Task 4.5: run_eval.py orchestrator

**Files:**
- Create: `eval/run_eval.py`

Drives all three judges, writes Markdown report.

- [ ] **Step 1: Implement**

`eval/run_eval.py`:

```python
"""Run the full evaluation suite over pairs.yaml.

Usage:
    cd backend && uv run python ../eval/run_eval.py
    (Backend env required since we import its modules.)
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
from mockinterview.agent.resume_parser import parse_resume  # noqa: E402  (we won't use; stub)
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
    """For eval we already have plaintext resumes — bypass PDF and call Claude
    directly to structure them. Reuses the same prompt as production for
    apples-to-apples eval."""
    from mockinterview.agent.client import build_cached_system, call_json
    from mockinterview.agent.prompts.resume_parse import (
        RESUME_PARSE_SYSTEM,
        RESUME_PARSE_USER_TEMPLATE,
    )

    payload = call_json(
        system_blocks=build_cached_system([RESUME_PARSE_SYSTEM]),
        messages=[
            {"role": "user", "content": RESUME_PARSE_USER_TEMPLATE.format(resume_text=text)}
        ],
        max_tokens=4096,
    )
    return payload


def run_pair(client: Anthropic, pair: dict) -> dict:
    resume_text = (DATA / "resumes" / pair["resume"]).read_text(encoding="utf-8")
    jd_text = (
        (DATA / "jds" / pair["jd"]).read_text(encoding="utf-8") if pair["jd"] else None
    )

    console.print(f"[bold]→ pair {pair['id']}[/bold] (role={pair['role']}, jd={'yes' if jd_text else 'no'})")

    structured = parse_resume_text(resume_text)
    qlist = generate_questions(
        role=pair["role"],
        resume_json=structured,
        jd_text=jd_text,
        company_name=None,
    )

    # Relevance scoring
    rel_scores = []
    for q in qlist.questions:
        s = relevance.score_question(
            client,
            resume=resume_text,
            jd=jd_text or "",
            question={"text": q.text, "category": q.category, "source": q.source},
        )
        rel_scores.append(s["score"])

    # Drilling: run 3 simulated U-loops on T1 questions, judge each followup
    t1_qs = [q for q in qlist.questions if q.category == "T1"][:3]
    drill_hits = []
    drill_total = 0
    for q in t1_qs:
        transcript = [TranscriptTurn(role="agent", text=q.text, round=0)]
        for round_i in range(2):  # 2 followups max per pair
            sim_text = user_simulator.simulate_answer(
                client,
                resume=resume_text,
                question=q.text,
                transcript=[t.model_dump() for t in transcript],
            )
            transcript.append(TranscriptTurn(role="user", text=sim_text, round=round_i + 1))
            ev = evaluate_and_followup(
                category=q.category,
                question_text=q.text,
                transcript=transcript,
            )
            from mockinterview.agent.rubrics import load_rubric
            rubric = load_rubric(q.category)
            judge = drilling.judge_followup(
                client,
                question=q.text,
                rubric_dims=rubric["dimensions"],
                last_answer=sim_text,
                followup=ev.next_followup,
            )
            drill_hits.append(1 if judge["hit_weakest"] else 0)
            drill_total += 1
            transcript.append(
                TranscriptTurn(role="agent", text=ev.next_followup, round=round_i + 1)
            )
            if ev.total_score >= 9:
                break

    # Baseline compare on the FIRST T1 question
    if t1_qs:
        ours_pair = {"question": t1_qs[0].text, "first_followup": ""}
        # drive one round to get our first followup
        transcript = [
            TranscriptTurn(role="agent", text=t1_qs[0].text, round=0),
            TranscriptTurn(role="user", text="<placeholder mid-quality answer>", round=1),
        ]
        ev = evaluate_and_followup(
            category=t1_qs[0].category,
            question_text=t1_qs[0].text,
            transcript=transcript,
        )
        ours_pair["first_followup"] = ev.next_followup

        baseline_pair = baseline_compare.baseline_pair(
            client, resume=resume_text, jd=jd_text or ""
        )
        a, b, ours_label = baseline_compare.shuffled_label_pair(ours_pair, baseline_pair)
        verdict = baseline_compare.judge_blind(
            client, resume=resume_text, jd=jd_text or "", a_pair=a, b_pair=b
        )
        if verdict["winner"] == "tie":
            ours_won = None
        else:
            ours_won = verdict["winner"] == ours_label
    else:
        ours_won = None

    return {
        "pair": pair["id"],
        "n_questions": len(qlist.questions),
        "relevance_scores": rel_scores,
        "relevance_avg": statistics.mean(rel_scores),
        "drill_hits": drill_hits,
        "drill_hit_rate": (sum(drill_hits) / drill_total) if drill_total else None,
        "baseline_we_won": ours_won,
    }


def write_report(results: list[dict]) -> Path:
    date = datetime.now().strftime("%Y-%m-%d")
    path = OUT / f"{date}.md"
    rel_avg = statistics.mean([r["relevance_avg"] for r in results])
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


def main() -> None:
    pairs = yaml.safe_load((DATA / "pairs.yaml").read_text())["pairs"]
    client = Anthropic()
    results = [run_pair(client, p) for p in pairs]
    path = write_report(results)
    console.print(f"[green]Report written[/green]: {path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add eval/
git commit -m "eval: run_eval orchestrator (relevance + drilling + baseline) with markdown report"
```

---

### Task 4.6: Run eval + tune prompts (1-2 rounds)

- [ ] **Step 1: Run baseline eval**

```bash
cd backend
ANTHROPIC_API_KEY=... uv run python ../eval/run_eval.py
```

Expected runtime: 8 pairs × ~10 LLM calls = ~80 calls = 5-15 min depending on retries. Cost: ~$3-8 with prompt caching.

- [ ] **Step 2: Manual抽检 ~10% (1-2 pairs end-to-end)**

Open the most-recent eval report. For 2 pairs:
- Read 12 generated questions, pick the 3 lowest-scored — does the score match your judgment?
- Read 1 simulated U-loop transcript — did the agent follow up on the actual weakest spot?
- Read the baseline compare — was the verdict reasonable?

If judges seem mis-calibrated (e.g., relevance scoring 3/3 indiscriminately), adjust the judge prompt's score_levels description.

- [ ] **Step 3: Tune highest-ROI prompt**

If `relevance_avg < 2.0`: tighten `question_gen` prompt — emphasize "题面必须引用简历里的具体项目名/数字". Add 2-3 negative examples ("❌ 不要这样：'介绍一下你最有挑战的项目'").

If `drill_hit_rate < 0.6`: tighten `drill_eval` prompt — make weakest dimension selection more explicit (e.g., "在两个并列最低的维度中，选影响答题质量更大的一个"). Add 1 example.

If `baseline win rate < 0.6`: revisit `question_gen` 来源标签设计 — judges respond strongly to "反推自项目 X" vs generic "项目深挖"; make sure source ALWAYS contains the specific project name.

Re-run after each prompt change. Keep `eval/reports/<date>-r1.md`, `<date>-r2.md` for diffs.

- [ ] **Step 4: Commit prompt changes**

```bash
git add backend/ eval/
git commit -m "tune: question_gen prompt — concrete项目引用 + 反例 (eval r2: rel 2.4, win 75%)"
```

(Actual commit message reflects the actual eval delta.)

---

### Task 4.7: Backend Dockerfile + Railway deploy

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/.dockerignore`
- Create: `backend/railway.json` (or use Railway dashboard)

- [ ] **Step 1: Dockerfile**

`backend/Dockerfile`:

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

`backend/.dockerignore`:

```
.venv
__pycache__
tests
.pytest_cache
data
*.log
```

- [ ] **Step 2: Set up Railway service**

Either via dashboard or CLI:

```bash
# CLI route:
brew install railway
railway login
cd backend
railway init
railway add  # add a Volume named "data" mounted at /data
railway variables --set ANTHROPIC_API_KEY=...
railway variables --set CORS_ORIGINS='["https://<your-vercel-domain>.vercel.app"]'
railway up
```

Note: `cors_origins` config field accepts JSON-encoded list. Update `config.py`:

```python
@field_validator("cors_origins", mode="before")
@classmethod
def parse_cors(cls, v):
    if isinstance(v, str):
        return json.loads(v)
    return v
```

(Add `from pydantic import field_validator` and `import json`.)

- [ ] **Step 3: Verify deployment**

```bash
curl https://<railway-url>/health
# Expected: {"status":"ok"}
```

- [ ] **Step 4: Commit**

```bash
git add backend/
git commit -m "deploy: backend Dockerfile + Railway config"
```

---

### Task 4.8: Vercel deploy frontend

**Files:**
- Modify: `frontend/.env.local` (gitignored)
- Verify: `frontend/next.config.ts`

- [ ] **Step 1: Set env**

```bash
cd frontend
echo "NEXT_PUBLIC_API_URL=https://<railway-url>" > .env.production.local
```

- [ ] **Step 2: Vercel CLI deploy**

```bash
brew install vercel
vercel login
cd frontend
vercel --prod
# When prompted: link to a new project named "mockinterview-agent"
# Set NEXT_PUBLIC_API_URL in Vercel dashboard env vars (Production scope)
```

- [ ] **Step 3: Update Railway CORS_ORIGINS to include the Vercel URL**

```bash
railway variables --set CORS_ORIGINS='["https://mockinterview-agent.vercel.app","https://mockinterview-agent-*.vercel.app"]'
```

(Include preview URL pattern if needed.)

- [ ] **Step 4: Smoke test prod**

Full walkthrough on the live URL:
1. Upload PDF → 题库
2. Drill 一题 → 报告
3. 5 题模拟面试 → 整套报告

- [ ] **Step 5: Commit + tag**

```bash
git add frontend/
git commit -m "deploy: frontend production env config"
git tag -a v1-deployed -m "v1 production-ready"
```

---

### Task 4.9: README + 简历金句 + 小红书素材

**Files:**
- Create: `README.md`
- Create: `docs/resume-bullets.md`
- Create: `docs/xiaohongshu/<week>.md` (4 weekly posts: text + screenshots list)

- [ ] **Step 1: README**

`README.md`:

```markdown
# MockInterview Agent

垂直岗位 AI 面试演练 · 简历反向挖题 · 多轮追问 · 场景切换 UX。

**Live**: https://mockinterview-agent.vercel.app

## What it does
- 上传简历 PDF + 选岗位（PM / 数据 / AI / 其他）+ 可选 JD
- agent 反向挖出 12 道个性化面试题（5 类：项目深挖 / outcomes 追问 / JD 对齐 / 通用题 / 行为题）
- 单题 U-loop 演练：rubric 评分 + 多轮追问 + **场景切换让路**（"这个例子不够典型，要不你说说项目里类似的事？"）
- 单题报告（雷达图 + 改进建议 + 范例答案）/ 整套面试报告（5 题串联 + 短板维度）

## Architecture
- Backend: Python + FastAPI + Anthropic SDK (Claude 4.7 Opus) + SQLModel + SQLite
- Frontend: Next.js 16 + shadcn/ui + Tailwind + Recharts
- Agent: 手写状态机 + 单次 LLM structured output（每轮一次调用：评分 + 找最弱维度 + 生成追问）

## Eval results
见 [`eval/reports/`](eval/reports/) — vs 裸 Claude 盲评胜率、出题相关性、追问命中率三项核心指标。

## Local dev

```bash
# Backend
cd backend
ANTHROPIC_API_KEY=... uv run uvicorn mockinterview.main:app --reload
# Frontend (in another terminal)
cd frontend
pnpm dev
```

打开 http://localhost:3000 。

## Project journey
- 立项: [`PROJECT.md`](PROJECT.md)
- 设计: [`docs/superpowers/specs/2026-04-27-mock-interview-agent-v1-design.md`](docs/superpowers/specs/2026-04-27-mock-interview-agent-v1-design.md)
- 实施计划: [`plans/2026-04-27-mock-interview-agent-v1.md`](plans/2026-04-27-mock-interview-agent-v1.md)
```

- [ ] **Step 2: 简历金句**

`docs/resume-bullets.md`:

```markdown
# Resume Bullets — MockInterview Agent

(Fill `<X>%` after eval. Below are sentence templates that fit a PM/data resume.)

- Built and deployed an AI mock-interview agent that reverse-mines questions from a candidate's resume and conducts multi-turn drilling with rubric-based scoring; achieved **<X>% blind-eval win rate vs. naive Claude** on PM-track scenarios.
- Designed a 5-rubric system (STAR / 量化严谨度 / JD 对齐 / 结构化思考 / 自洽真诚) replacing one-size-fits-all STAR; agent picks each round's weakest dimension via a single structured-output call (eval drilling-hit rate **<X>%**).
- Shipped a "scenario switch" UX inspired by real interviewer behavior: when a candidate's example can't support the question, the agent proactively offers alternative scenarios (实习 → 项目 → 校园 → 生活) while preserving the underlying competency being tested.
- 4-week solo build: spec → 4-phase plan → backend (FastAPI + Anthropic SDK + SQLModel) + frontend (Next.js 16 + shadcn) + automated eval pipeline + Vercel/Railway deploy.
- (Living metric — to fill after own job-hunt season): in **<N>** real interviews, **<X>%** of asked questions had been pre-drilled in the agent.
```

- [ ] **Step 3: 小红书 4 条 weekly 模板**

`docs/xiaohongshu/week1.md`:

```markdown
# 小红书 — Week 1

标题：我用 4 周做一个 AI 面试 Agent #1：智能解析简历

正文：
我做了一个为 PM/数据/AI 求职者打造的 AI 面试拷打 Agent。
第 1 周完成简历智能解析——上传 PDF，agent 自动提取 4 类字段（基本信息 / 项目 / 工作经历 / 技能），不抓证书 / 论文 / 兴趣这些"反向挖题用不上"的字段。

下周做"反向挖题引擎"——根据简历项目反推面试官最可能挖的角度。

#AI求职 #产品经理 #秋招准备 #ProductHunt

附图：解析后的结构化字段截图（脱敏）
```

(Do similar for week2/week3/week4 referencing spec §9 narrative.)

- [ ] **Step 4: Final commit**

```bash
git add README.md docs/resume-bullets.md docs/xiaohongshu/
git commit -m "docs: README + resume bullets + 小红书素材"
git tag -a v1.0 -m "v1 shipped"
```

---

### Phase 4 Wrap-up

- [ ] **Final smoke test** on live URL — repeat the W3 walkthrough
- [ ] **Sanity check eval report numbers** match what you'd quote in resume bullets
- [ ] **First 小红书 post** scheduled (W1 content was already published earlier; here you publish W4)

---

## Risk Mitigation Summary

Sequenced from highest probability of biting:

| Risk | Trigger | Mitigation |
|---|---|---|
| Week 2 U-loop overruns | 6 exits + scenario switch prompts harder than expected | Drop小红书素材polish in Week 4; ship core functionality only |
| Frontend learning curve too steep | Next.js 16 unfamiliar | Use Claude Code/v0 to scaffold; if Week 3 Wed not on chat UI, drop mock mode (Task 3.6/3.7) and ship single-question only |
| Deploy failures (CORS / volume / DNS) | Week 4 Thu | Fall back to local + recorded video for demo; defer deploy to Week 5 buffer |
| Eval shows quality regression | Late Week 4 | Prioritize tuning question_gen prompt (highest leverage); accept partial weakness on T4/T5 |
| Claude API cost spike | Frequent eval re-runs | Verify prompt caching is actually hitting (check usage dashboard); cap eval to 3 pairs during tuning |
| PDF parsing edge cases | Real resumes with images / weird fonts | If pdfplumber fails, fall back to "paste text" textarea on upload page (3-line UI tweak) |

---

## Self-Review Notes

- ✓ **Spec coverage:** all 13 spec sections map to phases 1-4. §11 non-goals are honored (no exports, no auth, no voice).
- ✓ **Type consistency:** `QuestionStatus` / `ExitType` enums match between models.py, schemas, and frontend types.ts. `DrillState` / `DrillResponse` carry consistent fields.
- ✓ **Placeholder scan:** `<X>%` in resume bullets is intentionally awaiting eval results; no other TODOs remain.
- ⚠ **Test density:** frontend has no automated tests in v1 (intentional, called out in Test Strategy). Manual e2e is the gate.
- ⚠ **Curate-the-seed-bank task** (Task 1.8) is a content task that can grow — capped to ~half-day Wednesday. If running long, ship with 15 questions per role and curate the rest in Week 4 Friday buffer.

