"""M2 JSON API composition."""
from fastapi import APIRouter

from content_pilot.api.routes import content_plans, media, posts, projects


router = APIRouter(prefix="/api")


@router.get("/health")
def api_health() -> dict[str, str]:
    return {"service": "content-pilot", "status": "ok"}


router.include_router(projects.router)
router.include_router(content_plans.router)
router.include_router(posts.router)
router.include_router(media.router)
