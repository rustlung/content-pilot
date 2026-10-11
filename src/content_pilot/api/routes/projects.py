from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from content_pilot.api.schemas import ProjectCreate, ProjectRead
from content_pilot.db.session import get_session
from content_pilot.services.projects import create_project, get_project, list_projects

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectRead, status_code=201)
def create(payload: ProjectCreate, session: Session = Depends(get_session)):
    return create_project(session, **payload.model_dump())


@router.get("", response_model=list[ProjectRead])
def list_all(session: Session = Depends(get_session)):
    return list_projects(session)


@router.get("/{project_id}", response_model=ProjectRead)
def get_one(project_id: UUID, session: Session = Depends(get_session)):
    return get_project(session, project_id)
