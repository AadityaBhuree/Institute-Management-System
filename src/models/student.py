"""Student schemas for admissions and student registry."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StudentBase(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)

    @field_validator("first_name", mode="before")
    @classmethod
    def validate_first_name(cls, v: str) -> str:
        if isinstance(v, str):
            stripped = v.strip()
            if len(stripped) < 2:
                raise ValueError("First name must contain at least 2 non-whitespace characters")
            return stripped
        return v

    @field_validator("last_name", mode="before")
    @classmethod
    def validate_last_name(cls, v: str) -> str:
        if isinstance(v, str):
            stripped = v.strip()
            if len(stripped) < 1:
                raise ValueError("Last name must contain at least 1 non-whitespace character")
            return stripped
        return v

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
    is_deleted: bool = False
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
