"""Pydantic Models for Institutional Email Subsystem."""

from typing import List, Optional

from pydantic import BaseModel, Field


class EmailSendRequest(BaseModel):
    """Payload to trigger an email dispatch."""

    recipient: str = Field(..., description="Target recipient email address")
    subject: str = Field(..., min_length=1, max_length=200, description="Email subject line")
    body_text: str = Field(..., min_length=1, description="Plaintext email fallback body")
    body_html: Optional[str] = Field(default=None, description="Optional rich HTML email body")
    template: Optional[str] = Field(default=None, description="Optional template identifier")


class EmailDeliveryResult(BaseModel):
    """Delivery confirmation or diagnostic result."""

    status: str = Field(..., description="Delivery status: SENT, MOCKED, FAILED, QUEUED")
    recipient: str
    subject: str
    template: Optional[str] = None
    message_id: Optional[str] = None
    delivered_at: Optional[str] = None
    error: Optional[str] = None


class EmailLogOut(BaseModel):
    """Recorded institutional email dispatch journal entry."""

    id: int
    recipient: str
    subject: str
    template: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    sent_at: str


class EmailLogListResponse(BaseModel):
    """Collection of recorded institutional email logs."""

    total: int
    logs: List[EmailLogOut]
