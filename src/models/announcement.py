"""Announcement schemas."""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class AnnouncementBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=200, description="Announcement headline")
    content: str = Field(..., min_length=5, description="Full notice message body")
    category: Literal["ACADEMIC", "EXAM", "FEES", "EVENT", "URGENT", "GENERAL"] = "GENERAL"
    target_audience: Literal["ALL", "STUDENTS", "FACULTY"] = "ALL"
    priority: Literal["HIGH", "NORMAL", "LOW"] = "NORMAL"
    author_name: str = Field(default="Office of Academic Affairs", max_length=100)
    expires_at: Optional[str] = None


class AnnouncementCreate(AnnouncementBase):
    pass


class AnnouncementOut(AnnouncementBase):
    id: int
    is_active: int
    created_at: str

    model_config = ConfigDict(from_attributes=True)
