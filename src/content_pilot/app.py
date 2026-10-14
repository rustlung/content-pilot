"""FastAPI application factory for the ContentPilot foundation."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from content_pilot.api.router import router as api_router
from content_pilot.config import Settings
from content_pilot.web.router import TEMPLATES, router as web_router, template_context
from content_pilot.ai.client import AIConfigurationError, AIError, AIProviderError, AIResponseValidationError
from content_pilot.services.errors import ConflictError, NotFoundError, ValidationDomainError

STATIC_ROOT = Path(__file__).parent / "web" / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the web application without connecting to or mutating the database."""
    resolved_settings = settings or Settings()
    app = FastAPI(title=resolved_settings.app_name, debug=resolved_settings.app_debug)
    app.state.settings = resolved_settings
    app.mount("/media", StaticFiles(directory=resolved_settings.media_root, check_dir=False), name="media")
    app.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")

    def error_response(request: Request, status_code: int, title: str, detail: str) -> Response:
        if request.url.path.startswith("/api"):
            return JSONResponse(status_code=status_code, content={"detail": detail})
        return TEMPLATES.TemplateResponse(
            request=request,
            name="error.html",
            context=template_context(request, status_code=status_code, title=title, detail=detail),
            status_code=status_code,
        )

    @app.exception_handler(NotFoundError)
    async def not_found(request: Request, error: NotFoundError) -> Response:
        return error_response(request, 404, "Ничего не найдено", str(error))

    @app.exception_handler(ConflictError)
    async def conflict(request: Request, error: ConflictError) -> Response:
        return error_response(request, 409, "Действие недоступно", str(error))

    @app.exception_handler(ValidationDomainError)
    async def invalid(request: Request, error: ValidationDomainError) -> Response:
        return error_response(request, 422, "Проверьте введённые данные", str(error))

    @app.exception_handler(AIConfigurationError)
    async def ai_config(request: Request, error: AIConfigurationError) -> Response:
        return error_response(request, 503, "AI-генерация не настроена", str(error))

    async def ai_failure(request: Request, error: AIError) -> Response:
        return error_response(request, 502, "AI-сервис недоступен", str(error))

    app.add_exception_handler(AIProviderError, ai_failure)
    app.add_exception_handler(AIResponseValidationError, ai_failure)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(web_router)
    app.include_router(api_router)
    return app
