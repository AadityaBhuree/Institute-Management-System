"""Campus Events, Seminars & Symposium Hub Pydantic Schemas."""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class EventBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=150)
    category: Literal[
        "SEMINAR",
        "WORKSHOP",
        "SYMPOSIUM",
        "HACKATHON",
        "CULTURAL",
        "SPORTS",
        "CONFERENCE",
    ] = "SEMINAR"
    department_id: Optional[int] = Field(None, gt=0)
    organizer_faculty_id: Optional[int] = Field(None, gt=0)
    venue: str = Field(..., min_length=2, max_length=100)
    event_date: str = Field(..., description="ISO Date YYYY-MM-DD")
    start_time: str = Field(..., description="HH:MM format e.g. 09:30")
    end_time: str = Field(..., description="HH:MM format e.g. 17:00")
    max_capacity: int = Field(100, ge=1, le=5000)
    registration_fee: float = Field(0.0, ge=0.0)
    status: Literal["UPCOMING", "ACTIVE", "COMPLETED", "CANCELLED"] = "UPCOMING"
    description: Optional[str] = None


class EventCreate(EventBase):
    pass


class EventStatusUpdate(BaseModel):
    status: Literal["UPCOMING", "ACTIVE", "COMPLETED", "CANCELLED"]


class EventOut(EventBase):
    id: int
    event_code: str
    department_name: Optional[str] = None
    organizer_name: Optional[str] = None
    registered_count: int = 0
    attended_count: int = 0
    available_seats: int = 0
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class EventRegistrationCreate(BaseModel):
    event_id: int = Field(..., gt=0)
    student_id: int = Field(..., gt=0)


class EventRegistrationStatusUpdate(BaseModel):
    status: Literal["REGISTERED", "ATTENDED", "CANCELLED"]
    certificate_issued: Optional[int] = Field(None, ge=0, le=1)


class EventRegistrationOut(BaseModel):
    id: int
    event_id: int
    student_id: int
    registration_number: str
    event_title: Optional[str] = None
    event_code: Optional[str] = None
    student_name: Optional[str] = None
    enrollment_no: Optional[str] = None
    department_code: Optional[str] = None
    status: Literal["REGISTERED", "ATTENDED", "CANCELLED"]
    certificate_issued: int
    attendance_marked_at: Optional[str] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class EventStatsOut(BaseModel):
    total_events: int
    upcoming_events: int
    active_or_completed_events: int
    total_registrations: int
    total_attended: int
    total_certificates_issued: int
