"""Hostel & Residential Hall Management API Router."""

import sqlite3
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.database.connection import get_db
from src.models.hostel import (
    HostelBlockCreate,
    HostelBlockOut,
    HostelRoomCreate,
    HostelRoomOut,
    HostelStatsOut,
    RoomAllocationCreate,
    RoomAllocationOut,
    RoomCheckoutRequest,
)
from src.services.hostel_service import HostelService

router = APIRouter(prefix="/api/hostel", tags=["Hostel Management"])


@router.get("/blocks", response_model=List[HostelBlockOut])
def list_blocks(conn: sqlite3.Connection = Depends(get_db)):
    """List all residential blocks and wardens."""
    return HostelService.list_blocks(conn)


@router.post("/blocks", response_model=HostelBlockOut, status_code=status.HTTP_201_CREATED)
def create_block(data: HostelBlockCreate, conn: sqlite3.Connection = Depends(get_db)):
    """Add a new residential block."""
    try:
        return HostelService.create_block(conn, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/rooms", response_model=List[HostelRoomOut])
def list_rooms(
    block_id: Optional[int] = Query(None, description="Filter by residential block"),
    room_type: Optional[str] = Query(None, description="SINGLE, DOUBLE, TRIPLE, DORM"),
    room_status: Optional[str] = Query(
        None, alias="status", description="AVAILABLE, FULL, MAINTENANCE"
    ),
    conn: sqlite3.Connection = Depends(get_db),
):
    """List hostel rooms with occupancy metrics."""
    return HostelService.list_rooms(
        conn, block_id=block_id, room_type=room_type, status=room_status
    )


@router.post("/rooms", response_model=HostelRoomOut, status_code=status.HTTP_201_CREATED)
def create_room(data: HostelRoomCreate, conn: sqlite3.Connection = Depends(get_db)):
    """Add a room to a residential block."""
    try:
        return HostelService.create_room(conn, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/allocations", response_model=List[RoomAllocationOut])
def list_allocations(
    alloc_status: Optional[str] = Query(
        None, alias="status", description="ACTIVE, CHECKED_OUT, CANCELLED"
    ),
    block_id: Optional[int] = Query(None, description="Filter allocations by block"),
    student_id: Optional[int] = Query(None, description="Filter allocations by student"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """List student room allocations and tenant directory."""
    return HostelService.list_allocations(
        conn, status=alloc_status, block_id=block_id, student_id=student_id
    )


@router.post("/allocate", response_model=RoomAllocationOut, status_code=status.HTTP_201_CREATED)
def allocate_room(data: RoomAllocationCreate, conn: sqlite3.Connection = Depends(get_db)):
    """Allocate a bed in a room to a student."""
    try:
        return HostelService.allocate_room(conn, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/checkout/{allocation_id}", response_model=RoomAllocationOut)
def checkout_room(
    allocation_id: int,
    data: RoomCheckoutRequest,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Process student room check-out and restore bed availability."""
    try:
        return HostelService.checkout_room(conn, allocation_id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/stats", response_model=HostelStatsOut)
def get_hostel_stats(conn: sqlite3.Connection = Depends(get_db)):
    """Retrieve overall residential capacity and occupancy telemetry."""
    return HostelService.get_stats(conn)
