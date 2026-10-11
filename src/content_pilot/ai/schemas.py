"""Strict, provider-neutral structured output contracts."""
from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ContentGoal(str, Enum):
    EXPERTISE = "expertise"
    ENGAGEMENT = "engagement"
    EDUCATION = "education"
    PROMOTION = "promotion"
    PERSONAL_BRAND = "personal_brand"


class ContentType(str, Enum):
    EDUCATIONAL = "educational"
    STORY = "story"
    OPINION = "opinion"
    CASE_STUDY = "case_study"
    ANNOUNCEMENT = "announcement"
    CHECKLIST = "checklist"
    BEHIND_THE_SCENES = "behind_the_scenes"


class StrictAIModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ContentPlanItemAI(StrictAIModel):
    title: str = Field(max_length=255)
    topic: str = Field(max_length=255)
    goal: ContentGoal
    content_type: ContentType
    suggested_date: date
    rationale: str | None = Field(default=None, max_length=1000)

    @field_validator("title", "topic")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value.strip()


class ContentPlanAI(StrictAIModel):
    items: list[ContentPlanItemAI] = Field(min_length=1, max_length=100)


class PostGenerationAI(StrictAIModel):
    text: str = Field(max_length=10000)
    hook: str | None = Field(default=None, max_length=500)
    call_to_action: str | None = Field(default=None, max_length=500)
    hashtags: list[str] = Field(default_factory=list, max_length=10)
    image_needed: bool
    image_concept: str | None = Field(default=None, max_length=1000)

    @field_validator("text")
    @classmethod
    def text_nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value.strip()


class ImagePromptAI(StrictAIModel):
    prompt: str = Field(max_length=2000)
    alt_text: str = Field(max_length=500)

    @field_validator("prompt", "alt_text")
    @classmethod
    def fields_nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value.strip()
