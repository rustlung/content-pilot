# ContentPilot 0.1.0 — Release checklist

## Demo scenario

Create a project named **«Личный бренд Python-разработчика»**.

- Description: Python backend, AI-автоматизация, pet-проекты и инженерные решения
- Audience: Python-разработчики, технические специалисты, рекрутеры и нанимающие менеджеры
- Tone: профессиональный, практичный, понятный, без канцелярита
- Language: `ru`

## Screenshots

- [ ] Dashboard with analytics cards and platform counts
- [ ] Projects list
- [ ] Content plan
- [ ] LinkedIn post editor with generated image and manual-mode note
- [ ] Scheduled VK or Telegram post
- [ ] Published post with publication-attempt history
- [ ] VK media capability note and manual image fallback

## Screencast

- [ ] Create a project
- [ ] Generate a content plan
- [ ] Generate and edit a platform post
- [ ] Generate an image
- [ ] Approve and schedule the post
- [ ] Show the publication result and attempt history

## Zerocoder delivery

- [ ] Public GitHub repository
- [ ] README
- [ ] Technical specification DOCX (prepare from `docs/spec-outline.md` after M7)
- [ ] Screenshots
- [ ] Screencast
- [ ] Working project demonstration

## Optional development cleanup

Do not delete data automatically. For a disposable local Compose database only,
stop the stack and remove its named PostgreSQL volume deliberately:

```powershell
docker compose down
docker volume rm content-pilot_content-pilot-postgres-data
```

Confirm the volume name with `docker volume ls` first. Never use this against a
database containing material you need to retain.
