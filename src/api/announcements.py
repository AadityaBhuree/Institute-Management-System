"""Campus Announcements API Router."""

import sqlite3
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.database.connection import get_db
from src.models.announcement import AnnouncementCreate, AnnouncementOut
from src.services.announcement_service import AnnouncementService

router = APIRouter(prefix="/api/announcements", tags=["Announcements"])


@router.get("", response_model=List[AnnouncementOut])
def list_announcements(
    category: Optional[str] = Query(None, description="Filter by category (ACADEMIC, EXAM, FEES, EVENT, URGENT, GENERAL)"),
    target_audience: Optional[str] = Query(None, description="Filter by target audience (ALL, STUDENTS, FACULTY)"),
    is_active: Optional[int] = Query(None, description="Filter by active status (1 or 0)"),
    search: Optional[str] = Query(None, description="Search term for title/content"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve campus bulletins and announcements matching filters."""
    return AnnouncementService.list_announcements(
        conn,
        category=category,
        target_audience=target_audience,
        is_active=is_active,
        search=search,
    )


@router.get("/{id}", response_model=AnnouncementOut)
def get_announcement(id: int, conn: sqlite3.Connection = Depends(get_db)):
    """Retrieve single announcement by ID."""
    item = AnnouncementService.get_by_id(conn, id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Announcement #{id} not found",
        )
    return item


@router.post("", response_model=AnnouncementOut, status_code=status.HTTP_201_CREATED)
def create_announcement(
    data: AnnouncementCreate,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Post an institutional announcement or campus notice."""
    try:
        return AnnouncementService.create(conn, data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.put("/{id}/toggle-active", response_model=AnnouncementOut)
def toggle_announcement_active(
    id: int,
    is_active: int = Query(..., ge=0, le=1),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Toggle announcement published state."""
    item = AnnouncementService.toggle_active(conn, id, is_active)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Announcement #{id} not found",
        )
    return item


@router.delete("/{id}", status_code=status.HTTP_200_OK)
def delete_announcement(id: int, conn: sqlite3.Connection = Depends(get_db)):
    """Remove an announcement notice."""
    deleted = AnnouncementService.delete(conn, id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Announcement #{id} not found",
        )
    return {"message": f"Announcement #{id} deleted successfully"}
