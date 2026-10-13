"""Scholarships, Grants & Financial Aid Pydantic Schemas."""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ScholarshipSchemeBase(BaseModel):
    scheme_name: str = Field(..., min_length=2, max_length=150)
    sponsor_type: Literal["INSTITUTIONAL", "GOVERNMENT", "CORPORATE", "ALUMNI_ENDOWMENT"] = (
        "INSTITUTIONAL"
    )
    award_amount: float = Field(..., gt=0.0)
    min_gpa_required: float = Field(7.5, ge=0.0, le=10.0)
    max_family_income: float = Field(800000.0, gt=0.0)
    eligible_category: str = Field("ALL", max_length=100)
    status: Literal["ACTIVE", "CLOSED"] = "ACTIVE"


class ScholarshipSchemeCreate(ScholarshipSchemeBase):
    pass


class ScholarshipSchemeOut(ScholarshipSchemeBase):
    id: int
    applications_count: Optional[int] = 0
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class ScholarshipApplicationCreate(BaseModel):
    scheme_id: int = Field(..., gt=0)
    student_id: int = Field(..., gt=0)
    current_gpa: float = Field(..., ge=0.0, le=10.0)
    annual_family_income: float = Field(..., ge=0.0)


class ScholarshipReviewUpdate(BaseModel):
    status: Literal["APPROVED", "DISBURSED", "REJECTED"]
    review_remarks: Optional[str] = None
    disbursed_amount: Optional[float] = Field(None, ge=0.0)


class ScholarshipApplicationOut(BaseModel):
    id: int
    scheme_id: int
    student_id: int
    scheme_name: Optional[str] = None
    award_amount: Optional[float] = None
    student_name: Optional[str] = None
    enrollment_no: Optional[str] = None
    department_code: Optional[str] = None
    current_gpa: float
    annual_family_income: float
    disbursed_amount: float
    status: Literal["PENDING", "APPROVED", "DISBURSED", "REJECTED"]
    review_remarks: Optional[str] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class ScholarshipStatsOut(BaseModel):
    total_schemes: int
    active_schemes: int
    total_applications: int
    awarded_count: int
    total_funds_disbursed: float
    average_award_amount: float
