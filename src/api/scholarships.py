"""Scholarships, Grants & Financial Aid API Router."""

import sqlite3
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.database.connection import get_db
from src.models.scholarship import (
    ScholarshipApplicationCreate,
    ScholarshipApplicationOut,
    ScholarshipReviewUpdate,
    ScholarshipSchemeCreate,
    ScholarshipSchemeOut,
    ScholarshipStatsOut,
)
from src.services.scholarship_service import ScholarshipService

router = APIRouter(prefix="/api/scholarships", tags=["Scholarships & Financial Aid"])


@router.get("/schemes", response_model=List[ScholarshipSchemeOut])
def list_schemes(
    status: Optional[str] = Query(None, description="ACTIVE, CLOSED"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """List scholarship schemes with applicant counts."""
    return ScholarshipService.list_schemes(conn, status=status)


@router.post("/schemes", response_model=ScholarshipSchemeOut, status_code=status.HTTP_201_CREATED)
def create_scheme(data: ScholarshipSchemeCreate, conn: sqlite3.Connection = Depends(get_db)):
    """Define a new institutional or sponsored scholarship scheme."""
    try:
        return ScholarshipService.create_scheme(conn, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/applications", response_model=List[ScholarshipApplicationOut])
def list_applications(
    scheme_id: Optional[int] = Query(None, description="Filter by scheme ID"),
    student_id: Optional[int] = Query(None, description="Filter by candidate student ID"),
    status: Optional[str] = Query(None, description="PENDING, APPROVED, DISBURSED, REJECTED"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """List scholar financial aid and scholarship applications."""
    return ScholarshipService.list_applications(
        conn, scheme_id=scheme_id, student_id=student_id, status=status
    )


@router.post(
    "/apply", response_model=ScholarshipApplicationOut, status_code=status.HTTP_201_CREATED
)
def apply_for_scholarship(
    data: ScholarshipApplicationCreate, conn: sqlite3.Connection = Depends(get_db)
):
    """Submit a scholarship grant application with academic and income gating."""
    try:
        return ScholarshipService.apply_for_scholarship(conn, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.put("/applications/{id}/review", response_model=ScholarshipApplicationOut)
def review_application(
    id: int,
    data: ScholarshipReviewUpdate,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Review, approve, or disburse scholarship grant award."""
    try:
        return ScholarshipService.review_application(conn, id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/stats", response_model=ScholarshipStatsOut)
def get_scholarship_stats(conn: sqlite3.Connection = Depends(get_db)):
    """Retrieve financial aid allocations, award recipients, and fund totals."""
    return ScholarshipService.get_stats(conn)
