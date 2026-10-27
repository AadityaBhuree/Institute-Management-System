"""Tests for Phase 5: High-Performance Architecture, Connection Pooling, TTL Caching, and Server-Side Pagination."""

import sqlite3
import threading
import time
from datetime import date, timedelta

from src.core.cache import TTLCache, cache
from src.database.connection import SQLiteConnectionPool, get_db
from src.services.course_service import CourseService
from src.services.dashboard_service import DashboardService
from src.services.department_service import DepartmentService
from src.services.faculty_service import FacultyService
from src.services.finance_service import FinanceService
from src.services.student_service import StudentService


def test_ttl_cache_basic_operations():
    """Verify in-memory TTLCache stores, retrieves, expires, and reports telemetry."""
    test_cache = TTLCache(default_ttl_seconds=1.0)

    # Set and get
    test_cache.set("foo", "bar", ttl_seconds=0.3)
    assert test_cache.get("foo") == "bar"

    # Telemetry tracking
    stats = test_cache.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 0

    # Wait for TTL expiration
    time.sleep(0.35)
    assert test_cache.get("foo") is None
    stats_after = test_cache.stats()
    assert stats_after["misses"] == 1

    # Prefix invalidation
    test_cache.set("dept:1", "CSE")
    test_cache.set("dept:2", "ECE")
    test_cache.set("user:1", "Admin")
    del_count = test_cache.invalidate_prefix("dept:")
    assert del_count == 2
    assert test_cache.get("dept:1") is None
    assert test_cache.get("user:1") == "Admin"


def test_ttl_cache_get_or_set():
    """Verify get_or_set executes factory only on cache miss."""
    test_cache = TTLCache(default_ttl_seconds=60.0)
    calls = 0

    def compute_val():
        nonlocal calls
        calls += 1
        return "expensive_result"

    res1 = test_cache.get_or_set("computed", compute_val)
    res2 = test_cache.get_or_set("computed", compute_val)

    assert res1 == "expensive_result"
    assert res2 == "expensive_result"
    assert calls == 1  # Only executed once


def test_sqlite_connection_pool_acquire_and_reuse(tmp_path):
    """Verify SQLiteConnectionPool allocates and reuses connections up to capacity."""
    test_db = tmp_path / "pool_test.db"
    pool = SQLiteConnectionPool(max_connections_per_db=3, timeout=5.0)

    # Acquire connection 1
    conn1 = pool.acquire(test_db)
    assert isinstance(conn1, sqlite3.Connection)
    stats1 = pool.stats(test_db)
    assert stats1["allocated_connections"] == 1
    assert stats1["idle_connections"] == 0

    # Release back to pool
    pool.release(conn1, test_db)
    stats2 = pool.stats(test_db)
    assert stats2["idle_connections"] == 1

    # Acquire again -> should reuse idle connection
    conn2 = pool.acquire(test_db)
    assert conn2 is conn1
    stats3 = pool.stats(test_db)
    assert stats3["idle_connections"] == 0
    assert stats3["allocated_connections"] == 1

    pool.release(conn2, test_db)
    pool.close_all()


def test_sqlite_connection_pool_concurrent_threads(tmp_path):
    """Verify connection pool under concurrent multi-threaded contention."""
    test_db = tmp_path / "concurrent_pool.db"
    pool = SQLiteConnectionPool(max_connections_per_db=4, timeout=10.0)

    errors = []

    def worker():
        try:
            for _ in range(5):
                conn = pool.acquire(test_db)
                cursor = conn.cursor()
                cursor.execute("SELECT 1 + 1 AS sum;")
                assert cursor.fetchone()["sum"] == 2
                cursor.close()
                time.sleep(0.01)
                pool.release(conn, test_db)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    pool.close_all()


def test_sqlite_connection_pool_rollback_dirty_state(tmp_path):
    """Verify pool automatically rolls back active transactions when released."""
    test_db = tmp_path / "rollback_test.db"
    pool = SQLiteConnectionPool(max_connections_per_db=2, timeout=5.0)

    conn = pool.acquire(test_db)
    conn.execute("CREATE TABLE test (val INT);")
    conn.execute("BEGIN;")
    conn.execute("INSERT INTO test VALUES (99);")
    assert conn.in_transaction

    # Release while in transaction
    pool.release(conn, test_db)

    # Re-acquire
    conn_reused = pool.acquire(test_db)
    cursor = conn_reused.execute("SELECT COUNT(*) AS total FROM test;")
    assert cursor.fetchone()["total"] == 0  # rolled back
    pool.release(conn_reused, test_db)
    pool.close_all()


def test_department_caching_and_invalidation(client):
    """Verify DepartmentService uses in-memory TTL caching and invalidates on insert."""
    cache.clear()

    # Initial fetch populates cache
    with next(get_db()) as conn:
        depts1 = DepartmentService.list_all(conn)
        stats1 = cache.stats()
        assert stats1["active_entries"] >= 1

        # Second fetch hits cache
        depts2 = DepartmentService.list_all(conn)
        assert len(depts1) == len(depts2)
        stats2 = cache.stats()
        assert stats2["hits"] >= 1

    # Creating a department invalidates cache
    create_payload = {
        "code": "PERF",
        "name": "Performance Engineering & High Scale",
        "description": "Systems optimization",
    }
    res = client.post("/api/departments", json=create_payload)
    assert res.status_code == 201

    assert cache.get("departments:all") is None  # Cache was invalidated


