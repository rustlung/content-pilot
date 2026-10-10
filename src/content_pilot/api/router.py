"""Foundation API endpoints only."""
from fastapi import APIRouter


router = APIRouter(prefix="/api")


@router.get("/health")
def api_health() -> dict[str, str]:
    return {"service": "content-pilot", "status": "ok"}
