from fastapi import APIRouter, Depends

from mockinterview.agent.providers import active
from mockinterview.routes._deps import use_provider
from mockinterview.schemas.provider import ProviderTestResult

router = APIRouter(prefix="/provider", tags=["provider"])


@router.post("/test", response_model=ProviderTestResult)
def test_provider(_: None = Depends(use_provider)) -> ProviderTestResult:
    """Verify the active provider+model+key by sending a minimal JSON-mode
    ping (~30 tokens). Never raises — all failures are mapped to a structured
    ProviderTestResult with a category the frontend can render specifically.
    """
    p = active()
    return p.test_connection()
