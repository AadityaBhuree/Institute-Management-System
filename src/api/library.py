"""Campus Library & Resource Circulation API Router."""

import sqlite3
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.database.connection import get_db
from src.models.library import (
    BookIssueRequest,
    BookLoanOut,
    BookReturnRequest,
    LibraryBookCreate,
    LibraryBookOut,
    LibraryStatsOut,
)
from src.services.library_service import LibraryService

router = APIRouter(prefix="/api/library", tags=["Library Management"])


@router.get("/books", response_model=List[LibraryBookOut])
def list_books(
    category: Optional[str] = Query(None, description="Category filter"),
    search: Optional[str] = Query(None, description="Search by title, author, or ISBN"),
    available_only: bool = Query(False, description="Filter only books with available copies > 0"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve library books catalog."""
    return LibraryService.list_books(
        conn, category=category, search=search, available_only=available_only
    )


@router.get("/books/{id}", response_model=LibraryBookOut)
def get_book(id: int, conn: sqlite3.Connection = Depends(get_db)):
    """Retrieve book catalog record by ID."""
    book = LibraryService.get_book_by_id(conn, id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Library book #{id} not found",
        )
    return book


@router.post("/books", response_model=LibraryBookOut, status_code=status.HTTP_201_CREATED)
def create_book(data: LibraryBookCreate, conn: sqlite3.Connection = Depends(get_db)):
    """Add a new book accession to library catalog."""
    try:
        return LibraryService.create_book(conn, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/loans", response_model=List[BookLoanOut])
def list_loans(
    status_filter: Optional[str] = Query(
        None, alias="status", description="ISSUED, RETURNED, OVERDUE"
    ),
    student_id: Optional[int] = Query(None, description="Filter loans by student ID"),
    book_id: Optional[int] = Query(None, description="Filter loans by book ID"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve active or historic book loans with metadata."""
    return LibraryService.list_loans(
        conn, status=status_filter, student_id=student_id, book_id=book_id
    )


@router.post("/issue", response_model=BookLoanOut, status_code=status.HTTP_201_CREATED)
def issue_book(data: BookIssueRequest, conn: sqlite3.Connection = Depends(get_db)):
    """Issue a book copy to a student."""
    try:
        return LibraryService.issue_book(conn, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/return/{loan_id}", response_model=BookLoanOut)
def return_book(
    loan_id: int,
    data: BookReturnRequest,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Return a borrowed book copy and process fine assessment."""
    try:
        return LibraryService.return_book(conn, loan_id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/stats", response_model=LibraryStatsOut)
def get_library_stats(conn: sqlite3.Connection = Depends(get_db)):
    """Retrieve high-level circulation statistics."""
    return LibraryService.get_stats(conn)
