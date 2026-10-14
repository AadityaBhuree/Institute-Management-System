"""Unit and integration test suite for Reports & Analytics CSV Data Export Engine."""

from fastapi.testclient import TestClient


def test_export_students_csv(client: TestClient):
    """Verify downloading students roster CSV with proper headers and data."""
    # Enroll sample student to ensure data exists
    client.post(
        "/api/students",
        json={
            "first_name": "Vikram",
            "last_name": "Sarabhai",
            "email": "vikram.sarabhai@space.edu",
            "department_id": 1,
            "dob": "2002-08-12",
            "gender": "Male",
        },
    )

    res = client.get("/api/reports/export/students/csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "attachment; filename=students_roster.csv" in res.headers["content-disposition"]

    csv_text = res.text
    lines = csv_text.strip().splitlines()
    assert len(lines) >= 2
    header = lines[0]
    assert "Enrollment No" in header
    assert "First Name" in header
    assert "Last Name" in header
    assert "Email" in header
    assert "Department" in header
    assert "Semester" in header
    assert "Admission Date" in header
    assert any("Vikram" in line for line in lines)


def test_export_attendance_risk_csv(client: TestClient):
    """Verify attendance risk sentinel CSV export."""
    res = client.get("/api/reports/export/attendance-risk/csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "attachment; filename=attendance_risk_sentinel.csv" in res.headers["content-disposition"]

    csv_text = res.text
    lines = csv_text.strip().splitlines()
    assert len(lines) >= 1
    header = lines[0]
    assert "Enrollment No" in header
    assert "Total Sessions" in header
    assert "Attendance Percentage" in header
    assert "Risk Level" in header


def test_export_finances_csv(client: TestClient):
    """Verify bursar fee ledger audit CSV export."""
    # Issue invoice to guarantee row in ledger
    student_res = client.post(
        "/api/students",
        json={
            "first_name": "Homi",
            "last_name": "Bhabha",
            "email": "homi.bhabha@atomic.edu",
            "department_id": 1,
            "dob": "2003-10-30",
            "gender": "Male",
        },
    )
    student_id = student_res.json()["id"]

    client.post(
        "/api/finance/invoices",
        json={
            "student_id": student_id,
            "title": "Semester 1 Academic Fee",
            "term_name": "Fall 2026",
            "total_amount": 3500.0,
            "due_date": "2026-12-31",
        },
    )

    res = client.get("/api/reports/export/finances/csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "attachment; filename=financial_ledger_audit.csv" in res.headers["content-disposition"]

    csv_text = res.text
    lines = csv_text.strip().splitlines()
    assert len(lines) >= 2
    header = lines[0]
    assert "Invoice No" in header
    assert "Student Name" in header
    assert "Total Invoiced" in header
    assert "Balance Due" in header
    assert any("Homi Bhabha" in line for line in lines)


def test_export_with_department_filtering(client: TestClient):
    """Verify CSV export filtering by department ID."""
    res = client.get("/api/reports/export/students/csv?department_id=1")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert len(res.text.strip().splitlines()) >= 2


def test_reports_html_view_has_export_buttons(client: TestClient):
    """Verify HTML reports view renders direct CSV download buttons."""
    res = client.get("/reports")
    assert res.status_code == 200
    html = res.text
    assert "btn-export-students-csv" in html
    assert "btn-export-risk-csv" in html
    assert "btn-export-finance-csv" in html
    assert "/api/reports/export/students/csv" in html
    assert "/api/reports/export/attendance-risk/csv" in html
    assert "/api/reports/export/finances/csv" in html
