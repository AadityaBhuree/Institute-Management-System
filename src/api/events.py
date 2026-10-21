"""Campus Events, Seminars & Symposium Hub API Router."""

import sqlite3
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.database.connection import get_db
from src.models.event import (
    EventCreate,
    EventOut,
    EventRegistrationCreate,
    EventRegistrationOut,
    EventRegistrationStatusUpdate,
    EventStatsOut,
    EventStatusUpdate,
)
from src.services.event_service import EventService

router = APIRouter(prefix="/api/events", tags=["Campus Events & Symposiums"])


@router.get("", response_model=List[EventOut])
def list_events(
    category: Optional[str] = Query(
        None, description="SEMINAR, WORKSHOP, SYMPOSIUM, HACKATHON, CULTURAL, SPORTS, CONFERENCE"
    ),
    status: Optional[str] = Query(None, description="UPCOMING, ACTIVE, COMPLETED, CANCELLED"),
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    search: Optional[str] = Query(None, description="Search by title, venue, or event code"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """List campus events with category, status, and department filtering."""
    return EventService.list_events(
        conn,
        category=category,
        status=status,
        department_id=department_id,
        search=search,
    )


@router.post("", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def create_event(data: EventCreate, conn: sqlite3.Connection = Depends(get_db)):
    """Host or schedule a new institutional event."""
    try:
        return EventService.create_event(conn, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/stats", response_model=EventStatsOut)
def get_event_stats(conn: sqlite3.Connection = Depends(get_db)):
    """Aggregate total events, upcoming, registrations, attendance, and certificates."""
    return EventService.get_stats(conn)


@router.get("/{id}", response_model=EventOut)
def get_event_by_id(id: int, conn: sqlite3.Connection = Depends(get_db)):
    """Retrieve details for a specific campus event."""
    event = EventService.get_event_by_id(conn, id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event #{id} not found")
    return event


@router.put("/{id}/status", response_model=EventOut)
def update_event_status(
    id: int,
    data: EventStatusUpdate,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Transition event status (UPCOMING, ACTIVE, COMPLETED, CANCELLED)."""
    try:
        return EventService.update_event_status(conn, id, data.status)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/{id}/registrations", response_model=List[EventRegistrationOut])
def list_event_registrations(
    id: int,
    status: Optional[str] = Query(None, description="REGISTERED, ATTENDED, CANCELLED"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """List attendee registrations for a specific event."""
    return EventService.list_registrations(conn, event_id=id, status=status)


@router.post("/register", response_model=EventRegistrationOut, status_code=status.HTTP_201_CREATED)
def register_student(
    data: EventRegistrationCreate,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Register a student attendee for an event."""
    try:
        return EventService.register_for_event(conn, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.put("/registrations/{id}/status", response_model=EventRegistrationOut)
def update_registration_status(
    id: int,
    data: EventRegistrationStatusUpdate,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Update registration status (ATTENDED, CANCELLED) and certificate status."""
    try:
        return EventService.update_registration_status(
            conn,
            id,
            status=data.status,
            certificate_issued=data.certificate_issued,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
