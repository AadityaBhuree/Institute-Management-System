"""Notification and Institutional Alert Data Models."""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

NotificationCategory = Literal["ACADEMIC", "FINANCE", "HEALTH", "PLACEMENT", "SYSTEM", "GENERAL"]
NotificationPriority = Literal["LOW", "NORMAL", "HIGH", "URGENT"]
RecipientRole = Literal["ALL", "ADMIN", "FACULTY", "STUDENT"]


class NotificationBase(BaseModel):
    recipient_role: RecipientRole = Field(
        default="ALL", description="Target audience role for notification"
    )
    recipient_id: Optional[int] = Field(
        None, description="Specific scholar or faculty member ID (null for broadcast)"
    )
    title: str = Field(..., min_length=3, max_length=150)
    message: str = Field(..., min_length=5, max_length=1000)
    category: NotificationCategory = Field(default="GENERAL")
    priority: NotificationPriority = Field(default="NORMAL")
    action_url: Optional[str] = Field(None, max_length=255)


class NotificationCreate(NotificationBase):
    pass


class NotificationOut(NotificationBase):
    id: int
    is_read: bool
    created_at: str

    model_config = ConfigDict(from_attributes=True)
