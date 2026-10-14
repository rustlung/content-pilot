"""ProxyAPI-backed OpenAI SDK client, instantiated only at generation time."""
from __future__ import annotations

import base64

import httpx
from openai import OpenAI
from pydantic import BaseModel, ValidationError

from content_pilot.ai.prompts import SYSTEM_INSTRUCTION
from content_pilot.ai.schemas import ContentPlanAI, ImagePromptAI, PostGenerationAI
from content_pilot.config import AISettings


class AIError(Exception):
    """Base error safe to translate into an HTTP response."""


class AIConfigurationError(AIError):
    pass


class AIProviderError(AIError):
    pass


class AIResponseValidationError(AIError):
    pass


class AIClient:
    def __init__(self, settings: AISettings) -> None:
        self.settings = settings

    def _client(self) -> OpenAI:
        if self.settings.proxyapi_api_key is None or not self.settings.proxyapi_api_key.get_secret_value():
            raise AIConfigurationError("AI generation is not configured")
        return OpenAI(
            api_key=self.settings.proxyapi_api_key.get_secret_value(),
            base_url=self.settings.proxyapi_base_url,
            timeout=self.settings.ai_timeout_seconds,
        )

    def _structured(self, prompt: str, schema: type[BaseModel]) -> BaseModel:
        try:
            response = self._client().beta.chat.completions.parse(
                model=self.settings.ai_text_model,
                messages=[
                    {"role": "system", "content": SYSTEM_INSTRUCTION},
                    {"role": "user", "content": prompt},
                ],
                response_format=schema,
            )
            parsed = response.choices[0].message.parsed
        except AIError:
            raise
        except Exception as error:
            raise AIProviderError("AI text provider is unavailable") from error
        if parsed is None:
            raise AIResponseValidationError("AI returned no structured response")
        try:
            return schema.model_validate(parsed)
        except ValidationError as error:
            raise AIResponseValidationError("AI returned an invalid structured response") from error

    def generate_content_plan(self, prompt: str) -> ContentPlanAI:
        return self._structured(prompt, ContentPlanAI)  # type: ignore[return-value]

    def generate_post(self, prompt: str) -> PostGenerationAI:
        return self._structured(prompt, PostGenerationAI)  # type: ignore[return-value]

    def generate_image_prompt(self, prompt: str) -> ImagePromptAI:
        return self._structured(prompt, ImagePromptAI)  # type: ignore[return-value]

    def generate_image(self, prompt: str) -> bytes:
        try:
            response = self._client().images.generate(
                model=self.settings.ai_image_model, prompt=prompt, size="1024x1024"
            )
            image = response.data[0]
            if image.b64_json:
                return base64.b64decode(image.b64_json, validate=True)
            if image.url:
                with httpx.Client(timeout=self.settings.ai_timeout_seconds, follow_redirects=True) as client:
                    downloaded = client.get(image.url)
                if downloaded.is_error:
                    raise AIProviderError(f"AI image download failed with HTTP {downloaded.status_code}")
                return downloaded.content
        except AIError:
            raise
        except Exception as error:
            raise AIProviderError("AI image provider is unavailable") from error
        raise AIResponseValidationError("AI returned no image data")
