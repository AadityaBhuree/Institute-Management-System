"""Campus Assets, Laboratory Equipment & Inventory Circulation Hub API Router."""

import sqlite3
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.database.connection import get_db
from src.models.asset import (
    AssetCheckoutCreate,
    AssetCheckoutOut,
    AssetCreate,
    AssetMaintenanceCreate,
    AssetMaintenanceOut,
    AssetMaintenanceStatusUpdate,
    AssetOut,
    AssetReturnUpdate,
    AssetStatsOut,
    AssetUpdate,
)
from src.services.asset_service import AssetService

router = APIRouter(prefix="/api/inventory", tags=["Campus Assets & Lab Inventory"])


@router.get("/assets", response_model=List[AssetOut])
def list_assets(
    category: Optional[str] = Query(
        None,
        description="LAB_EQUIPMENT, COMPUTING, AV_MULTIMEDIA, RESEARCH_INSTRUMENT, FURNITURE, OTHER",
    ),
    status: Optional[str] = Query(
        None, description="AVAILABLE, CHECKED_OUT, MAINTENANCE, DECOMMISSIONED"
    ),
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    lab_room: Optional[str] = Query(None, description="Filter by lab room or location"),
    search: Optional[str] = Query(None, description="Search by name, tag, serial, or room"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """List laboratory instruments and campus equipment with multi-criteria filtering."""
    return AssetService.list_assets(
        conn,
        category=category,
        status=status,
        department_id=department_id,
        lab_room=lab_room,
        search=search,
    )


@router.post("/assets", response_model=AssetOut, status_code=status.HTTP_201_CREATED)
def create_asset(data: AssetCreate, conn: sqlite3.Connection = Depends(get_db)):
    """Register a new institutional asset or laboratory instrument."""
    try:
        return AssetService.create_asset(conn, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/assets/stats", response_model=AssetStatsOut)
def get_inventory_stats(conn: sqlite3.Connection = Depends(get_db)):
    """Retrieve inventory valuation, active loans, and maintenance telemetry."""
    return AssetService.get_stats(conn)


@router.get("/assets/{id}", response_model=AssetOut)
def get_asset_by_id(id: int, conn: sqlite3.Connection = Depends(get_db)):
    """Retrieve detailed asset profile with circulation history and maintenance ledger."""
    asset = AssetService.get_asset_by_id(conn, id)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset #{id} not found")
    return asset


@router.put("/assets/{id}", response_model=AssetOut)
def update_asset(
    id: int,
    data: AssetUpdate,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Update asset specifications, lab room location, or status."""
    try:
        return AssetService.update_asset(conn, id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/checkouts", response_model=AssetCheckoutOut, status_code=status.HTTP_201_CREATED)
def checkout_asset(
    data: AssetCheckoutCreate,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Check out campus equipment or lab gear to an active scholar or faculty instructor."""
    try:
        return AssetService.checkout_asset(conn, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/checkouts", response_model=List[AssetCheckoutOut])
def list_checkouts(
    status: Optional[str] = Query(None, description="ACTIVE, RETURNED, OVERDUE"),
    asset_id: Optional[int] = Query(None, description="Filter by asset ID"),
    student_id: Optional[int] = Query(None, description="Filter by student ID"),
    faculty_id: Optional[int] = Query(None, description="Filter by faculty ID"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """List circulation checkouts with borrower details and overdue indicators."""
    return AssetService.list_checkouts(
        conn,
        status=status,
        asset_id=asset_id,
        student_id=student_id,
        faculty_id=faculty_id,
    )


@router.put("/checkouts/{id}/return", response_model=AssetCheckoutOut)
def return_asset(
    id: int,
    data: AssetReturnUpdate,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Process return of checked out asset with condition inspection."""
    try:
        return AssetService.return_asset(conn, id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/maintenance", response_model=AssetMaintenanceOut, status_code=status.HTTP_201_CREATED
)
def schedule_maintenance(
    data: AssetMaintenanceCreate,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Schedule calibration, preventative servicing, or equipment repair ticket."""
    try:
        return AssetService.schedule_maintenance(conn, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/maintenance", response_model=List[AssetMaintenanceOut])
def list_maintenance(
    status: Optional[str] = Query(None, description="SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED"),
    asset_id: Optional[int] = Query(None, description="Filter by asset ID"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """List scheduled and completed maintenance or calibration tickets."""
    return AssetService.list_maintenance(conn, status=status, asset_id=asset_id)


@router.put("/maintenance/{id}/status", response_model=AssetMaintenanceOut)
def update_maintenance_status(
    id: int,
    data: AssetMaintenanceStatusUpdate,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Update maintenance ticket status and return asset to service upon resolution."""
    try:
        return AssetService.update_maintenance_status(conn, id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
