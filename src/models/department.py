"""Department schemas."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DepartmentBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=10, description="Department code, e.g. CSE")
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentOut(DepartmentBase):
    id: int
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
