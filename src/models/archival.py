"""Pydantic schemas for scholar cohort archival and cryptographic verification."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CohortArchivalRequest(BaseModel):
    """Payload to initiate a policy-driven scholar cohort archival."""

    model_config = ConfigDict(extra="forbid")

    graduation_year: int = Field(..., ge=1950, le=2100, description="Target cohort graduation year")
    department_id: Optional[int] = Field(None, description="Optional department filter")
    notes: Optional[str] = Field(None, max_length=500, description="Administrative archival notes")


class ArchivedStudentItem(BaseModel):
    """Archived scholar record item."""

    id: int
    original_student_id: int
    enrollment_no: str
    full_name: str
    email: Optional[str] = None
    department_code: str
    graduation_year: int
    final_cgpa: float
    total_credits: int
    integrity_hash: str
    archived_by: str
    archived_at: str


class CohortArchivalResponse(BaseModel):
    """Response returned upon completing cohort archival."""

    status: str
    graduation_year: int
    archived_count: int
    archived_records: List[ArchivedStudentItem]


class ArchivalIntegrityResponse(BaseModel):
    """Result of SHA-256 cryptographic verification of cold archive snapshot."""

    archive_id: int
    enrollment_no: str
    is_valid: bool
    stored_hash: str
    computed_hash: str
    archived_at: str
