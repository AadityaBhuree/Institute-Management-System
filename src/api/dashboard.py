"""Executive dashboard and KPI metrics API router."""

import sqlite3

from fastapi import APIRouter, Depends

from src.database.connection import get_db
from src.services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats")
def get_dashboard_stats(conn: sqlite3.Connection = Depends(get_db)):
    """Retrieve real-time KPI metrics and administrative summary."""
    return DashboardService.get_kpi_summary(conn)