def test_dashboard_kpi_query_consolidation_and_cache(client):
    """Verify DashboardService consolidation and caching behavior."""
    cache.clear()

    with next(get_db()) as conn:
        kpis1 = DashboardService.get_kpi_summary(conn)
        assert "total_students" in kpis1
        assert "total_faculty" in kpis1
        assert "total_courses" in kpis1
        assert "recovery_rate" in kpis1

        # Check cached
        cached_kpis = cache.get("dashboard:kpi_summary")
        assert cached_kpis is not None
        assert cached_kpis["total_courses"] == kpis1["total_courses"]

        # Invalidate
        DashboardService.invalidate_cache()
        assert cache.get("dashboard:kpi_summary") is None


def test_student_server_side_pagination(client):
    """Verify StudentService count_students, offset math, and pagination controls."""
    with next(get_db()) as conn:
        total = StudentService.count_students(conn)
        assert total >= 0

        # Retrieve first page
        page1 = StudentService.list_students(conn, limit=2, offset=0)
        assert len(page1) <= 2

        # Retrieve second page
        page2 = StudentService.list_students(conn, limit=2, offset=2)
        if len(page1) == 2 and total > 2:
            assert page1[0]["id"] != page2[0]["id"]

    # Web page returns pagination context and HTML controls
    res = client.get("/students?page=1&page_size=2")
    assert res.status_code == 200
    assert "Student Registry Roster" in res.text


def test_course_and_faculty_pagination_api(client):
    """Verify course and faculty API endpoints support limit and offset query params."""
    res_courses = client.get("/api/courses?limit=2&offset=0")
    assert res_courses.status_code == 200
    data_courses = res_courses.json()
    assert len(data_courses) <= 2

    res_faculty = client.get("/api/faculty?limit=2&offset=0")
    assert res_faculty.status_code == 200
    data_faculty = res_faculty.json()
    assert len(data_faculty) <= 2

    with next(get_db()) as conn:
        assert CourseService.count_courses(conn) >= 0
        assert FacultyService.count_faculty(conn) >= 0


def test_finance_invoice_pagination_and_count(client):
    """Verify FinanceService count_invoices and web view pagination."""
    with next(get_db()) as conn:
        total_inv = FinanceService.count_invoices(conn)
        assert total_inv >= 0

    res = client.get("/finance?page=1&page_size=5")
    assert res.status_code == 200
    assert "Institutional Standard Fee Schedules" in res.text


def test_overdue_invoice_throttled_sync(client):
    """Verify overdue invoices are synced without write transactions on every read."""
    with next(get_db()) as conn:
        # Create a past-due unpaid invoice
        past_date = (date.today() - timedelta(days=15)).isoformat()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM students WHERE is_deleted = 0 LIMIT 1;")
        st_row = cursor.fetchone()
        if st_row:
            issued_date = (date.today() - timedelta(days=30)).isoformat()
            cursor.execute(
                """
                INSERT INTO fee_invoices (invoice_no, student_id, title, term_name, total_amount, paid_amount, balance_amount, status, issued_date, due_date)
                VALUES ('TEST-OVERDUE-01', ?, 'Overdue Test', 'Fall 2026', 1000.0, 0.0, 1000.0, 'UNPAID', ?, ?);
                """,
                (st_row["id"], issued_date, past_date),
            )
            conn.commit()

            # Trigger explicit sync
            updated = FinanceService.sync_overdue_invoices(conn)
            assert updated >= 1

            # Verify invoice is now OVERDUE
            cursor.execute("SELECT status FROM fee_invoices WHERE invoice_no = 'TEST-OVERDUE-01';")
            assert cursor.fetchone()["status"] == "OVERDUE"

            # Immediate second call should be throttled (returns 0)
            throttled = FinanceService.sync_overdue_invoices_if_needed(
                conn, min_interval_seconds=3600.0
            )
            assert throttled == 0

        cursor.close()


def test_composite_indexes_present_in_database(client):
    """Verify all 4 new Phase 5 composite performance indexes are created in SQLite."""
    with next(get_db()) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index';")
        indexes = {r["name"] for r in cursor.fetchall()}
        cursor.close()

        assert "idx_attendance_student_course" in indexes
        assert "idx_invoices_status_due" in indexes
        assert "idx_students_deleted_dept" in indexes
        assert "idx_courses_dept_sem" in indexes


def test_system_telemetry_includes_pool_and_cache(client):
    """Verify /api/system/telemetry reports connection_pool and cache health stats."""
    res = client.get("/api/system/telemetry")
    assert res.status_code == 200
    data = res.json()

    assert "connection_pool" in data
    assert "allocated_connections" in data["connection_pool"]
    assert "cache" in data
    assert "hits" in data["cache"]
    assert "misses" in data["cache"]
