"""Career Placements & Campus Recruitment Cell Schemas."""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class PlacementDriveBase(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=150)
    industry: str = Field("Technology & Software", max_length=100)
    job_title: str = Field(..., min_length=2, max_length=150)
    job_location: str = Field("Bengaluru / Hybrid", max_length=150)
    package_lpa: float = Field(..., gt=0.0, description="Package in Lakhs Per Annum")
    min_gpa_required: float = Field(6.5, ge=0.0, le=10.0)
    eligible_departments: str = Field("ALL", max_length=100)
    drive_date: str = Field(..., description="ISO Date YYYY-MM-DD")
    registration_deadline: str = Field(..., description="ISO Date YYYY-MM-DD")
    status: Literal["UPCOMING", "ACTIVE", "CLOSED"] = "ACTIVE"


class PlacementDriveCreate(PlacementDriveBase):
    pass


class PlacementDriveOut(PlacementDriveBase):
    id: int
    applications_count: Optional[int] = 0
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class PlacementApplicationCreate(BaseModel):
    drive_id: int = Field(..., gt=0)
    student_id: int = Field(..., gt=0)
    current_gpa: float = Field(..., ge=0.0, le=10.0)
    resume_link: Optional[str] = None
    remarks: Optional[str] = None


class PlacementStatusUpdate(BaseModel):
    status: Literal["APPLIED", "SHORTLISTED", "TECHNICAL_ROUND", "SELECTED", "REJECTED"]
    interview_date: Optional[str] = None
    offer_package_lpa: Optional[float] = Field(None, ge=0.0)
    remarks: Optional[str] = None


class PlacementApplicationOut(BaseModel):
    id: int
    drive_id: int
    student_id: int
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    package_lpa: Optional[float] = None
    student_name: Optional[str] = None
    enrollment_no: Optional[str] = None
    department_code: Optional[str] = None
    current_gpa: float
    resume_link: Optional[str] = None
    status: Literal["APPLIED", "SHORTLISTED", "TECHNICAL_ROUND", "SELECTED", "REJECTED"]
    interview_date: Optional[str] = None
    offer_package_lpa: Optional[float] = None
    remarks: Optional[str] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class PlacementStatsOut(BaseModel):
    total_drives: int
    active_drives: int
    total_applications: int
    selected_offers: int
    average_package_lpa: float
    highest_package_lpa: float
