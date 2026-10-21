"""Timetable and Lecture Scheduling Schemas."""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class TimetableSlotBase(BaseModel):
    course_id: int = Field(..., gt=0)
    day_of_week: Literal["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    start_time: str = Field(..., description="Format HH:MM e.g. 09:00")
    end_time: str = Field(..., description="Format HH:MM e.g. 10:30")
    room_number: str = Field(..., min_length=2, max_length=50)
    building: str = Field(default="Main Academic Block", max_length=100)


class TimetableSlotCreate(TimetableSlotBase):
    pass


class TimetableSlotOut(TimetableSlotBase):
    id: int
    course_code: Optional[str] = None
    course_title: Optional[str] = None
    instructor_name: Optional[str] = None
    department_name: Optional[str] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)
