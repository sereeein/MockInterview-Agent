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
