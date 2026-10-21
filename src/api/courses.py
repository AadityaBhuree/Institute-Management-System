"""Courses and Enrollments API Endpoints."""

import sqlite3
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.database.connection import get_db
from src.models.course import CourseCreate, CourseOut, CourseUpdate, EnrollmentCreate
from src.services.course_service import CourseService

router = APIRouter(prefix="/api/courses", tags=["Courses & Curriculum"])


@router.get("", response_model=List[CourseOut])
def list_courses(
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    semester: Optional[int] = Query(None, description="Filter by semester (1-8)"),
    search: Optional[str] = Query(None, description="Search course by code or title"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve course catalog units with occupancy indicators."""
    return CourseService.list_courses(
        conn,
        department_id=department_id,
        semester=semester,
        search=search,
    )


@router.post("", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
def create_course(
    course_in: CourseCreate,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Create a new course catalog unit."""
    try:
        return CourseService.create(conn, course_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/{course_id}", response_model=CourseOut)
def get_course(
    course_id: int,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve detailed unit syllabus and instructor assignment."""
    course = CourseService.get_by_id(conn, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID {course_id} not found.",
        )
    return course


@router.put("/{course_id}", response_model=CourseOut)
def update_course(
    course_id: int,
    course_up: CourseUpdate,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Update course attributes or capacity."""
    updated = CourseService.update(conn, course_id, course_up)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID {course_id} not found.",
        )
    return updated


@router.post("/{course_id}/assign-instructor", response_model=CourseOut)
def assign_instructor(
    course_id: int,
    instructor_id: Optional[int] = Query(None, description="Faculty ID or null to unassign"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Assign an instructional faculty member to lead a course."""
    try:
        return CourseService.assign_instructor(conn, course_id, instructor_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/enroll", status_code=status.HTTP_201_CREATED)
def enroll_student(
    enrollment_in: EnrollmentCreate,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Enroll a registered student into a course subject to capacity limits."""
    try:
        return CourseService.enroll_student(conn, enrollment_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/{course_id}/students")
def list_enrolled_students(
    course_id: int,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve active student roster for a course."""
    return CourseService.list_course_students(conn, course_id)


@router.delete("/{course_id}")
def delete_course(
    course_id: int,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Delete a course catalog unit."""
    success = CourseService.delete(conn, course_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID {course_id} not found.",
        )
    return {"message": "Course unit deleted successfully.", "id": course_id}
