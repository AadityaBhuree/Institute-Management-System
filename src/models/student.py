"""Student schemas for admissions and student registry."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class StudentBase(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    phone: Optional[str] = Field(None, max_length=20)
    dob: Optional[str] = Field(None, description="YYYY-MM-DD")
    gender: Optional[str] = Field(None, description="Male, Female, Other, Prefer Not to Say")
    blood_group: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    department_id: int = Field(..., gt=0)
    current_semester: int = Field(1, ge=1, le=8)
    status: str = Field(
        "ENROLLED", description="ENROLLED, PENDING, PROBATION, SUSPENDED, GRADUATED, WITHDRAWN"
    )


class StudentCreate(StudentBase):
    admission_date: Optional[str] = Field(None, description="Defaults to current date if omitted")


class StudentUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = Field(None, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    phone: Optional[str] = None
    dob: Optional[str] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    department_id: Optional[int] = None
    current_semester: Optional[int] = None
    status: Optional[str] = None


class StudentOut(StudentBase):
    id: int
    enrollment_no: str
    admission_date: str
    department_name: Optional[str] = None
    department_code: Optional[str] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
