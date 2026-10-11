from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from content_pilot.ai.service import AIProvider
from content_pilot.api.dependencies import get_ai_provider
from content_pilot.api.schemas import PostGenerate, PostRead
from content_pilot.db.session import get_session
from content_pilot.services.posts import generate_post, list_posts

router = APIRouter(tags=["posts"])


@router.post("/content-items/{content_item_id}/posts/generate", response_model=PostRead)
def generate(content_item_id: UUID, payload: PostGenerate, session: Session = Depends(get_session), provider: AIProvider = Depends(get_ai_provider)):
    return generate_post(session, provider, content_item_id, **payload.model_dump())


@router.get("/content-items/{content_item_id}/posts", response_model=list[PostRead])
def list_for_item(content_item_id: UUID, session: Session = Depends(get_session)):
    return list_posts(session, content_item_id)
