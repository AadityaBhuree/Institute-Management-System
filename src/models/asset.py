"""Campus Assets, Laboratory Equipment & Inventory Circulation Hub Models."""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class AssetBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    category: Literal[
        "LAB_EQUIPMENT",
        "COMPUTING",
        "AV_MULTIMEDIA",
        "RESEARCH_INSTRUMENT",
        "FURNITURE",
        "OTHER",
    ] = "LAB_EQUIPMENT"
    department_id: Optional[int] = Field(None, gt=0)
    lab_room: str = Field(..., min_length=2, max_length=100)
    serial_number: Optional[str] = Field(None, max_length=100)
    model_number: Optional[str] = Field(None, max_length=100)
    manufacturer: Optional[str] = Field(None, max_length=100)
    purchase_date: str = Field(..., description="ISO Date YYYY-MM-DD")
    purchase_cost: float = Field(..., ge=0.0)
    warranty_expiry: Optional[str] = Field(None, description="ISO Date YYYY-MM-DD")
    status: Literal["AVAILABLE", "CHECKED_OUT", "MAINTENANCE", "DECOMMISSIONED"] = "AVAILABLE"


class AssetCreate(AssetBase):
    pass


class AssetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    lab_room: Optional[str] = Field(None, min_length=2, max_length=100)
    status: Optional[Literal["AVAILABLE", "CHECKED_OUT", "MAINTENANCE", "DECOMMISSIONED"]] = None
    warranty_expiry: Optional[str] = None
    model_number: Optional[str] = None
    manufacturer: Optional[str] = None


class AssetOut(AssetBase):
    id: int
    asset_tag: str
    department_name: Optional[str] = None
    department_code: Optional[str] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class AssetCheckoutCreate(BaseModel):
    asset_id: int = Field(..., gt=0)
    borrower_type: Literal["STUDENT", "FACULTY"]
    student_id: Optional[int] = Field(None, gt=0)
    faculty_id: Optional[int] = Field(None, gt=0)
    checkout_date: str = Field(..., description="ISO Date YYYY-MM-DD")
    due_date: str = Field(..., description="ISO Date YYYY-MM-DD")
    condition_out: Literal["NEW", "EXCELLENT", "GOOD", "FAIR"] = "GOOD"
    notes: Optional[str] = None


class AssetReturnUpdate(BaseModel):
    returned_date: Optional[str] = Field(None, description="ISO Date YYYY-MM-DD")
    condition_in: Literal["EXCELLENT", "GOOD", "FAIR", "DAMAGED"] = "GOOD"
    notes: Optional[str] = None


class AssetCheckoutOut(BaseModel):
    id: int
    checkout_code: str
    asset_id: int
    asset_tag: Optional[str] = None
    asset_name: Optional[str] = None
    borrower_type: str
    borrower_name: Optional[str] = None
    borrower_identifier: Optional[str] = None
    student_id: Optional[int] = None
    faculty_id: Optional[int] = None
    checkout_date: str
    due_date: str
    returned_date: Optional[str] = None
    condition_out: str
    condition_in: Optional[str] = None
    status: Literal["ACTIVE", "RETURNED", "OVERDUE"]
    is_overdue: bool = False
    notes: Optional[str] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class AssetMaintenanceCreate(BaseModel):
    asset_id: int = Field(..., gt=0)
    maintenance_type: Literal[
        "CALIBRATION",
        "PREVENTATIVE",
        "REPAIR",
        "FIRMWARE_UPGRADE",
        "INSPECTION",
    ] = "CALIBRATION"
    scheduled_date: str = Field(..., description="ISO Date YYYY-MM-DD")
    technician_name: str = Field(..., min_length=2, max_length=100)
    cost: float = Field(0.0, ge=0.0)
    status: Literal["SCHEDULED", "IN_PROGRESS", "COMPLETED", "CANCELLED"] = "SCHEDULED"
    resolution_notes: Optional[str] = None


class AssetMaintenanceStatusUpdate(BaseModel):
    status: Literal["SCHEDULED", "IN_PROGRESS", "COMPLETED", "CANCELLED"]
    completed_date: Optional[str] = Field(None, description="ISO Date YYYY-MM-DD")
    cost: Optional[float] = Field(None, ge=0.0)
    resolution_notes: Optional[str] = None


class AssetMaintenanceOut(BaseModel):
    id: int
    maintenance_code: str
    asset_id: int
    asset_tag: Optional[str] = None
    asset_name: Optional[str] = None
    maintenance_type: str
    scheduled_date: str
    completed_date: Optional[str] = None
    technician_name: str
    cost: float
    status: str
    resolution_notes: Optional[str] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class AssetStatsOut(BaseModel):
    total_assets: int
    total_valuation: float
    available_assets: int
    active_checkouts: int
    in_maintenance: int
    overdue_checkouts: int
