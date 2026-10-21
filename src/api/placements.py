"""Campus Placements & Corporate Recruitment API Router."""

import sqlite3
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.database.connection import get_db
from src.models.placement import (
    PlacementApplicationCreate,
    PlacementApplicationOut,
    PlacementDriveCreate,
    PlacementDriveOut,
    PlacementStatsOut,
    PlacementStatusUpdate,
)
from src.services.placement_service import PlacementService

router = APIRouter(prefix="/api/placements", tags=["Placements & Career Cell"])


@router.get("/drives", response_model=List[PlacementDriveOut])
def list_drives(
    drive_status: Optional[str] = Query(
        None, alias="status", description="UPCOMING, ACTIVE, CLOSED"
    ),
    search: Optional[str] = Query(None, description="Search company, job title, or industry"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """List recruitment drives with applicants telemetry."""
    return PlacementService.list_drives(conn, status=drive_status, search=search)


@router.post("/drives", response_model=PlacementDriveOut, status_code=status.HTTP_201_CREATED)
def create_drive(data: PlacementDriveCreate, conn: sqlite3.Connection = Depends(get_db)):
    """Host a new campus corporate recruitment drive."""
    try:
        return PlacementService.create_drive(conn, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/applications", response_model=List[PlacementApplicationOut])
def list_applications(
    drive_id: Optional[int] = Query(None, description="Filter by placement drive ID"),
    student_id: Optional[int] = Query(None, description="Filter by candidate student ID"),
    app_status: Optional[str] = Query(
        None,
        alias="status",
        description="APPLIED, SHORTLISTED, TECHNICAL_ROUND, SELECTED, REJECTED",
    ),
    conn: sqlite3.Connection = Depends(get_db),
):
    """List student placement applications and interview pipelines."""
    return PlacementService.list_applications(
        conn, drive_id=drive_id, student_id=student_id, status=app_status
    )


@router.post("/apply", response_model=PlacementApplicationOut, status_code=status.HTTP_201_CREATED)
def apply_for_drive(data: PlacementApplicationCreate, conn: sqlite3.Connection = Depends(get_db)):
    """Submit a scholar job application with GPA validation."""
    try:
        return PlacementService.apply_for_drive(conn, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.put("/applications/{id}/status", response_model=PlacementApplicationOut)
def update_application_status(
    id: int,
    data: PlacementStatusUpdate,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Advance candidate interview stage or confirm job offer package."""
    try:
        return PlacementService.update_application_status(conn, id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/stats", response_model=PlacementStatsOut)
def get_placement_stats(conn: sqlite3.Connection = Depends(get_db)):
    """Aggregate career placements, offer packages, and hiring statistics."""
    return PlacementService.get_stats(conn)
