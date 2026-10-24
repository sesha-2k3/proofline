from fastapi import APIRouter

from app.rules import accessors
from app.schemas.api import HealthResponse
from app.settings import get_settings

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        ok=True,
        demo_mode=settings.demo_mode,
        llm_provider=settings.llm_provider or "none",
        rules_version=accessors.rules_version(),
    )
