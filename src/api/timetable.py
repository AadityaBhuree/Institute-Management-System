"""Academic Timetable and Lecture Scheduling API Router."""

import sqlite3
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.core.security import require_role
from src.database.connection import get_db
from src.models.timetable import TimetableSlotCreate, TimetableSlotOut
from src.services.auth_service import AuthService
from src.services.timetable_service import TimetableService

router = APIRouter(prefix="/api/timetable", tags=["Academic Timetable"])


@router.get("", response_model=List[TimetableSlotOut])
def list_timetable_slots(
    day_of_week: Optional[str] = Query(None, description="Monday, Tuesday, etc."),
    course_id: Optional[int] = Query(None, description="Filter by Course ID"),
    room_number: Optional[str] = Query(None, description="Filter by lecture room"),
    department_id: Optional[int] = Query(None, description="Filter by academic department"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve scheduled lecture timetable slots."""
    return TimetableService.list_slots(
        conn,
        day_of_week=day_of_week,
        course_id=course_id,
        room_number=room_number,
        department_id=department_id,
    )


@router.get("/matrix")
def get_weekly_timetable_matrix(
    department_id: Optional[int] = Query(None, description="Filter by academic department"),
    conn: sqlite3.Connection = Depends(get_db),
) -> Dict[str, List[dict]]:
    """Retrieve complete weekly schedule matrix organized by days (Monday through Saturday)."""
    return TimetableService.get_weekly_matrix(conn, department_id=department_id)


@router.get("/{id}", response_model=TimetableSlotOut)
def get_timetable_slot(id: int, conn: sqlite3.Connection = Depends(get_db)):
    """Retrieve single timetable slot by ID."""
    slot = TimetableService.get_by_id(conn, id)
    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Timetable slot #{id} not found",
        )
    return slot


@router.post("", response_model=TimetableSlotOut, status_code=status.HTTP_201_CREATED)
def create_timetable_slot(
    data: TimetableSlotCreate,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Schedule lecture slot with room and instructor collision avoidance."""
    try:
        return TimetableService.create_slot(conn, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.delete("/{id}", status_code=status.HTTP_200_OK)
def delete_timetable_slot(
    id: int,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    """Remove a lecture timetable slot (Admin only)."""
    deleted = TimetableService.delete_slot(conn, id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Timetable slot #{id} not found",
        )
    AuthService.log_audit(
        conn,
        action="DELETE_TIMETABLE_SLOT",
        resource="timetable",
        resource_id=str(id),
        user_id=current_user.get("id"),
        username=current_user.get("username"),
        details=f"Deleted lecture slot #{id}.",
    )
    return {"message": f"Timetable slot #{id} deleted successfully"}
