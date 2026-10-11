"""HTTP request and response contracts for manual M2 validation."""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from content_pilot.models.enums import ContentItemStatus, MediaSource, MediaType, Platform, PostStatus


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    audience: str | None = None
    tone_of_voice: str | None = None
    language: str = Field(default="ru", min_length=1, max_length=16)


class ProjectRead(APIModel):
    id: UUID
    name: str
    description: str | None
    audience: str | None
    tone_of_voice: str | None
    language: str
    created_at: datetime
    updated_at: datetime


class ContentPlanGenerate(BaseModel):
    start_date: date
    end_date: date
    posts_count: int = Field(ge=1, le=100)
    platforms: list[Platform] = Field(min_length=1)


class ContentItemRead(APIModel):
    id: UUID
    project_id: UUID
    title: str
    topic: str | None
    goal: str | None
    content_type: str
    planned_date: date | None
    status: ContentItemStatus
    created_at: datetime
    updated_at: datetime


class PostGenerate(BaseModel):
    platform: Platform
    instructions: str | None = Field(default=None, max_length=2000)


class PostRead(APIModel):
    id: UUID
    content_item_id: UUID
    platform: Platform
    text: str | None
    status: PostStatus
    scheduled_at: datetime | None
    published_at: datetime | None
    external_post_id: str | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class MediaAssetRead(APIModel):
    id: UUID
    post_id: UUID
    media_type: MediaType
    source: MediaSource
    file_path: str | None
    prompt: str | None
    created_at: datetime
    media_url: str | None = None
