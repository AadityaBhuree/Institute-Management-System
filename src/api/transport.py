"""Campus Transport Fleet & Transit Logistics API Router."""

import sqlite3
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.database.connection import get_db
from src.models.transport import (
    TransportPassCreate,
    TransportPassOut,
    TransportRouteCreate,
    TransportRouteOut,
    TransportStatsOut,
    TransportVehicleCreate,
    TransportVehicleOut,
)
from src.services.transport_service import TransportService

router = APIRouter(prefix="/api/transport", tags=["Transport Fleet & Logistics"])


@router.get("/routes", response_model=List[TransportRouteOut])
def list_routes(
    status: Optional[str] = Query(None, description="ACTIVE, INACTIVE"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """List transport routes with assigned vehicles and passes count."""
    return TransportService.list_routes(conn, status=status)


@router.post("/routes", response_model=TransportRouteOut, status_code=status.HTTP_201_CREATED)
def create_route(data: TransportRouteCreate, conn: sqlite3.Connection = Depends(get_db)):
    """Create a new campus bus route."""
    try:
        return TransportService.create_route(conn, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/vehicles", response_model=List[TransportVehicleOut])
def list_vehicles(
    route_id: Optional[int] = Query(None, description="Filter by route ID"),
    status: Optional[str] = Query(None, description="ACTIVE, MAINTENANCE, RETIRED"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """List fleet transit vehicles with assigned routes."""
    return TransportService.list_vehicles(conn, route_id=route_id, status=status)


@router.post("/vehicles", response_model=TransportVehicleOut, status_code=status.HTTP_201_CREATED)
def create_vehicle(data: TransportVehicleCreate, conn: sqlite3.Connection = Depends(get_db)):
    """Register a new vehicle in the campus fleet."""
    try:
        return TransportService.create_vehicle(conn, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/passes", response_model=List[TransportPassOut])
def list_passes(
    route_id: Optional[int] = Query(None, description="Filter by route ID"),
    student_id: Optional[int] = Query(None, description="Filter by student ID"),
    status: Optional[str] = Query(None, description="ACTIVE, EXPIRED, CANCELLED"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """List student transit passes and route allocations."""
    return TransportService.list_passes(
        conn, route_id=route_id, student_id=student_id, status=status
    )


@router.post("/passes", response_model=TransportPassOut, status_code=status.HTTP_201_CREATED)
def issue_transit_pass(data: TransportPassCreate, conn: sqlite3.Connection = Depends(get_db)):
    """Issue a student transit bus pass."""
    try:
        return TransportService.issue_transit_pass(conn, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.put("/passes/{id}/cancel", status_code=status.HTTP_200_OK)
def cancel_pass(id: int, conn: sqlite3.Connection = Depends(get_db)):
    """Cancel an active student transit pass."""
    success = TransportService.cancel_pass(conn, id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Pass #{id} not found")
    return {"message": f"Pass #{id} cancelled successfully."}


@router.get("/stats", response_model=TransportStatsOut)
def get_transport_stats(conn: sqlite3.Connection = Depends(get_db)):
    """Aggregate fleet vehicle count, active passes, and occupancy rate."""
    return TransportService.get_stats(conn)
