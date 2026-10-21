"""Common Pydantic models for responses and errors."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standardized error response payload."""

    detail: str = Field(..., description="Human-readable error explanation.")
    error_code: Optional[str] = Field(None, description="Domain-specific error classifier code.")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the error event.",
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional diagnostic metadata.")


class MessageResponse(BaseModel):
    """Standardized informational/success message payload."""

    message: str = Field(..., description="Status or confirmation message.")
    success: bool = Field(True, description="Boolean flag confirming successful execution.")
