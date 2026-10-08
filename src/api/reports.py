"""Institutional Reports & Analytics API Router."""

import sqlite3
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from src.database.connection import get_db
from src.services.reports_service import ReportsService

router = APIRouter(prefix="/api/reports", tags=["Reports & Analytics"])


@router.get("/analytics-summary")
def get_analytics_summary(
    department_id: Optional[int] = Query(None, description="Filter analytics by department ID"),
    conn: sqlite3.Connection = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve full institutional telemetry, attendance risk sentinel, and financial recovery metrics."""
    return ReportsService.get_analytics_summary(conn, department_id=department_id)
