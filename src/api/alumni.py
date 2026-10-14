"""Alumni Network & Career Mentorship Hub API Router."""

import sqlite3
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.database.connection import get_db
from src.models.alumni import (
    AlumniMemberCreate,
    AlumniMemberOut,
    AlumniMentorshipRequestCreate,
    AlumniMentorshipRequestOut,
    AlumniMentorshipStatusUpdate,
    AlumniStatsOut,
)
from src.services.alumni_service import AlumniService

router = APIRouter(prefix="/api/alumni", tags=["Alumni Network & Mentorship"])


@router.get("/members", response_model=List[AlumniMemberOut])
def list_alumni(
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    graduation_year: Optional[int] = Query(None, description="Filter by graduation batch year"),
    mentorship_status: Optional[str] = Query(None, description="AVAILABLE, BUSY, INACTIVE"),
    search: Optional[str] = Query(None, description="Search name, company, role, or city"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """List registered alumni members and professional directory."""
    return AlumniService.list_alumni(
        conn,
        department_id=department_id,
        graduation_year=graduation_year,
        mentorship_status=mentorship_status,
        search=search,
    )


@router.post("/members", response_model=AlumniMemberOut, status_code=status.HTTP_201_CREATED)
def register_alumnus(data: AlumniMemberCreate, conn: sqlite3.Connection = Depends(get_db)):
    """Enroll a graduate in the alumni network directory."""
    try:
        return AlumniService.register_alumnus(conn, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/mentorship-requests", response_model=List[AlumniMentorshipRequestOut])
def list_mentorship_requests(
    alumni_id: Optional[int] = Query(None, description="Filter by mentor alumni ID"),
    student_id: Optional[int] = Query(None, description="Filter by mentee student ID"),
    status: Optional[str] = Query(None, description="REQUESTED, ACCEPTED, COMPLETED, DECLINED"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """List alumni mentorship connections and status."""
    return AlumniService.list_mentorship_requests(
        conn, alumni_id=alumni_id, student_id=student_id, status=status
    )


@router.post(
    "/mentorship-requests",
    response_model=AlumniMentorshipRequestOut,
    status_code=status.HTTP_201_CREATED,
)
def request_mentorship(
    data: AlumniMentorshipRequestCreate, conn: sqlite3.Connection = Depends(get_db)
):
    """Submit a career mentorship request to an alumnus."""
    try:
        return AlumniService.request_mentorship(conn, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.put("/mentorship-requests/{id}/status", response_model=AlumniMentorshipRequestOut)
def update_mentorship_status(
    id: int,
    data: AlumniMentorshipStatusUpdate,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Accept, complete, or decline a student mentorship request."""
    try:
        return AlumniService.update_mentorship_status(conn, id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/stats", response_model=AlumniStatsOut)
def get_alumni_stats(conn: sqlite3.Connection = Depends(get_db)):
    """Aggregate total alumni, active mentors, and mentorship connections."""
    return AlumniService.get_stats(conn)
