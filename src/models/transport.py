"""Campus Transport Fleet & Transit Logistics Pydantic Schemas."""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class TransportRouteBase(BaseModel):
    route_name: str = Field(..., min_length=2, max_length=100)
    source: str = Field(..., min_length=2, max_length=150)
    destination: str = Field(..., min_length=2, max_length=150)
    total_stops: int = Field(5, ge=1, le=50)
    fare_per_semester: float = Field(..., ge=0.0)
    status: Literal["ACTIVE", "INACTIVE"] = "ACTIVE"


class TransportRouteCreate(TransportRouteBase):
    pass


class TransportRouteOut(TransportRouteBase):
    id: int
    assigned_vehicles_count: Optional[int] = 0
    active_passes_count: Optional[int] = 0
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class TransportVehicleBase(BaseModel):
    route_id: Optional[int] = Field(None, gt=0)
    vehicle_number: str = Field(..., min_length=3, max_length=50)
    driver_name: str = Field(..., min_length=2, max_length=100)
    driver_phone: str = Field(..., min_length=5, max_length=20)
    capacity: int = Field(..., ge=5, le=120)
    status: Literal["ACTIVE", "MAINTENANCE", "RETIRED"] = "ACTIVE"


class TransportVehicleCreate(TransportVehicleBase):
    pass


class TransportVehicleOut(TransportVehicleBase):
    id: int
    route_name: Optional[str] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class TransportPassCreate(BaseModel):
    student_id: int = Field(..., gt=0)
    route_id: int = Field(..., gt=0)
    pickup_stop: str = Field(..., min_length=2, max_length=150)
    academic_year: str = Field("2026-2027", max_length=20)
    valid_until: str = Field(..., description="ISO Date YYYY-MM-DD")


class TransportPassOut(BaseModel):
    id: int
    student_id: int
    route_id: int
    pass_number: str
    student_name: Optional[str] = None
    enrollment_no: Optional[str] = None
    department_code: Optional[str] = None
    route_name: Optional[str] = None
    pickup_stop: str
    academic_year: str
    valid_until: str
    status: Literal["ACTIVE", "EXPIRED", "CANCELLED"]
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class TransportStatsOut(BaseModel):
    total_routes: int
    active_routes: int
    total_vehicles: int
    active_passes: int
    total_capacity: int
    fleet_occupancy_pct: float
