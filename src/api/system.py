"""System health diagnostics, telemetry, and hot backup snapshot API router."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from src.core.config import APP_NAME, APP_VERSION
from src.core.security import require_role
from src.database.connection import get_db
from src.services.auth_service import AuthService
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
def create_system_backup(
    conn: sqlite3.Connection = Depends(get_db),
    admin_user: dict = Depends(require_role("admin")),
):
    """Perform hot online SQLite database backup snapshot (Admin only)."""
    result = SystemService.create_backup(conn)
    AuthService.log_audit(
        conn,
        action="SYSTEM_BACKUP",
        resource="system",
        resource_id=result.get("filename"),
        user_id=admin_user.get("id"),
        username=admin_user.get("username"),
        details=f"Database snapshot generated: {result.get('filename')} ({result.get('size_kb')} KB)",
    )
    return result


@router.get("/api/system/backups")
def list_system_backups(
    admin_user: dict = Depends(require_role("admin")),
):
    """List all available database snapshots in data/backups/ (Admin only)."""
    return SystemService.list_backups()


@router.post("/api/system/restore")
def restore_system_backup(
    payload: dict,
    conn: sqlite3.Connection = Depends(get_db),
    admin_user: dict = Depends(require_role("admin")),
):
    """Restore active database state from a point-in-time snapshot (Admin only)."""
    filename = payload.get("filename")
    if not filename:
        raise HTTPException(status_code=400, detail="Missing required 'filename' field.")
    try:
        result = SystemService.restore_backup(conn, filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    AuthService.log_audit(
        conn,
        action="SYSTEM_RESTORE",
        resource="system",
        resource_id=filename,
        user_id=admin_user.get("id"),
        username=admin_user.get("username"),
        details=f"Database state restored from snapshot: {filename}",
    )
    return result


@router.get("/api/system/migrations")
def get_migration_status(
    conn: sqlite3.Connection = Depends(get_db),
    admin_user: dict = Depends(require_role("admin")),
):
    """Retrieve schema migration history and pending migrations (Admin only)."""
    from src.database.migration_manager import MigrationManager

    return MigrationManager.get_status(conn)


@router.post("/api/system/migrate")
def run_migrations(
    conn: sqlite3.Connection = Depends(get_db),
    admin_user: dict = Depends(require_role("admin")),
):
    """Execute all pending schema migrations (Admin only)."""
    from src.database.migration_manager import MigrationManager

    results = MigrationManager.run_pending_migrations(conn)
    AuthService.log_audit(
        conn,
        action="SCHEMA_MIGRATION",
        resource="database",
        resource_id=str(len(results)),
        user_id=admin_user.get("id"),
        username=admin_user.get("username"),
        details=f"Executed {len(results)} pending schema migrations.",
    )
    return {"applied": results, "total_applied": len(results)}
