"""Pydantic Models for High-Performance SQLite FTS5 Omnisearch."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class SearchResultItem(BaseModel):
    """Unified search result entry across institutional domains."""

    id: int = Field(..., description="Unique entity database identifier")
    category: str = Field(..., description="Domain category: STUDENT, FACULTY, COURSE, BOOK, ANNOUNCEMENT")
    title: str = Field(..., description="Primary headline or name")
    subtitle: Optional[str] = Field(default=None, description="Contextual subtitle, code, or secondary detail")
    snippet: Optional[str] = Field(default=None, description="BM25 search match excerpt with highlight markers")
    url: str = Field(..., description="Navigation route or direct portal resource URL")


class SearchResponse(BaseModel):
    """Unified global omnisearch response envelope."""

    query: str = Field(..., description="Cleaned and executed search query string")
    total: int = Field(..., description="Aggregate total matching items across queried categories")
    categories: Dict[str, int] = Field(default_factory=dict, description="Counts breakdown by category")
    results: List[SearchResultItem] = Field(default_factory=list, description="Ranked list of matching records")
