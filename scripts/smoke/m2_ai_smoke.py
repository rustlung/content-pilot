"""Manual real-ProxyAPI M2 smoke; never run from pytest or application startup."""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import sessionmaker

from content_pilot.ai.client import AIClient
from content_pilot.config import Settings
from content_pilot.db.engine import create_db_engine
from content_pilot.models.enums import Platform
from content_pilot.services.content_plans import generate_content_plan
from content_pilot.services.media import generate_image
from content_pilot.services.posts import generate_post
from content_pilot.services.projects import create_project


def main() -> None:
    settings = Settings()
    provider = AIClient(settings)
    factory = sessionmaker(create_db_engine(settings), expire_on_commit=False)
    with factory() as session:
        project = create_project(
            session,
            name="Личный бренд Python-разработчика",
            description="Практика Python backend-разработки, AI-автоматизация, pet-проекты и разбор инженерных решений",
            audience="Python-разработчики, технические специалисты, рекрутеры и нанимающие менеджеры",
            tone_of_voice="профессиональный, практичный, понятный, без канцелярита",
            language="ru",
        )
        start_date = date.today()
        items = generate_content_plan(session, provider, project.id, start_date, start_date + timedelta(days=7), 3, [Platform.LINKEDIN])
        post = generate_post(session, provider, items[0].id, Platform.LINKEDIN)
        asset = generate_image(session, provider, post.id, settings.media_root)
        project_id = str(project.id)
        item_ids = ",".join(str(item.id) for item in items)
        post_id = str(post.id)
        asset_id = str(asset.id)
        media_path = asset.file_path
    print(f"PROJECT_ID={project_id}")
    print(f"CONTENT_ITEM_IDS={item_ids}")
    print(f"POST_ID={post_id}")
    print(f"MEDIA_ASSET_ID={asset_id}")
    print(f"MEDIA_PATH={media_path}")
    print("M2 AI SMOKE: PASS")


if __name__ == "__main__":
    main()
