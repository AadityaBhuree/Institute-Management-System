"""High-Performance SQLite FTS5 Full-Text Omnisearch REST API Router."""

import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from src.core.security import get_current_user
from src.database.connection import get_db
from src.models.search import SearchResponse
from src.services.search_service import SearchService

router = APIRouter(tags=["Omnisearch"])


@router.get(
    "/api/search",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
)
def global_search(
    q: str = Query(..., min_length=1, max_length=100, description="Search query string"),
    category: Optional[str] = Query(
        None,
        description="Filter domain category: STUDENT, FACULTY, COURSE, BOOK, ANNOUNCEMENT",
    ),
    limit: int = Query(20, ge=1, le=100, description="Max search results"),
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Execute sub-millisecond global institutional full-text omnisearch with BM25 ranking."""
    user_role = current_user.get("role", "student")
    return SearchService.global_search(
        conn=conn,
        query=q,
        category=category,
        limit=limit,
        user_role=user_role,
    )
