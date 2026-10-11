"""Language and platform-style rules remain explicit and independently testable."""
from datetime import date
from types import SimpleNamespace

from content_pilot.ai.prompts import (
    PLATFORM_INSTRUCTIONS,
    SYSTEM_INSTRUCTION,
    content_plan_prompt,
    image_prompt,
    post_prompt,
)
from content_pilot.models.enums import Platform


def russian_project() -> SimpleNamespace:
    return SimpleNamespace(
        name="Личный бренд Python-разработчика",
        description="Практика Python backend-разработки",
        audience="Технические специалисты",
        tone_of_voice="Практичный",
        language="ru",
    )


def test_russian_project_prompt_requires_russian_output() -> None:
    prompt = content_plan_prompt(russian_project(), date(2026, 10, 10), date(2026, 10, 20), 3, [Platform.VK])
    assert "строго русский" in prompt
    assert "Не используй английские заголовки" in prompt
    assert "без канцелярита" in prompt
    assert "становится ключевым инструментом" in prompt
    assert "я внедрил" in prompt


def test_linkedin_uses_russian_language_not_english_default() -> None:
    item = SimpleNamespace(title="Разбор FastAPI", topic="API", goal="expertise", content_type="educational")
    prompt = post_prompt(russian_project(), item, Platform.LINKEDIN, None)
    assert "строго русский" in prompt
    assert "Профессиональный, но не корпоративный стиль" in prompt
    assert "English" not in prompt
    assert "2–5 коротких абзацев" in prompt
    assert "не заканчивай пост вопросом" in prompt
    assert "один конкретный инженерный угол" in prompt
    assert "Не пиши обзорную статью" in prompt


def test_platform_profiles_affect_style_but_not_language() -> None:
    assert "язык" not in PLATFORM_INSTRUCTIONS[Platform.LINKEDIN].lower()
    assert "язык" not in PLATFORM_INSTRUCTIONS[Platform.VK].lower()
    assert "язык" not in PLATFORM_INSTRUCTIONS[Platform.TELEGRAM].lower()
    item = SimpleNamespace(title="Разбор FastAPI", topic="API")
    prompt = image_prompt(russian_project(), item, "Текст поста", Platform.TELEGRAM)
    assert "alt_text обязательно пиши на языке проекта" in prompt
    assert "может быть на английском" in prompt


def test_content_plan_requires_specific_developer_topics() -> None:
    prompt = content_plan_prompt(russian_project(), date(2026, 10, 10), date(2026, 10, 20), 3, [Platform.TELEGRAM])
    assert "Не предлагай generic-темы" in prompt
    assert "архитектурное решение" in prompt
    assert "практический вывод" in prompt


def test_prompts_require_factual_grounding_for_technical_claims() -> None:
    item = SimpleNamespace(title="Очереди задач", topic="Фоновая обработка", goal="education", content_type="educational")
    prompt = post_prompt(russian_project(), item, Platform.LINKEDIN, None)
    assert "ограничения технологий" in prompt
    assert "производительности или безопасности" in prompt
    assert "гарантии" in prompt
    assert "не выдумывай её и не маскируй предположение под факт" in prompt
    assert "зависит от конфигурации" in prompt
    assert "переход с Redis на RabbitMQ" in prompt
    assert "Само название технологии" in prompt
    assert "формат вопросов, критериев проверки или вариантов выбора" in prompt
    assert "не утверждай, что Redis выполняет конкретную роль" in prompt
    assert "Не используй собственные или общеизвестные знания" in prompt
    assert "исключи каждое декларативное техническое утверждение" in prompt


def test_system_instruction_requires_factual_grounding() -> None:
    assert "Если не уверен в технической детали — не выдумывай её" in SYSTEM_INSTRUCTION
    assert "Название технологии или тема поста" in SYSTEM_INSTRUCTION
    assert "критериях проверки" in SYSTEM_INSTRUCTION
    assert "общеизвестными знаниями" in SYSTEM_INSTRUCTION


def test_content_plan_also_inherits_factual_grounding_requirement() -> None:
    prompt = content_plan_prompt(russian_project(), date(2026, 10, 10), date(2026, 10, 20), 3, [Platform.VK])
    assert "технические факты только тогда, когда они прямо следуют из предоставленного контекста" in prompt


def test_vk_and_telegram_profiles_have_distinct_non_salesy_styles() -> None:
    assert "продающего тона" in PLATFORM_INSTRUCTIONS[Platform.VK]
    assert "технические детали" in PLATFORM_INSTRUCTIONS[Platform.TELEGRAM]
