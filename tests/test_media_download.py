"""Safe original-media download coverage without real AI or social calls."""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from content_pilot.app import create_app
from content_pilot.config import Settings
from content_pilot.db.base import Base
from content_pilot.db.session import get_session
from content_pilot.models.content_item import ContentItem
from content_pilot.models.enums import MediaSource, MediaType, Platform
from content_pilot.models.media_asset import MediaAsset
from content_pilot.models.post import Post
from content_pilot.models.project import Project
import content_pilot.models  # noqa: F401


def build_client(tmp_path: Path) -> tuple[TestClient, Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(engine)()
    app = create_app(Settings(postgres_password="test-password", media_root=tmp_path))
    app.dependency_overrides[get_session] = lambda: session
    return TestClient(app), session


def create_image_asset(session: Session, media_root: Path, file_path: str = "images/original.png") -> MediaAsset:
    project = Project(name="Media project")
    item = ContentItem(project=project, title="Image post", content_type="educational")
    post = Post(content_item=item, platform=Platform.VK, text="Text")
    asset = MediaAsset(
        post=post,
        media_type=MediaType.IMAGE,
        source=MediaSource.AI,
        file_path=file_path,
    )
    session.add(asset)
    session.commit()
    if not Path(file_path).is_absolute() and ".." not in Path(file_path).parts:
        destination = media_root / file_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"original-image-bytes")
    return asset


def test_download_returns_original_asset_and_post_detail_button(tmp_path: Path) -> None:
    client, session = build_client(tmp_path)
    asset = create_image_asset(session, tmp_path)

    response = client.get(f"/downloads/media/{asset.id}")
    assert response.status_code == 200
    assert response.content == b"original-image-bytes"
    assert f"contentpilot-vk-{asset.post_id}.png" in response.headers["content-disposition"]

    detail = client.get(f"/posts/{asset.post_id}")
    assert detail.status_code == 200
    assert "Скачать изображение" in detail.text
    assert f"/downloads/media/{asset.id}" in detail.text
    client.close()
    session.close()


def test_download_returns_404_for_missing_media(tmp_path: Path) -> None:
    client, session = build_client(tmp_path)
    response = client.get(f"/downloads/media/{uuid4()}")
    assert response.status_code == 404
    client.close()
    session.close()


def test_download_rejects_media_path_outside_media_root(tmp_path: Path) -> None:
    client, session = build_client(tmp_path)
    asset = create_image_asset(session, tmp_path, "../outside.png")

    response = client.get(f"/downloads/media/{asset.id}")
    assert response.status_code == 404
    assert "Файл изображения недоступен" in response.text
    client.close()
    session.close()
