"""Attendance & Examination Management API Endpoints."""

import sqlite3
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.database.connection import get_db
from src.models.academics import AttendanceBatchMark, ExamCreate, ExamGradeBatchSubmit, ExamOut
from src.services.academics_service import AcademicsService

router = APIRouter(prefix="/api/academics", tags=["Attendance & Examinations"])


@router.post("/attendance/mark", status_code=status.HTTP_201_CREATED)
def mark_attendance(
    batch_in: AttendanceBatchMark,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Bulk record or update student attendance for a course session."""
    try:
        return AcademicsService.mark_attendance_batch(conn, batch_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/attendance")
def get_attendance(
    course_id: int = Query(..., description="Course ID"),
    attendance_date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    student_id: Optional[int] = Query(None, description="Student ID filter"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve session attendance roster."""
    return AcademicsService.get_attendance_records(
        conn,
        course_id=course_id,
        attendance_date=attendance_date,
        student_id=student_id,
    )


@router.get("/attendance/student/{student_id}/summary")
def get_student_attendance(
    student_id: int,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve student attendance percentage and low-attendance alert."""
    return AcademicsService.get_student_attendance_summary(conn, student_id)


@router.post("/exams", response_model=ExamOut, status_code=status.HTTP_201_CREATED)
def create_exam(
    exam_in: ExamCreate,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Schedule an examination or academic evaluation."""
    try:
        return AcademicsService.create_examination(conn, exam_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/exams", response_model=List[ExamOut])
def list_exams(
    course_id: Optional[int] = Query(None, description="Filter by course ID"),
    exam_type: Optional[str] = Query(None, description="Filter by exam type"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve scheduled examinations and grading status."""
    return AcademicsService.list_examinations(conn, course_id=course_id, exam_type=exam_type)


@router.get("/exams/{exam_id}", response_model=ExamOut)
def get_exam(
    exam_id: int,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve examination specification."""
    exam = AcademicsService.get_exam_by_id(conn, exam_id)
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam ID {exam_id} not found.",
        )
    return exam


@router.post("/exams/{exam_id}/grades")
def submit_grades(
    exam_id: int,
    grade_in: ExamGradeBatchSubmit,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Submit candidate evaluation marks with automated letter grade calculation."""
    try:
        return AcademicsService.submit_exam_grades_batch(conn, exam_id, grade_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/exams/{exam_id}/results")
def get_exam_results_dossier(
    exam_id: int,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve examination grade roster and statistical analytics."""
    results = AcademicsService.get_exam_results(conn, exam_id)
    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam ID {exam_id} not found.",
        )
    return results
