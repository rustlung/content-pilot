"""Dependencies intentionally constructed lazily so health checks need no AI key."""
from content_pilot.ai.client import AIClient
from content_pilot.config import Settings


def get_ai_provider() -> AIClient:
    return AIClient(Settings())
