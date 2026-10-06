"""Faculty data models and schemas."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class FacultyBase(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    phone: Optional[str] = None
    department_id: int = Field(..., gt=0)
    designation: str = Field("Assistant Professor", max_length=100)
    qualification: Optional[str] = None
    hire_date: Optional[str] = Field(None, description="YYYY-MM-DD")
    status: str = Field("ACTIVE", description="ACTIVE, ON_LEAVE, RESIGNED, RETIRED")


class FacultyCreate(FacultyBase):
    pass


class FacultyUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = Field(None, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    phone: Optional[str] = None
    department_id: Optional[int] = None
    designation: Optional[str] = None
    qualification: Optional[str] = None
    status: Optional[str] = None


class FacultyOut(FacultyBase):
    id: int
    faculty_id: str
    hire_date: str
    department_name: Optional[str] = None
    department_code: Optional[str] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
