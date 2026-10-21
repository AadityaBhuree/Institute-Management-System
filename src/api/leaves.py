"""Institutional Leave Management API Router."""

import sqlite3
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.database.connection import get_db
from src.models.leave import LeaveRequestCreate, LeaveRequestOut, LeaveStatusUpdate
from src.services.leave_service import LeaveService

router = APIRouter(prefix="/api/leaves", tags=["Leave Management"])


@router.get("", response_model=List[LeaveRequestOut])
def list_leaves(
    applicant_type: Optional[str] = Query(None, description="STUDENT or FACULTY"),
    status: Optional[str] = Query(None, description="PENDING, APPROVED, or REJECTED"),
    applicant_id: Optional[int] = Query(None, description="Filter by applicant student/faculty ID"),
    search: Optional[str] = Query(None, description="Search applicant name or reason"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve institutional leave requests matching filters."""
    return LeaveService.list_leaves(
        conn,
        applicant_type=applicant_type,
        status=status,
        applicant_id=applicant_id,
        search=search,
    )


@router.get("/stats/summary")
def get_leave_stats(conn: sqlite3.Connection = Depends(get_db)) -> Dict[str, int]:
    """Retrieve aggregate statistics on pending, approved, and rejected leaves."""
    return LeaveService.get_leave_stats(conn)


@router.get("/{id}", response_model=LeaveRequestOut)
def get_leave(id: int, conn: sqlite3.Connection = Depends(get_db)):
    """Retrieve single leave request dossier."""
    item = LeaveService.get_by_id(conn, id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Leave application #{id} not found",
        )
    return item


@router.post("", response_model=LeaveRequestOut, status_code=status.HTTP_201_CREATED)
def submit_leave(data: LeaveRequestCreate, conn: sqlite3.Connection = Depends(get_db)):
    """Submit a student or faculty absence request."""
    try:
        return LeaveService.submit_leave(conn, data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.put("/{id}/status", response_model=LeaveRequestOut)
def update_leave_status(
    id: int,
    data: LeaveStatusUpdate,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Review and update leave request decision (APPROVED or REJECTED)."""
    item = LeaveService.update_status(conn, id, data)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Leave application #{id} not found",
        )
    return item
