"""M2 services with a deterministic provider and SQLite; no network calls."""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from content_pilot.ai.client import AIProviderError
from content_pilot.ai.schemas import ContentPlanAI, ContentPlanItemAI, ContentGoal, ContentType, ImagePromptAI, PostGenerationAI
from content_pilot.db.base import Base
import content_pilot.models  # noqa: F401
from content_pilot.models.content_item import ContentItem
from content_pilot.models.enums import Platform, PostStatus
from content_pilot.models.media_asset import MediaAsset
from content_pilot.models.post import Post
from content_pilot.models.project import Project
from content_pilot.services.content_plans import generate_content_plan
from content_pilot.services.errors import ConflictError, ValidationDomainError
from content_pilot.services.media import generate_image
from content_pilot.services.posts import generate_post


class FakeAI:
    def __init__(self, plan: ContentPlanAI | None = None, fail: bool = False) -> None:
        self.plan = plan or ContentPlanAI(items=[ContentPlanItemAI(title="Практика Python backend", topic="Проектирование API", goal=ContentGoal.EXPERTISE, content_type=ContentType.EDUCATIONAL, suggested_date=date(2026, 10, 12))])
        self.fail = fail

    def generate_content_plan(self, prompt: str) -> ContentPlanAI:
        if self.fail:
            raise AIProviderError("provider unavailable")
        return self.plan

    def generate_post(self, prompt: str) -> PostGenerationAI:
        if self.fail:
            raise AIProviderError("provider unavailable")
        return PostGenerationAI(text="Практический пост о Python backend-разработке.", hashtags=["#python"], image_needed=True)

    def generate_image_prompt(self, prompt: str) -> ImagePromptAI:
        if self.fail:
            raise AIProviderError("provider unavailable")
        return ImagePromptAI(prompt="Professional backend illustration, no text", alt_text="Абстрактная иллюстрация backend-разработки")

    def generate_image(self, prompt: str) -> bytes:
        if self.fail:
            raise AIProviderError("provider unavailable")
        return b"fake-png-data"


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with factory() as session:
        yield session


@pytest.fixture
def project(session: Session) -> Project:
    project = Project(name="Тестовый проект")
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def test_valid_plan_persists_items(session: Session, project: Project) -> None:
    items = generate_content_plan(session, FakeAI(), project.id, date(2026, 10, 10), date(2026, 10, 20), 1, [Platform.LINKEDIN])
    assert len(items) == 1
    assert session.scalar(select(ContentItem).where(ContentItem.project_id == project.id)).title == "Практика Python backend"


def test_invalid_plan_date_and_provider_failure_persist_nothing(session: Session, project: Project) -> None:
    outside = ContentPlanAI(items=[ContentPlanItemAI(title="Outside", topic="Topic", goal=ContentGoal.EDUCATION, content_type=ContentType.STORY, suggested_date=date(2026, 11, 1))])
    with pytest.raises(ValidationDomainError):
        generate_content_plan(session, FakeAI(outside), project.id, date(2026, 10, 10), date(2026, 10, 20), 1, [Platform.VK])
    with pytest.raises(AIProviderError):
        generate_content_plan(session, FakeAI(fail=True), project.id, date(2026, 10, 10), date(2026, 10, 20), 1, [Platform.VK])
    assert session.scalars(select(ContentItem)).all() == []


def test_post_generation_updates_only_draft(session: Session, project: Project) -> None:
    item = ContentItem(project_id=project.id, title="Title", content_type="educational")
    session.add(item)
    session.commit()
    first = generate_post(session, FakeAI(), item.id, Platform.LINKEDIN)
    second = generate_post(session, FakeAI(), item.id, Platform.LINKEDIN)
    assert first.id == second.id
    assert len(session.scalars(select(Post)).all()) == 1
    second.status = PostStatus.APPROVED
    session.commit()
    with pytest.raises(ConflictError):
        generate_post(session, FakeAI(), item.id, Platform.LINKEDIN)


def test_image_writes_file_and_asset(session: Session, project: Project, tmp_path) -> None:
    item = ContentItem(project_id=project.id, title="Title", content_type="educational")
    post = Post(content_item=item, platform=Platform.TELEGRAM, text="Post text")
    session.add(post)
    session.commit()
    asset = generate_image(session, FakeAI(), post.id, tmp_path)
    assert asset.file_path
    assert (tmp_path / asset.file_path).read_bytes() == b"fake-png-data"
    assert session.scalar(select(MediaAsset).where(MediaAsset.id == asset.id)) is not None


def test_image_provider_failure_leaves_no_asset(session: Session, project: Project, tmp_path) -> None:
    item = ContentItem(project_id=project.id, title="Title", content_type="educational")
    post = Post(content_item=item, platform=Platform.VK, text="Post text")
    session.add(post)
    session.commit()
    with pytest.raises(AIProviderError):
        generate_image(session, FakeAI(fail=True), post.id, tmp_path)
    assert session.scalars(select(MediaAsset)).all() == []
