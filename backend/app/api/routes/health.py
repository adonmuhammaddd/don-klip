from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.api.deps import SessionDep
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(session: SessionDep) -> HealthResponse:
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:  # surfaced as 503, jangan bocorin detail internal
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return HealthResponse(status="ok", database="ok")
