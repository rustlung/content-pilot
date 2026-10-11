from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from content_pilot.ai.service import AIProvider
from content_pilot.api.dependencies import get_ai_provider
from content_pilot.api.schemas import ContentItemRead, ContentPlanGenerate
from content_pilot.db.session import get_session
from content_pilot.services.content_plans import generate_content_plan, list_content_items

router = APIRouter(tags=["content-plans"])


@router.post("/projects/{project_id}/content-plan/generate", response_model=list[ContentItemRead])
def generate(project_id: UUID, payload: ContentPlanGenerate, session: Session = Depends(get_session), provider: AIProvider = Depends(get_ai_provider)):
    return generate_content_plan(session, provider, project_id, **payload.model_dump())


@router.get("/projects/{project_id}/content-items", response_model=list[ContentItemRead])
def list_items(project_id: UUID, session: Session = Depends(get_session)):
    return list_content_items(session, project_id)
