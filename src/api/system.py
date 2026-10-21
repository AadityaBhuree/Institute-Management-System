"""System health diagnostics, telemetry, and hot backup snapshot API router."""

import sqlite3

from fastapi import APIRouter, Depends

from src.core.config import APP_NAME, APP_VERSION
from src.database.connection import get_db
from src.services.system_service import SystemService

router = APIRouter(tags=["System"])


@router.get("/api/health")
def health_check(conn: sqlite3.Connection = Depends(get_db)) -> dict:
    """System health check and database connectivity verification."""
    cursor = conn.cursor()
    cursor.execute("SELECT 1 AS ok;")
    result = cursor.fetchone()["ok"]
    cursor.close()
    return {
        "status": "healthy",
        "app": APP_NAME,
        "version": APP_VERSION,
        "database": "connected" if result == 1 else "unhealthy",
    }


@router.get("/api/system/telemetry")
def get_system_telemetry(conn: sqlite3.Connection = Depends(get_db)):
    """Retrieve system diagnostics, database size, and table telemetry."""
    return SystemService.get_system_telemetry(conn)


@router.post("/api/system/backup")
def create_system_backup(conn: sqlite3.Connection = Depends(get_db)):
    """Perform hot online SQLite database backup snapshot."""
    return SystemService.create_backup(conn)


@router.get("/api/system/backups")
def list_system_backups():
    """List all available database snapshots in data/backups/."""
    return SystemService.list_backups()
