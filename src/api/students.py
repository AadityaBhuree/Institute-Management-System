"""Student Admissions & Registry API Endpoints."""

import sqlite3
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.database.connection import get_db
from src.models.student import StudentCreate, StudentOut, StudentUpdate
from src.services.student_service import StudentService

router = APIRouter(prefix="/api/students", tags=["Students & Admissions"])


@router.get("", response_model=List[StudentOut])
def list_students(
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    status: Optional[str] = Query(None, description="Filter by enrollment status"),
    search: Optional[str] = Query(None, description="Search by name, email, or enrollment no"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    conn: sqlite3.Connection = Depends(get_db),
):
    """List students with dynamic filtering, search, and pagination."""
    return StudentService.list_students(
        conn,
        department_id=department_id,
        status=status,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
def create_student(
    student_in: StudentCreate,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Enroll a new student and generate a unique institutional enrollment number."""
    try:
        created = StudentService.create(conn, student_in)
        return created
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/stats/summary")
def get_students_summary(conn: sqlite3.Connection = Depends(get_db)):
    """Retrieve student status count breakdown."""
    return StudentService.get_stats(conn)


@router.get("/{student_id}", response_model=StudentOut)
def get_student(
    student_id: int,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve full demographic and registry profile of a student."""
    student = StudentService.get_by_id(conn, student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID {student_id} not found.",
        )
    return student


@router.put("/{student_id}", response_model=StudentOut)
def update_student(
    student_id: int,
    student_up: StudentUpdate,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Update student profile, semester, or enrollment status."""
    updated = StudentService.update(conn, student_id, student_up)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID {student_id} not found.",
        )
    return updated


@router.delete("/{student_id}")
def delete_student(
    student_id: int,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Remove a student registry record."""
    success = StudentService.delete(conn, student_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID {student_id} not found.",
        )
    return {"message": "Student record successfully purged from registry.", "id": student_id}


@router.get("/{student_id}/portal-dossier")
def get_student_portal_dossier(
    student_id: int,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve comprehensive academic, attendance, and fee dossier for scholar portal."""
    dossier = StudentService.get_student_portal_dossier(conn, student_id)
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID {student_id} not found.",
        )
    return dossier

