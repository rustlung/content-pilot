"""Minimal project persistence needed by M2 manual API checks."""
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from content_pilot.models.content_item import ContentItem
from content_pilot.models.project import Project
from content_pilot.services.errors import NotFoundError


def create_project(session: Session, **values: str | None) -> Project:
    project = Project(**values)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def get_project(session: Session, project_id: object) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise NotFoundError("Project not found")
    return project


def list_projects(session: Session) -> list[Project]:
    return list(
        session.scalars(
            select(Project)
            .options(selectinload(Project.content_items).selectinload(ContentItem.posts))
            .order_by(Project.created_at.desc())
        )
    )
