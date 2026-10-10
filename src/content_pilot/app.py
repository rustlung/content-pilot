"""FastAPI application factory for the ContentPilot foundation."""
from __future__ import annotations

from fastapi import FastAPI

from content_pilot.api.router import router as api_router
from content_pilot.config import Settings
from content_pilot.web.router import router as web_router


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the web application without connecting to or mutating the database."""
    resolved_settings = settings or Settings()
    app = FastAPI(title=resolved_settings.app_name, debug=resolved_settings.app_debug)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(web_router)
    app.include_router(api_router)
    return app
