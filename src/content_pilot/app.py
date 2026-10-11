"""FastAPI application factory for the ContentPilot foundation."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from content_pilot.api.router import router as api_router
from content_pilot.config import Settings
from content_pilot.web.router import router as web_router
from content_pilot.ai.client import AIConfigurationError, AIError, AIProviderError, AIResponseValidationError
from content_pilot.services.errors import ConflictError, NotFoundError, ValidationDomainError


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the web application without connecting to or mutating the database."""
    resolved_settings = settings or Settings()
    app = FastAPI(title=resolved_settings.app_name, debug=resolved_settings.app_debug)
    app.state.settings = resolved_settings
    app.mount("/media", StaticFiles(directory=resolved_settings.media_root, check_dir=False), name="media")

    @app.exception_handler(NotFoundError)
    async def not_found(_: Request, error: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(error)})

    @app.exception_handler(ConflictError)
    async def conflict(_: Request, error: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(error)})

    @app.exception_handler(ValidationDomainError)
    async def invalid(_: Request, error: ValidationDomainError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(error)})

    @app.exception_handler(AIConfigurationError)
    async def ai_config(_: Request, error: AIConfigurationError) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(error)})

    async def ai_failure(_: Request, error: AIError) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(error)})

    app.add_exception_handler(AIProviderError, ai_failure)
    app.add_exception_handler(AIResponseValidationError, ai_failure)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(web_router)
    app.include_router(api_router)
    return app
