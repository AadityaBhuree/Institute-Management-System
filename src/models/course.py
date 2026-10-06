"""Course data models and schemas."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CourseBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=20, description="Course code e.g. CS101")
    title: str = Field(..., min_length=3, max_length=150)
    department_id: int = Field(..., gt=0)
    credits: int = Field(3, gt=0, le=12)
    semester: int = Field(1, ge=1, le=8)
    capacity: int = Field(60, gt=0, le=500)
    syllabus_summary: Optional[str] = None
    instructor_id: Optional[int] = None


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    code: Optional[str] = None
    title: Optional[str] = None
    department_id: Optional[int] = None
    credits: Optional[int] = None
    semester: Optional[int] = None
    capacity: Optional[int] = None
    syllabus_summary: Optional[str] = None
    instructor_id: Optional[int] = None


class CourseOut(CourseBase):
    id: int
    department_name: Optional[str] = None
    department_code: Optional[str] = None
    instructor_name: Optional[str] = None
    enrolled_count: int = 0
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class EnrollmentCreate(BaseModel):
    student_id: int = Field(..., gt=0)
    course_id: int = Field(..., gt=0)
    academic_year: str = Field("2026-2027")
    semester: int = Field(1, ge=1, le=8)
