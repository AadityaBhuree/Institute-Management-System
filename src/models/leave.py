"""Institutional Leave & Absence Schemas."""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class LeaveRequestBase(BaseModel):
    applicant_type: Literal["STUDENT", "FACULTY"] = "STUDENT"
    applicant_id: int = Field(..., gt=0)
    applicant_name: str = Field(..., min_length=2, max_length=150)
    leave_type: Literal["SICK", "CASUAL", "ACADEMIC", "EMERGENCY", "MATERNITY", "DUTY"] = "CASUAL"
    start_date: str = Field(..., description="ISO Date YYYY-MM-DD")
    end_date: str = Field(..., description="ISO Date YYYY-MM-DD")
    reason: str = Field(..., min_length=5, description="Reason for absence request")


class LeaveRequestCreate(LeaveRequestBase):
    pass


class LeaveStatusUpdate(BaseModel):
    status: Literal["APPROVED", "REJECTED"]
    review_remarks: Optional[str] = None
    reviewed_by: Optional[str] = "Academic Dean"


class LeaveRequestOut(LeaveRequestBase):
    id: int
    status: Literal["PENDING", "APPROVED", "REJECTED"]
    review_remarks: Optional[str] = None
    reviewed_by: Optional[str] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)
