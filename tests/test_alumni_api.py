"""Unit and integration test suite for Alumni Network & Career Mentorship Hub."""

from fastapi.testclient import TestClient


def test_register_alumnus_and_duplicate_email(client: TestClient):
    payload = {
        "full_name": "Satya Nadella",
        "email": "satya.nadella.alumni@institute.edu",
        "phone": "+91-9876500001",
        "graduation_year": 1988,
        "degree": "B.Tech Electrical",
        "department_id": 1,
        "current_company": "Microsoft Corporation",
        "job_title": "Chairman & Chief Executive Officer",
        "city": "Redmond / Hyderabad",
        "linkedin_url": "https://linkedin.com/in/satyanadella",
        "mentorship_status": "AVAILABLE",
    }
    res = client.post("/api/alumni/members", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["id"] is not None
    assert data["full_name"] == "Satya Nadella"
    assert data["graduation_year"] == 1988

    # Duplicate email rejection
    res_dup = client.post("/api/alumni/members", json=payload)
    assert res_dup.status_code == 400


def test_list_alumni_and_filters(client: TestClient):
    # Register second alumnus
    client.post(
        "/api/alumni/members",
        json={
            "full_name": "Sundar Pichai",
            "email": "sundar.pichai.alumni@institute.edu",
            "phone": "+91-9876500002",
            "graduation_year": 1993,
            "degree": "B.Tech Metallurgy",
            "department_id": 1,
            "current_company": "Alphabet / Google",
            "job_title": "Chief Executive Officer",
            "city": "Mountain View",
            "linkedin_url": "https://linkedin.com/in/sundarpichai",
            "mentorship_status": "BUSY",
        },
    )

    all_alumni = client.get("/api/alumni/members").json()
    assert len(all_alumni) >= 2

    # Filter by graduation year
    batch_88 = client.get("/api/alumni/members?graduation_year=1988").json()
    assert len(batch_88) == 1
    assert batch_88[0]["full_name"] == "Satya Nadella"

    # Search filter
    search_res = client.get("/api/alumni/members?search=Google").json()
    assert len(search_res) == 1
    assert search_res[0]["full_name"] == "Sundar Pichai"


def test_request_mentorship_success(client: TestClient):
    # 1. Enroll student
    student_res = client.post(
        "/api/students",
        json={
            "first_name": "Deepak",
            "last_name": "Bhardwaj",
            "email": "deepak.bhardwaj.mentee@institute.edu",
            "department_id": 1,
            "dob": "2003-04-12",
            "gender": "Male",
        },
    )
    student_id = student_res.json()["id"]

    # 2. Get available mentor (Satya Nadella)
    available_mentors = client.get("/api/alumni/members?mentorship_status=AVAILABLE").json()
    mentor_id = available_mentors[0]["id"]

    # 3. Request mentorship
    res = client.post(
        "/api/alumni/mentorship-requests",
        json={
            "alumni_id": mentor_id,
            "student_id": student_id,
            "mentorship_topic": "Cloud Infrastructure & Engineering Leadership",
            "notes": "Seeking advice on enterprise systems architecture.",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "REQUESTED"
    assert data["mentorship_topic"] == "Cloud Infrastructure & Engineering Leadership"


def test_request_mentorship_busy_alumnus_rejected(client: TestClient):
    # Enroll student
    student_res = client.post(
        "/api/students",
        json={
            "first_name": "Meera",
            "last_name": "Nair",
            "email": "meera.nair.mentee@institute.edu",
            "department_id": 1,
            "dob": "2003-09-25",
            "gender": "Female",
        },
    )
    student_id = student_res.json()["id"]

    # Find busy mentor (Sundar Pichai)
    busy_mentors = client.get("/api/alumni/members?mentorship_status=BUSY").json()
    assert len(busy_mentors) >= 1
    mentor_id = busy_mentors[0]["id"]

    res = client.post(
        "/api/alumni/mentorship-requests",
        json={
            "alumni_id": mentor_id,
            "student_id": student_id,
            "mentorship_topic": "Product Management in Big Tech",
        },
    )
    assert res.status_code == 400
    assert "not accepting mentorship requests" in res.json()["detail"]


def test_update_mentorship_status_accepted_and_completed(client: TestClient):
    requests = client.get("/api/alumni/mentorship-requests").json()
    req_id = requests[0]["id"]

    # Accept
    res_accept = client.put(
        f"/api/alumni/mentorship-requests/{req_id}/status",
        json={
            "status": "ACCEPTED",
            "notes": "Introductory session scheduled for next Saturday.",
        },
    )
    assert res_accept.status_code == 200
    assert res_accept.json()["status"] == "ACCEPTED"

    # Complete
    res_complete = client.put(
        f"/api/alumni/mentorship-requests/{req_id}/status",
        json={
            "status": "COMPLETED",
            "notes": "Completed 4-week architectural roadmap review.",
        },
    )
    assert res_complete.status_code == 200
    assert res_complete.json()["status"] == "COMPLETED"


def test_alumni_stats_and_telemetry(client: TestClient):
    res = client.get("/api/alumni/stats")
    assert res.status_code == 200
    stats = res.json()
    assert stats["total_alumni"] >= 2
    assert stats["available_mentors"] >= 1
    assert stats["graduating_batches_count"] >= 2
    assert stats["completed_mentorships"] >= 1


def test_view_alumni_html_page(client: TestClient):
    res = client.get("/alumni")
    assert res.status_code == 200
    html = res.text
    assert (
        "Alumni Network &amp; Career Mentorship Hub" in html
        or "Alumni Network & Career Mentorship Hub" in html
    )
    assert "Satya Nadella" in html
    assert "modal-register-alumni" in html
    assert "modal-request-mentorship" in html
    assert "modal-update-mentorship" in html
