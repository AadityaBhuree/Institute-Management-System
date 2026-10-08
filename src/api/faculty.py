"""Faculty API Endpoints."""

import sqlite3
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.database.connection import get_db
from src.models.faculty import FacultyCreate, FacultyOut, FacultyUpdate
from src.services.faculty_service import FacultyService

router = APIRouter(prefix="/api/faculty", tags=["Faculty"])


@router.get("", response_model=List[FacultyOut])
def list_faculty(
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search faculty by name or ID"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve faculty members roster."""
    return FacultyService.list_faculty(
        conn,
        department_id=department_id,
        status=status,
        search=search,
    )


@router.post("", response_model=FacultyOut, status_code=status.HTTP_201_CREATED)
def create_faculty(
    faculty_in: FacultyCreate,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Register a new faculty member."""
    try:
        return FacultyService.create(conn, faculty_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/{faculty_id}", response_model=FacultyOut)
def get_faculty_member(
    faculty_id: int,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve details for a single faculty member."""
    member = FacultyService.get_by_id(conn, faculty_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Faculty member ID {faculty_id} not found.",
        )
    return member


@router.put("/{faculty_id}", response_model=FacultyOut)
def update_faculty(
    faculty_id: int,
    faculty_up: FacultyUpdate,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Update faculty member profile or status."""
    updated = FacultyService.update(conn, faculty_id, faculty_up)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Faculty member ID {faculty_id} not found.",
        )
    return updated


@router.delete("/{faculty_id}")
def delete_faculty(
    faculty_id: int,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Delete a faculty member."""
    success = FacultyService.delete(conn, faculty_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Faculty member ID {faculty_id} not found.",
        )
    return {"message": "Faculty member removed from directory.", "id": faculty_id}


@router.get("/{faculty_id}/portal-data")
def get_faculty_portal_data(
    faculty_id: int,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve full workbench dossier for a faculty instructor."""
    data = FacultyService.get_faculty_portal_data(conn, faculty_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Faculty member ID {faculty_id} not found.",
        )
    return data

