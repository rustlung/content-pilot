"""Server-rendered M3 interface. Business actions delegate to application services."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from content_pilot.ai.service import AIProvider
from content_pilot.api.dependencies import get_ai_provider
from content_pilot.config import Settings
from content_pilot.db.session import get_session
from content_pilot.models.enums import ContentItemStatus, Platform, PostStatus
from content_pilot.services.content_plans import generate_content_plan, list_content_items
from content_pilot.services.dashboard import dashboard_data
from content_pilot.services.errors import ValidationDomainError
from content_pilot.services.media import generate_image
from content_pilot.services.post_workflow import approve_post, cancel_post, schedule_post, unschedule_post
from content_pilot.services.posts import generate_post, get_post, update_draft_post_text
from content_pilot.services.projects import create_project, get_project, list_projects


TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
router = APIRouter()

POST_STATUS_LABELS = {
    PostStatus.DRAFT: "Черновик", PostStatus.APPROVED: "Подтверждён", PostStatus.SCHEDULED: "Запланирован",
    PostStatus.PUBLISHING: "Публикуется", PostStatus.PUBLISHED: "Опубликован", PostStatus.FAILED: "Ошибка",
    PostStatus.CANCELLED: "Отменён",
}
CONTENT_ITEM_STATUS_LABELS = {
    ContentItemStatus.DRAFT: "Черновик", ContentItemStatus.PLANNED: "Запланирован", ContentItemStatus.CANCELLED: "Отменён",
}
PLATFORM_LABELS = {Platform.LINKEDIN: "LinkedIn", Platform.VK: "VK", Platform.TELEGRAM: "Telegram"}


def _local_datetime(value: datetime | None, timezone_name: str) -> str:
    if value is None:
        return "—"
    return value.astimezone(ZoneInfo(timezone_name)).strftime("%d.%m.%Y %H:%M")


TEMPLATES.env.filters["local_datetime"] = _local_datetime


def template_context(request: Request, **context: object) -> dict[str, object]:
    settings: Settings = request.app.state.settings
    return {
        "app_name": settings.app_name, "app_env": settings.app_env, "app_timezone": settings.app_timezone,
        "message": request.query_params.get("message"), "message_type": request.query_params.get("message_type", "success"),
        "post_status_labels": POST_STATUS_LABELS, "content_item_status_labels": CONTENT_ITEM_STATUS_LABELS,
        "platform_labels": PLATFORM_LABELS, **context,
    }


def render(request: Request, name: str, **context: object) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(request=request, name=name, context=template_context(request, **context))


def redirect(url: str, message: str, message_type: str = "success") -> RedirectResponse:
    separator = "&" if "?" in url else "?"
    return RedirectResponse(f"{url}{separator}{urlencode({'message': message, 'message_type': message_type})}", status_code=303)


def parse_platforms(values: list[str]) -> list[Platform]:
    try:
        return [Platform(value) for value in values]
    except ValueError as error:
        raise ValidationDomainError("Выберите поддерживаемую платформу") from error


def parse_local_datetime(value: str, settings: Settings) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValidationDomainError("Введите корректные дату и время") from error
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=settings.timezone)


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, session: Session = Depends(get_session)) -> HTMLResponse:
    return render(request, "dashboard.html", **dashboard_data(session))


@router.get("/projects", response_class=HTMLResponse)
def projects(request: Request, session: Session = Depends(get_session)) -> HTMLResponse:
    return render(request, "projects.html", projects=list_projects(session))


@router.get("/projects/new", response_class=HTMLResponse)
def project_create_form(request: Request) -> HTMLResponse:
    return render(request, "project_create.html")


@router.post("/projects")
def project_create(
    name: str = Form(...), description: str | None = Form(None), audience: str | None = Form(None),
    tone_of_voice: str | None = Form(None), language: str = Form("ru"), session: Session = Depends(get_session),
) -> RedirectResponse:
    project = create_project(session, name=name.strip(), description=description or None, audience=audience or None,
                             tone_of_voice=tone_of_voice or None, language=language.strip() or "ru")
    return redirect(f"/projects/{project.id}", "Проект создан")


@router.get("/projects/{project_id}", response_class=HTMLResponse)
def project_detail(request: Request, project_id: UUID, session: Session = Depends(get_session)) -> HTMLResponse:
    project = get_project(session, project_id)
    return render(request, "project_detail.html", project=project, content_items=list_content_items(session, project_id))


@router.get("/projects/{project_id}/plan", response_class=HTMLResponse)
def content_plan(request: Request, project_id: UUID, session: Session = Depends(get_session)) -> HTMLResponse:
    project = get_project(session, project_id)
    return render(request, "content_plan.html", project=project, content_items=list_content_items(session, project_id), platforms=list(Platform), today=date.today().isoformat())


@router.post("/projects/{project_id}/plan/generate")
def content_plan_generate(
    project_id: UUID, start_date: date = Form(...), end_date: date = Form(...), posts_count: int = Form(...),
    platforms: list[str] = Form(...), session: Session = Depends(get_session), provider: AIProvider = Depends(get_ai_provider),
) -> RedirectResponse:
    items = generate_content_plan(session, provider, project_id, start_date, end_date, posts_count, parse_platforms(platforms))
    return redirect(f"/projects/{project_id}/plan", f"Создано элементов плана: {len(items)}")


@router.post("/content-items/{content_item_id}/posts/generate")
def post_generate(
    content_item_id: UUID, platform: Platform = Form(...), instructions: str | None = Form(None),
    session: Session = Depends(get_session), provider: AIProvider = Depends(get_ai_provider),
) -> RedirectResponse:
    post = generate_post(session, provider, content_item_id, platform, instructions or None)
    return redirect(f"/posts/{post.id}", "Черновик поста сгенерирован")


@router.get("/posts/{post_id}", response_class=HTMLResponse)
def post_detail(request: Request, post_id: UUID, session: Session = Depends(get_session)) -> HTMLResponse:
    post = get_post(session, post_id)
    media = [{"asset": asset, "url": str(request.url_for("media", path=asset.file_path)) if asset.file_path else None} for asset in post.media_assets]
    return render(request, "post_detail.html", post=post, media=media)


@router.post("/posts/{post_id}/edit")
def post_edit(post_id: UUID, text: str = Form(...), session: Session = Depends(get_session)) -> RedirectResponse:
    update_draft_post_text(session, post_id, text)
    return redirect(f"/posts/{post_id}", "Текст черновика сохранён")


@router.post("/posts/{post_id}/regenerate")
def post_regenerate(
    post_id: UUID, instructions: str | None = Form(None), session: Session = Depends(get_session),
    provider: AIProvider = Depends(get_ai_provider),
) -> RedirectResponse:
    post = get_post(session, post_id)
    regenerated = generate_post(session, provider, post.content_item_id, post.platform, instructions or None)
    return redirect(f"/posts/{regenerated.id}", "Черновик перегенерирован")


@router.post("/posts/{post_id}/image/generate")
def image_generate(
    request: Request, post_id: UUID, session: Session = Depends(get_session), provider: AIProvider = Depends(get_ai_provider),
) -> RedirectResponse:
    generate_image(session, provider, post_id, request.app.state.settings.media_root)
    return redirect(f"/posts/{post_id}", "Изображение сгенерировано")


@router.post("/posts/{post_id}/approve")
def post_approve(post_id: UUID, session: Session = Depends(get_session)) -> RedirectResponse:
    approve_post(session, post_id)
    return redirect(f"/posts/{post_id}", "Пост подтверждён")


@router.post("/posts/{post_id}/schedule")
def post_schedule(
    request: Request, post_id: UUID, scheduled_at: str = Form(...), session: Session = Depends(get_session),
) -> RedirectResponse:
    schedule_post(session, post_id, parse_local_datetime(scheduled_at, request.app.state.settings))
    return redirect(f"/posts/{post_id}", "Пост запланирован")


@router.post("/posts/{post_id}/unschedule")
def post_unschedule(post_id: UUID, session: Session = Depends(get_session)) -> RedirectResponse:
    unschedule_post(session, post_id)
    return redirect(f"/posts/{post_id}", "Расписание снято: пост снова подтверждён")


@router.post("/posts/{post_id}/cancel")
def post_cancel(post_id: UUID, session: Session = Depends(get_session)) -> RedirectResponse:
    cancel_post(session, post_id)
    return redirect(f"/posts/{post_id}", "Пост отменён")
