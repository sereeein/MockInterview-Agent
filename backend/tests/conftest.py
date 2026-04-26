import pytest
from collections.abc import Iterator
from fastapi.testclient import TestClient

from mockinterview.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c
