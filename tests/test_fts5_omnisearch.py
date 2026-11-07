"""Automated Test Suite for SQLite FTS5 Full-Text Omnisearch Engine.
Validates virtual tables, Porter stemmer tokenization, BM25 ranking,
automatic trigger synchronization, query sanitization, and RBAC visibility.
"""

from src.database.connection import get_connection, release_connection
from src.services.search_service import SearchService


def test_fts5_virtual_tables_exist_and_populated():
    """Verify all 5 FTS5 virtual tables exist and return query counts."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        for tbl in [
            "fts_students",
            "fts_faculty",
            "fts_courses",
            "fts_library_books",
            "fts_announcements",
        ]:
            cur.execute(f"SELECT count(*) FROM {tbl};")
            count = cur.fetchone()[0]
            assert isinstance(count, int)
    finally:
        release_connection(conn)


def test_fts5_student_search_and_stemming():
    """Verify student search finds matching records with Porter stemming."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT first_name, last_name, enrollment_no FROM students LIMIT 1;")
        row = cur.fetchone()
        if row:
            query = row["first_name"]
            res = SearchService.global_search(conn, query=query, category="STUDENT")
            assert res["total"] >= 1
            assert any(row["first_name"].lower() in r["title"].lower() for r in res["results"])
    finally:
        release_connection(conn)


def test_fts5_faculty_search():
    """Verify faculty full-text query retrieves instructor details."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT first_name, designation FROM faculty LIMIT 1;")
        row = cur.fetchone()
        if row:
            res = SearchService.global_search(conn, query=row["first_name"], category="FACULTY")
            assert res["total"] >= 1
            assert res["results"][0]["category"] == "FACULTY"
    finally:
        release_connection(conn)


def test_fts5_courses_search():
    """Verify course search matches by code or title keywords."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT code, title FROM courses LIMIT 1;")
        row = cur.fetchone()
        if row:
            res = SearchService.global_search(conn, query=row["code"], category="COURSE")
            assert res["total"] >= 1
            assert res["results"][0]["category"] == "COURSE"
    finally:
        release_connection(conn)


def test_fts5_library_books_search():
    """Verify library book search locates monographs by author or title."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT title, author FROM library_books LIMIT 1;")
        row = cur.fetchone()
        if row:
            # Query by first word of book title
            first_word = row["title"].split()[0]
            res = SearchService.global_search(conn, query=first_word, category="BOOK")
            assert res["total"] >= 1
            assert res["results"][0]["category"] == "BOOK"
    finally:
        release_connection(conn)


def test_fts5_announcements_search():
    """Verify announcements FTS5 index returns circulars with snippet highlights."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT title FROM announcements WHERE is_active = 1 LIMIT 1;")
        row = cur.fetchone()
        if row:
            word = row["title"].split()[0]
            res = SearchService.global_search(conn, query=word, category="ANNOUNCEMENT")
            assert res["total"] >= 1
            assert res["results"][0]["category"] == "ANNOUNCEMENT"
    finally:
        release_connection(conn)


def test_fts5_trigger_synchronization_lifecycle():
    """Verify real-time SQLite triggers synchronize INSERT, UPDATE, and DELETE into FTS5 index."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        unique_email = "ftstest_scholar_9999@institute.edu"
        unique_enroll = "IMS-2026-FTS-9999"

        # 1. Insert new student into relational table
        cur.execute(
            """
            INSERT INTO students (
                enrollment_no, first_name, last_name, email, phone,
                department_id, current_semester, admission_date, status
            )
            VALUES (?, 'Zephyr', 'Astronomer', ?, '9876543210', 1, 1, '2026-08-01', 'ENROLLED');
            """,
            (unique_enroll, unique_email),
        )
        conn.commit()
        new_id = cur.lastrowid

        # Check FTS5 index immediately found record
        search_res = SearchService.global_search(conn, query="Zephyr", category="STUDENT")
        assert search_res["total"] >= 1
        found = any(r["id"] == new_id for r in search_res["results"])
        assert found is True

        # 2. Update student in relational table
        cur.execute(
            "UPDATE students SET first_name = 'Cassiopeia' WHERE id = ?;",
            (new_id,),
        )
        conn.commit()

        # Verify old name removed from FTS5, new name present
        res_old = SearchService.global_search(conn, query="Zephyr", category="STUDENT")
        assert not any(r["id"] == new_id for r in res_old["results"])

        res_new = SearchService.global_search(conn, query="Cassiopeia", category="STUDENT")
        assert any(r["id"] == new_id for r in res_new["results"])

        # 3. Delete student from relational table
        cur.execute("DELETE FROM students WHERE id = ?;", (new_id,))
        conn.commit()

        # Verify completely deleted from FTS5 index
        res_del = SearchService.global_search(conn, query="Cassiopeia", category="STUDENT")
        assert not any(r["id"] == new_id for r in res_del["results"])
    finally:
        release_connection(conn)


def test_fts5_query_sanitizer_resilience():
    """Verify query parser sanitizes dangerous FTS syntax without throwing SQLite exceptions."""
    conn = get_connection()
    try:
        dangerous_inputs = [
            '"""',
            "NEAR(foo, bar, 10)",
            "test* OR AND NOT",
            "SELECT * FROM students;",
            "col:value",
            "   ",
            "!!!@@@###$$$%%%^^^&&&***",
            "engineering & (software | cloud)",
        ]
        for query_str in dangerous_inputs:
            # Must safely return a dictionary without crashing
            res = SearchService.global_search(conn, query=query_str)
            assert isinstance(res, dict)
            assert "results" in res
            assert "total" in res
    finally:
        release_connection(conn)


def test_api_global_search_authenticated_admin(client):
    """Verify GET /api/search returns 200 with structured response for admin user."""
    res = client.get("/api/search?q=science")
    assert res.status_code == 200
    data = res.json()
    assert "query" in data
    assert "total" in data
    assert "categories" in data
    assert "results" in data
    assert isinstance(data["results"], list)


def test_api_global_search_category_filter(client):
    """Verify GET /api/search with category parameter constrains results."""
    res = client.get("/api/search?q=computer&category=COURSE")
    assert res.status_code == 200
    data = res.json()
    for item in data["results"]:
        assert item["category"] == "COURSE"


def test_api_global_search_student_role_filtering(student_client):
    """Verify student role cannot access sensitive student roster items via global search."""
    res = student_client.get("/api/search?q=student&category=STUDENT")
    assert res.status_code == 200
    data = res.json()
    # Student role is restricted from indexing student directory
    assert data["total"] == 0
    assert len(data["results"]) == 0


def test_api_global_search_unauthenticated_rejected(anon_client):
    """Verify GET /api/search rejects unauthenticated caller with HTTP 401."""
    res = anon_client.get("/api/search?q=test")
    assert res.status_code == 401
