"""Hostel & Residential Hall Management Schemas."""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class HostelBlockBase(BaseModel):
    block_name: str = Field(..., min_length=2, max_length=100)
    gender_type: Literal["MALE", "FEMALE", "COED"] = "COED"
    total_rooms: int = Field(10, ge=1)
    warden_name: str = Field(..., min_length=2, max_length=150)
    warden_contact: Optional[str] = None


class HostelBlockCreate(HostelBlockBase):
    pass


class HostelBlockOut(HostelBlockBase):
    id: int
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class HostelRoomBase(BaseModel):
    block_id: int = Field(..., gt=0)
    room_number: str = Field(..., min_length=1, max_length=20)
    room_type: Literal["SINGLE", "DOUBLE", "TRIPLE", "DORM"] = "DOUBLE"
    capacity: int = Field(2, ge=1)
    floor: int = Field(1, ge=0)
    fee_per_semester: float = Field(1200.0, ge=0.0)


class HostelRoomCreate(HostelRoomBase):
    pass


class HostelRoomOut(HostelRoomBase):
    id: int
    current_occupancy: int
    status: Literal["AVAILABLE", "FULL", "MAINTENANCE"]
    block_name: Optional[str] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class RoomAllocationCreate(BaseModel):
    room_id: int = Field(..., gt=0)
    student_id: int = Field(..., gt=0)
    academic_year: str = Field("2026-2027", min_length=4, max_length=15)
    check_in_date: str = Field(..., description="ISO Date YYYY-MM-DD")
    remarks: Optional[str] = None


class RoomCheckoutRequest(BaseModel):
    check_out_date: str = Field(..., description="ISO Date YYYY-MM-DD")
    remarks: Optional[str] = None


class RoomAllocationOut(BaseModel):
    id: int
    room_id: int
    student_id: int
    room_number: Optional[str] = None
    block_name: Optional[str] = None
    student_name: Optional[str] = None
    enrollment_no: Optional[str] = None
    academic_year: str
    check_in_date: str
    check_out_date: Optional[str] = None
    status: Literal["ACTIVE", "CHECKED_OUT", "CANCELLED"]
    remarks: Optional[str] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class HostelStatsOut(BaseModel):
    total_blocks: int
    total_rooms: int
    total_beds: int
    occupied_beds: int
    available_beds: int
    active_residents: int
