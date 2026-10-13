"""M3 server-rendered flow with FakeAI, SQLite and no real external calls."""
from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient

from content_pilot.api.dependencies import get_ai_provider
from tests.test_m2_services import FakeAI


def test_web_workflow_and_manual_linkedin_mode(client: TestClient) -> None:
    client.app.dependency_overrides[get_ai_provider] = lambda: FakeAI()
    assert client.get("/").status_code == 200
    assert client.get("/projects").status_code == 200
    created = client.post(
        "/projects",
        data={"name": "Личный бренд Python-разработчика", "language": "ru"},
        follow_redirects=False,
    )
    assert created.status_code == 303
    project_url = created.headers["location"].split("?")[0]
    assert client.get(project_url).status_code == 200
    project_id = project_url.rsplit("/", 1)[-1]
    plan = client.post(
        f"/projects/{project_id}/plan/generate",
        data={"start_date": "2026-10-10", "end_date": "2026-10-12", "posts_count": "1", "platforms": "linkedin"},
        follow_redirects=False,
    )
    assert plan.status_code == 303
    item_id = client.get(f"/api/projects/{project_id}/content-items").json()[0]["id"]
    generated = client.post(
        f"/content-items/{item_id}/posts/generate", data={"platform": "linkedin"}, follow_redirects=False
    )
    post_url = generated.headers["location"].split("?")[0]
    post_id = post_url.rsplit("/", 1)[-1]
    detail = client.get(post_url)
    assert detail.status_code == 200
    assert "LinkedIn:" in detail.text
    assert "Попыток публикации пока нет" in detail.text
    edited = client.post(f"/posts/{post_id}/edit", data={"text": "Отредактированный текст."}, follow_redirects=False)
    assert edited.status_code == 303
    image = client.post(f"/posts/{post_id}/image/generate", follow_redirects=False)
    assert image.status_code == 303
    assert "/media/" in client.get(post_url).text
    assert client.post(f"/posts/{post_id}/approve", follow_redirects=False).status_code == 303
    future = (datetime.now() + timedelta(days=1)).replace(second=0, microsecond=0).isoformat(timespec="minutes")
    assert client.post(f"/posts/{post_id}/schedule", data={"scheduled_at": future}, follow_redirects=False).status_code == 409
    generated_vk = client.post(
        f"/content-items/{item_id}/posts/generate", data={"platform": "vk"}, follow_redirects=False
    )
    vk_post_url = generated_vk.headers["location"].split("?")[0]
    vk_post_id = vk_post_url.rsplit("/", 1)[-1]
    assert "Изображения публикуйте вручную" in client.get(vk_post_url).text
    assert client.post(f"/posts/{vk_post_id}/approve", follow_redirects=False).status_code == 303
    assert client.post(f"/posts/{vk_post_id}/schedule", data={"scheduled_at": future}, follow_redirects=False).status_code == 303
    dashboard = client.get("/")
    assert "Контент-план: 1" in dashboard.text
    assert "Запланировано: 1" in dashboard.text
    assert "Ближайшая публикация:" in dashboard.text
    assert 'class="button button-secondary button-small" href="/projects"' in dashboard.text
    projects_page = client.get("/projects")
    assert f'href="/projects/{project_id}"' in projects_page.text
    assert "project-name-link" in projects_page.text
    assert "action-column" in projects_page.text
    assert client.post(f"/posts/{vk_post_id}/unschedule", follow_redirects=False).status_code == 303
    assert client.post(f"/posts/{vk_post_id}/cancel", follow_redirects=False).status_code == 303
