"""Alumni Network & Career Mentorship Hub Pydantic Schemas."""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class AlumniMemberBase(BaseModel):
    student_id: Optional[int] = Field(None, gt=0)
    full_name: str = Field(..., min_length=2, max_length=150)
    email: str = Field(..., min_length=5, max_length=150)
    phone: Optional[str] = Field(None, max_length=25)
    graduation_year: int = Field(..., ge=1950, le=2030)
    degree: str = Field("B.Tech", max_length=50)
    department_id: int = Field(..., gt=0)
    current_company: str = Field("Independent / Higher Studies", max_length=150)
    job_title: str = Field("Alumnus", max_length=150)
    city: str = Field("Bengaluru", max_length=100)
    linkedin_url: Optional[str] = Field(None, max_length=250)
    mentorship_status: Literal["AVAILABLE", "BUSY", "INACTIVE"] = "AVAILABLE"


class AlumniMemberCreate(AlumniMemberBase):
    pass


class AlumniMemberOut(AlumniMemberBase):
    id: int
    department_name: Optional[str] = None
    department_code: Optional[str] = None
    mentorship_requests_count: Optional[int] = 0
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class AlumniMentorshipRequestCreate(BaseModel):
    alumni_id: int = Field(..., gt=0)
    student_id: int = Field(..., gt=0)
    mentorship_topic: str = Field(..., min_length=5, max_length=250)
    notes: Optional[str] = None


class AlumniMentorshipStatusUpdate(BaseModel):
    status: Literal["REQUESTED", "ACCEPTED", "COMPLETED", "DECLINED"]
    notes: Optional[str] = None


class AlumniMentorshipRequestOut(BaseModel):
    id: int
    alumni_id: int
    student_id: int
    alumni_name: Optional[str] = None
    alumni_company: Optional[str] = None
    alumni_job_title: Optional[str] = None
    student_name: Optional[str] = None
    enrollment_no: Optional[str] = None
    department_code: Optional[str] = None
    mentorship_topic: str
    status: Literal["REQUESTED", "ACCEPTED", "COMPLETED", "DECLINED"]
    notes: Optional[str] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class AlumniStatsOut(BaseModel):
    total_alumni: int
    available_mentors: int
    graduating_batches_count: int
    active_mentorships: int
    completed_mentorships: int
