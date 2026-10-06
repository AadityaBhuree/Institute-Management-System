"""Tests for Admissions & Student Registry Endpoints and Operations."""


def test_enroll_new_student(client):
    """Verify enrolling a new student and generating enrollment number."""
    payload = {
        "first_name": "Aarav",
        "last_name": "Sharma",
        "email": "aarav.sharma@example.edu",
        "phone": "+91 98765 43210",
        "department_id": 1,
        "current_semester": 1,
        "dob": "2005-08-20",
        "gender": "Male",
        "blood_group": "B+",
        "status": "ENROLLED",
    }
    response = client.post("/api/students", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "Aarav"
    assert data["last_name"] == "Sharma"
    assert data["email"] == "aarav.sharma@example.edu"
    assert data["enrollment_no"].startswith("IMS-2026-")
    assert data["id"] > 0


def test_enroll_student_duplicate_email(client):
    """Verify duplicate email rejection."""
    payload = {
        "first_name": "Aarav",
        "last_name": "Sharma",
        "email": "aarav.sharma@example.edu",
        "department_id": 1,
        "current_semester": 1,
        "status": "ENROLLED",
    }
    response = client.post("/api/students", json=payload)
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_enroll_student_invalid_department(client):
    """Verify rejection when department does not exist."""
    payload = {
        "first_name": "Priya",
        "last_name": "Verma",
        "email": "priya.verma@example.edu",
        "department_id": 9999,
        "current_semester": 1,
        "status": "ENROLLED",
    }
    response = client.post("/api/students", json=payload)
    assert response.status_code == 400
    assert "Department with ID 9999 does not exist" in response.json()["detail"]


def test_list_students_and_filtering(client):
    """Verify listing students and applying status filter."""
    # Enroll a second student in ECE
    payload = {
        "first_name": "Rohan",
        "last_name": "Gupta",
        "email": "rohan.gupta@example.edu",
        "department_id": 2,
        "current_semester": 3,
        "status": "PENDING",
    }
    res = client.post("/api/students", json=payload)
    assert res.status_code == 201

    # Filter by department_id = 2
    res_filtered = client.get("/api/students?department_id=2")
    assert res_filtered.status_code == 200
    data = res_filtered.json()
    assert any(s["email"] == "rohan.gupta@example.edu" for s in data)

    # Filter by status = PENDING
    res_status = client.get("/api/students?status=PENDING")
    assert res_status.status_code == 200
    assert all(s["status"] == "PENDING" for s in res_status.json())


def test_search_students(client):
    """Verify search filter by name or enrollment number."""
    response = client.get("/api/students?search=Aarav")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["first_name"] == "Aarav"


def test_get_student_by_id(client):
    """Verify fetching single student profile."""
    # First search for Aarav
    search_res = client.get("/api/students?search=Aarav")
    student_id = search_res.json()[0]["id"]

    res = client.get(f"/api/students/{student_id}")
    assert res.status_code == 200
    assert res.json()["first_name"] == "Aarav"

    # Nonexistent ID
    res_404 = client.get("/api/students/999999")
    assert res_404.status_code == 404


def test_update_student_profile(client):
    """Verify updating student records."""
    search_res = client.get("/api/students?search=Rohan")
    student_id = search_res.json()[0]["id"]

    update_payload = {
        "current_semester": 4,
        "status": "ENROLLED",
        "phone": "+91 99999 88888",
    }
    res = client.put(f"/api/students/{student_id}", json=update_payload)
    assert res.status_code == 200
    updated = res.json()
    assert updated["current_semester"] == 4
    assert updated["status"] == "ENROLLED"
    assert updated["phone"] == "+91 99999 88888"


def test_students_summary_stats(client):
    """Verify students status summary breakdown."""
    res = client.get("/api/students/stats/summary")
    assert res.status_code == 200
    stats = res.json()
    assert "ENROLLED" in stats
    assert stats["ENROLLED"] >= 1


def test_delete_student(client):
    """Verify deleting a student record."""
    # Enroll a temporary student
    res = client.post(
        "/api/students",
        json={
            "first_name": "Temp",
            "last_name": "Student",
            "email": "temp.delete@example.edu",
            "department_id": 1,
            "current_semester": 1,
            "status": "WITHDRAWN",
        },
    )
    temp_id = res.json()["id"]

    del_res = client.delete(f"/api/students/{temp_id}")
    assert del_res.status_code == 200

    # Ensure student is gone
    get_res = client.get(f"/api/students/{temp_id}")
    assert get_res.status_code == 404


def test_view_students_html_page(client):
    """Verify HTML rendering of student registry page."""
    response = client.get("/students")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    html = response.text
    assert "Admissions & Student Registry" in html
    assert "Register Admission" in html
    assert "IMS-2026-" in html
