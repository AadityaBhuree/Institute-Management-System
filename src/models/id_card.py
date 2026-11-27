"""Digital ID Card Verification & Metadata Data Models."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class IDCardVerificationOut(BaseModel):
    valid: bool
    status: str
    entity_type: Optional[str] = None
    identifier: Optional[str] = None
    name: Optional[str] = None
    department: Optional[str] = None
    valid_until: Optional[str] = None
    issued_by: Optional[str] = None
    reason: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)
