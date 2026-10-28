"""Edge Case and Validation Robustness Test Suite.
Verifies:
- Full Unicode name and text support (Devanagari, CJK, Arabic, accented Latin)
- Boundary constraints and maximum length rejection
- Whitespace-only and empty string validation
- Malformed payloads and non-existent resource handling
"""

from fastapi.testclient import TestClient


def test_unicode_student_and_faculty_profiles(client: TestClient):
    """Verify storing, retrieving, and searching profiles with diverse Unicode scripts:
    Devanagari, CJK, Arabic, and accented Latin.
    """
    unicode_profiles = [
        {
            "first_name": "आदित्य",
            "last_name": "भुरे",
            "email": "aditya.devanagari@example.edu",
            "address": "१२३ शिवाजी मार्ग, पुणे, महाराष्ट्र",
        },
        {
            "first_name": "小伟",
            "last_name": "张",
            "email": "zhang.wei@example.edu",
            "address": "北京市海淀区中关村南大街5号",
        },
        {
            "first_name": "José-María",
            "last_name": "Peña Müller",
            "email": "jose.pena@example.edu",
            "address": "Av. de la Constitución 42, Sevilla",
        },
        {
            "first_name": "فاطمة",
            "last_name": "الزهراء",
            "email": "fatima.zahra@example.edu",
            "address": "شارع النصر، القاهرة",
        },
    ]

    for p in unicode_profiles:
        # Create student with Unicode characters
        res = client.post(
            "/api/students",
            json={
                "first_name": p["first_name"],
                "last_name": p["last_name"],
                "email": p["email"],
                "phone": "+91 98765 43210",
                "department_id": 1,
                "current_semester": 1,
                "address": p["address"],
                "admission_date": "2026-08-15",
            },
        )
        assert res.status_code == 201, f"Failed for {p['first_name']}: {res.text}"
        data = res.json()
        assert data["first_name"] == p["first_name"]
        assert data["last_name"] == p["last_name"]
        assert data["address"] == p["address"]

        student_id = data["id"]

        # Fetch by ID to confirm persistent SQLite UTF-8 storage
        fetch_res = client.get(f"/api/students/{student_id}")
        assert fetch_res.status_code == 200
        fetched = fetch_res.json()
        assert fetched["first_name"] == p["first_name"]
        assert fetched["address"] == p["address"]

        # Search by Unicode first name substring
        search_res = client.get(f"/api/students?search={p['first_name']}")
        assert search_res.status_code == 200
        search_results = search_res.json()
        assert any(s["id"] == student_id for s in search_results)


def test_empty_and_whitespace_only_validation(client: TestClient):
    """Verify that empty or whitespace-only inputs are rejected with 422 Unprocessable Entity."""
    # Empty first_name
    res_empty = client.post(
        "/api/students",
        json={
            "first_name": "",
            "last_name": "Smith",
            "email": "empty.first@example.edu",
            "department_id": 1,
            "current_semester": 1,
        },
    )
    assert res_empty.status_code == 422

    # Whitespace-only first_name
    res_spaces = client.post(
        "/api/students",
        json={
            "first_name": "   ",
            "last_name": "Smith",
            "email": "spaces.first@example.edu",
            "department_id": 1,
            "current_semester": 1,
        },
    )
    # Pydantic or service layer rejects empty stripped string
    assert res_spaces.status_code in (400, 422)


def test_invalid_email_format_rejection(client: TestClient):
    """Verify invalid email formats are caught and rejected."""
    bad_emails = [
        "not-an-email",
        "@missing-user.com",
        "missing-domain@",
        "spaces in email@domain.com",
    ]
    for email in bad_emails:
        res = client.post(
            "/api/students",
            json={
                "first_name": "Bad",
                "last_name": "Email",
                "email": email,
                "department_id": 1,
                "current_semester": 1,
            },
        )
        assert res.status_code == 422, f"Failed to reject invalid email '{email}'"


def test_numeric_boundary_and_range_validation(client: TestClient):
    """Verify negative amounts, invalid semester values, and out-of-range inputs are rejected."""
    # Negative invoice total amount
    res_neg_invoice = client.post(
        "/api/finance/invoices",
        json={
            "student_id": 1,
            "title": "Negative Tuition",
            "term_name": "Spring 2026",
            "total_amount": -500.0,
            "due_date": "2026-12-31",
        },
    )
    assert res_neg_invoice.status_code == 422

    # Invalid semester (< 1 or > 12)
    res_bad_sem = client.post(
        "/api/students",
        json={
            "first_name": "Semester",
            "last_name": "Overflow",
            "email": "semester.overflow@example.edu",
            "department_id": 1,
            "current_semester": 99,
        },
    )
    assert res_bad_sem.status_code == 422

    # Negative fee payment amount
    res_neg_pay = client.post(
        "/api/finance/payments",
        json={
            "invoice_id": 1,
            "amount": -100.0,
            "payment_method": "CASH",
        },
    )
    assert res_neg_pay.status_code == 422


def test_field_length_upper_bound_rejection(client: TestClient):
    """Verify fields exceeding maximum allowed length constraint are rejected."""
    # Very long first name (> 100 characters)
    oversized_name = "A" * 250
    res = client.post(
        "/api/students",
        json={
            "first_name": oversized_name,
            "last_name": "Normal",
            "email": "oversized.name@example.edu",
            "department_id": 1,
            "current_semester": 1,
        },
    )
    assert res.status_code == 422


def test_nonexistent_entity_returns_404(client: TestClient):
    """Verify querying non-existent entities consistently returns 404 Not Found."""
    non_existent_id = 999999

    endpoints = [
        f"/api/students/{non_existent_id}",
        f"/api/faculty/{non_existent_id}",
        f"/api/courses/{non_existent_id}",
        f"/api/finance/invoices/{non_existent_id}",
        f"/api/timetable/{non_existent_id}",
        f"/api/library/books/{non_existent_id}",
    ]

    for ep in endpoints:
        res = client.get(ep)
        assert res.status_code == 404, (
            f"Endpoint {ep} did not return 404! Returned {res.status_code}"
        )
        # Ensure response contains detail message
        data = res.json()
        assert "detail" in data or "error" in data


def test_malformed_json_returns_422(client: TestClient):
    """Verify sending invalid JSON body returns 422 Unprocessable Entity."""
    headers = {"Content-Type": "application/json"}
    bad_payload = "this is { not valid json: }"
    res = client.post("/api/students", content=bad_payload, headers=headers)
    assert res.status_code == 422
