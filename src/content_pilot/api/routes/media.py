from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from uuid import UUID

from content_pilot.ai.service import AIProvider
from content_pilot.api.dependencies import get_ai_provider
from content_pilot.api.schemas import MediaAssetRead
from content_pilot.db.session import get_session
from content_pilot.services.media import generate_image, list_media

router = APIRouter(tags=["media"])


def to_media_read(asset, request: Request) -> MediaAssetRead:
    payload = MediaAssetRead.model_validate(asset)
    if asset.file_path:
        payload.media_url = str(request.url_for("media", path=asset.file_path))
    return payload


@router.post("/posts/{post_id}/image/generate", response_model=MediaAssetRead)
def generate(post_id: UUID, request: Request, session: Session = Depends(get_session), provider: AIProvider = Depends(get_ai_provider)):
    asset = generate_image(session, provider, post_id, request.app.state.settings.media_root)
    return to_media_read(asset, request)


@router.get("/posts/{post_id}/media", response_model=list[MediaAssetRead])
def list_for_post(post_id: UUID, request: Request, session: Session = Depends(get_session)):
    return [to_media_read(asset, request) for asset in list_media(session, post_id)]
