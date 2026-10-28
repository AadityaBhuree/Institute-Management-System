"""Concurrency and Transaction Rollback Test Suite.
Verifies:
- Thread-safe unique enrollment number generation under high concurrency
- Multi-threaded connection pool acquire/release stress resilience
- Transaction context manager rollback on application exceptions
- Transaction context manager rollback on SQLite integrity constraint violations
"""

import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from src.database.connection import get_connection, release_connection, transaction
from src.models.student import StudentCreate
from src.services.student_service import StudentService


def test_concurrent_student_enrollments(setup_test_db):
    """Verify concurrent student enrollments across multiple threads produce strictly unique enrollment numbers."""
    from src.database.connection import pool

    worker_count = 6
    total_students = 12

    def enroll_worker(idx: int) -> str:
        conn = pool.acquire(setup_test_db)
        try:
            student_in = StudentCreate(
                first_name=f"Concurrent{idx}",
                last_name="Worker",
                email=f"concurrent.worker.{idx}@example.edu",
                department_id=1,
                current_semester=1,
                admission_date="2026-08-01",
            )
            created = StudentService.create(conn, student_in)
            return created["enrollment_no"]
        finally:
            pool.release(conn, setup_test_db)

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [executor.submit(enroll_worker, i) for i in range(total_students)]
        enrollment_numbers = [f.result() for f in as_completed(futures)]

    # All generated enrollment numbers must be strictly unique
    assert len(enrollment_numbers) == total_students
    assert len(set(enrollment_numbers)) == total_students, (
        "Collisions detected in concurrent enrollment generation!"
    )


def test_transaction_rollback_on_application_exception(setup_test_db):
    """Verify transaction context manager automatically rolls back all changes when an exception is raised."""
    conn = get_connection(setup_test_db)
    test_title = "ROLLBACK_TEST_ANNOUNCEMENT"
    try:
        # Pre-condition: title should not exist
        cur = conn.cursor()
        cur.execute("SELECT id FROM announcements WHERE title = ?;", (test_title,))
        assert cur.fetchone() is None
        cur.close()

        # Execute transaction block that raises an intentional exception
        with pytest.raises(RuntimeError, match="Simulated application failure during transaction"):
            with transaction(conn) as tx_cur:
                tx_cur.execute(
                    """
                    INSERT INTO announcements (title, content, category, priority, author_name)
                    VALUES (?, 'This content should be rolled back.', 'GENERAL', 'LOW', 'Registrar Desk');
                    """,
                    (test_title,),
                )
                # Verify row was staged inside transaction
                assert tx_cur.rowcount == 1
                raise RuntimeError("Simulated application failure during transaction")

        # Post-condition: row must NOT exist in database after rollback
        cur = conn.cursor()
        cur.execute("SELECT id FROM announcements WHERE title = ?;", (test_title,))
        assert cur.fetchone() is None, "Row was not rolled back after application exception!"
        cur.close()

        # Connection should not be trapped in an active transaction
        assert not conn.in_transaction
    finally:
        release_connection(conn, setup_test_db)


def test_transaction_rollback_on_integrity_violation(setup_test_db):
    """Verify multi-statement transaction rolls back preceding statements if a subsequent statement fails."""
    conn = get_connection(setup_test_db)
    first_title = "VALID_ANNOUNCEMENT_PART1"
    try:
        # Pre-condition check
        cur = conn.cursor()
        cur.execute("SELECT id FROM announcements WHERE title = ?;", (first_title,))
        assert cur.fetchone() is None
        cur.close()

        # Attempt transaction where statement 1 succeeds, but statement 2 violates FK or NOT NULL
        with pytest.raises(sqlite3.IntegrityError):
            with transaction(conn) as tx_cur:
                # Statement 1 (valid insert)
                tx_cur.execute(
                    """
                    INSERT INTO announcements (title, content, category, priority, author_name)
                    VALUES (?, 'Valid first step of multi-operation', 'GENERAL', 'NORMAL', 'Academic Affairs');
                    """,
                    (first_title,),
                )

                # Statement 2 (violates NOT NULL on title)
                tx_cur.execute(
                    """
                    INSERT INTO announcements (title, content, category, priority, author_name)
                    VALUES (NULL, 'Missing required title', 'GENERAL', 'HIGH', 'Test');
                    """
                )

        # Verification: First statement must have been rolled back
        cur = conn.cursor()
        cur.execute("SELECT id FROM announcements WHERE title = ?;", (first_title,))
        assert cur.fetchone() is None, (
            "First statement was committed despite second statement failing!"
        )
        cur.close()
        assert not conn.in_transaction
    finally:
        release_connection(conn, setup_test_db)


def test_connection_pool_concurrent_stress(setup_test_db):
    """Verify connection pool handles high concurrent worker contention without deadlocks or resource leaks."""
    from src.database.connection import pool

    thread_count = 10
    iterations_per_thread = 8

    def pool_worker(worker_id: int):
        for it in range(iterations_per_thread):
            c = pool.acquire(setup_test_db)
            try:
                cur = c.cursor()
                cur.execute("SELECT 1 AS ping, ? AS worker, ? AS iteration;", (worker_id, it))
                row = cur.fetchone()
                assert row["ping"] == 1
                assert row["worker"] == worker_id
                cur.close()
            finally:
                pool.release(c, setup_test_db)

    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        futures = [executor.submit(pool_worker, i) for i in range(thread_count)]
        for f in as_completed(futures):
            f.result()  # Will raise if any thread encountered an exception

    # Verify pool stats remain healthy
    stats = pool.stats(setup_test_db)
    assert stats["allocated_connections"] <= stats["max_connections"]
    assert stats["busy_connections"] == 0
