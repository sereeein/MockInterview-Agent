from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from mockinterview.agent.providers import set_active
from mockinterview.main import app
from mockinterview.routes._deps import use_provider


async def _test_provider_override() -> None:
    """Async (mirrors prod use_provider) so ContextVar.set() runs on the main task and
    propagates to sync route handlers via anyio. Sets a MagicMock as active provider
    so any UNMOCKED agent code raises a clear error (since MagicMock returns Mock
    objects, not parseable JSON). Tests that actually exercise agent paths must mock
    at the agent function level."""
    set_active(MagicMock())


@pytest.fixture
def client() -> Iterator[TestClient]:
    app.dependency_overrides[use_provider] = _test_provider_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
