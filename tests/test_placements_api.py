"""Unit and integration test suite for Campus Placements & Corporate Recruitment Cell."""

from fastapi.testclient import TestClient


def test_create_placement_drive_success_and_validation(client: TestClient):
    payload = {
        "company_name": "Google DeepMind",
        "industry": "Artificial Intelligence & Cloud",
        "job_title": "Research Systems Engineer",
        "job_location": "Bengaluru / Hybrid",
        "package_lpa": 34.5,
        "min_gpa_required": 8.0,
        "eligible_departments": "CSE, ECE",
        "drive_date": "2026-11-15",
        "registration_deadline": "2026-11-01",
        "status": "ACTIVE",
    }
    res = client.post("/api/placements/drives", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["id"] is not None
    assert data["company_name"] == "Google DeepMind"
    assert data["package_lpa"] == 34.5
    assert data["min_gpa_required"] == 8.0

    # Negative validation: invalid package
    invalid_payload = payload.copy()
    invalid_payload["package_lpa"] = -5.0
    res_invalid = client.post("/api/placements/drives", json=invalid_payload)
    assert res_invalid.status_code == 422


def test_list_placement_drives_and_search_filter(client: TestClient):
    # Create second drive
    client.post(
        "/api/placements/drives",
        json={
            "company_name": "NVIDIA Graphics",
            "industry": "Semiconductors & GPU Computing",
            "job_title": "CUDA Architect",
            "job_location": "Hyderabad",
            "package_lpa": 28.0,
            "min_gpa_required": 7.5,
            "eligible_departments": "CSE, ECE",
            "drive_date": "2026-11-20",
            "registration_deadline": "2026-11-05",
            "status": "UPCOMING",
        },
    )

    # List all drives
    all_drives = client.get("/api/placements/drives").json()
    assert len(all_drives) >= 2

    # Filter by status UPCOMING
    upcoming = client.get("/api/placements/drives?status=UPCOMING").json()
    assert any(d["company_name"] == "NVIDIA Graphics" for d in upcoming)

    # Search filter
    search_res = client.get("/api/placements/drives?search=DeepMind").json()
    assert len(search_res) == 1
    assert search_res[0]["company_name"] == "Google DeepMind"


def test_apply_for_drive_with_gpa_eligibility(client: TestClient):
    # 1. Enroll eligible student
    student_res = client.post(
        "/api/students",
        json={
            "first_name": "Srinivasa",
            "last_name": "Ramanujan",
            "email": "srinivasa.ramanujan.placement@institute.edu",
            "department_id": 1,
            "dob": "2002-12-22",
            "gender": "Male",
        },
    )
    assert student_res.status_code == 201
    student_id = student_res.json()["id"]

    # 2. Find Google DeepMind drive (min GPA: 8.0)
    drives = client.get("/api/placements/drives?search=DeepMind").json()
    drive_id = drives[0]["id"]

    # 3. Apply with qualifying GPA 9.85
    apply_res = client.post(
        "/api/placements/apply",
        json={
            "drive_id": drive_id,
            "student_id": student_id,
            "current_gpa": 9.85,
            "resume_link": "https://dossier.org/ramanujan.pdf",
            "remarks": "Exceptional mathematical foundations",
        },
    )
    assert apply_res.status_code == 201
    app_data = apply_res.json()
    assert app_data["status"] == "APPLIED"
    assert app_data["company_name"] == "Google DeepMind"
    assert app_data["current_gpa"] == 9.85


def test_apply_for_drive_below_min_gpa_rejected(client: TestClient):
    # 1. Enroll student with lower GPA
    student_res = client.post(
        "/api/students",
        json={
            "first_name": "Junior",
            "last_name": "Scholar",
            "email": "junior.scholar.placement@institute.edu",
            "department_id": 1,
            "dob": "2004-01-01",
            "gender": "Other",
        },
    )
    student_id = student_res.json()["id"]

    drives = client.get("/api/placements/drives?search=DeepMind").json()
    drive_id = drives[0]["id"]

    # 2. Apply with GPA 7.20 (min required is 8.0)
    apply_res = client.post(
        "/api/placements/apply",
        json={
            "drive_id": drive_id,
            "student_id": student_id,
            "current_gpa": 7.20,
            "resume_link": "https://dossier.org/junior.pdf",
        },
    )
    assert apply_res.status_code == 400
    assert "Eligibility requirement not met" in apply_res.json()["detail"]


def test_apply_for_drive_duplicate_rejected(client: TestClient):
    # Find Ramanujan student ID and DeepMind drive ID
    drives = client.get("/api/placements/drives?search=DeepMind").json()
    drive_id = drives[0]["id"]
    apps = client.get(f"/api/placements/applications?drive_id={drive_id}").json()
    assert len(apps) > 0
    student_id = apps[0]["student_id"]

    # Attempt second application
    dup_res = client.post(
        "/api/placements/apply",
        json={
            "drive_id": drive_id,
            "student_id": student_id,
            "current_gpa": 9.90,
        },
    )
    assert dup_res.status_code == 400
    assert "already submitted an application" in dup_res.json()["detail"]


def test_apply_nonexistent_drive_and_student(client: TestClient):
    res_drive = client.post(
        "/api/placements/apply",
        json={
            "drive_id": 99999,
            "student_id": 1,
            "current_gpa": 8.5,
        },
    )
    assert res_drive.status_code == 400
    assert "not found" in res_drive.json()["detail"]

    drives = client.get("/api/placements/drives").json()
    drive_id = drives[0]["id"]
    res_student = client.post(
        "/api/placements/apply",
        json={
            "drive_id": drive_id,
            "student_id": 99999,
            "current_gpa": 8.5,
        },
    )
    assert res_student.status_code == 400
    assert "not found" in res_student.json()["detail"]


def test_update_candidate_pipeline_stage_and_offer(client: TestClient):
    # Retrieve application
    apps = client.get("/api/placements/applications").json()
    assert len(apps) > 0
    app_id = apps[0]["id"]

    # Advance to SHORTLISTED
    res_shortlist = client.put(
        f"/api/placements/applications/{app_id}/status",
        json={"status": "SHORTLISTED", "remarks": "Resume screened and approved"},
    )
    assert res_shortlist.status_code == 200
    assert res_shortlist.json()["status"] == "SHORTLISTED"

    # Advance to TECHNICAL_ROUND with interview date
    res_tech = client.put(
        f"/api/placements/applications/{app_id}/status",
        json={
            "status": "TECHNICAL_ROUND",
            "interview_date": "2026-11-16",
            "remarks": "System architecture interview",
        },
    )
    assert res_tech.status_code == 200
    assert res_tech.json()["status"] == "TECHNICAL_ROUND"
    assert res_tech.json()["interview_date"] == "2026-11-16"

    # Advance to SELECTED with confirmed offer package
    res_selected = client.put(
        f"/api/placements/applications/{app_id}/status",
        json={
            "status": "SELECTED",
            "offer_package_lpa": 36.0,
            "remarks": "Extended offer package with signing bonus",
        },
    )
    assert res_selected.status_code == 200
    assert res_selected.json()["status"] == "SELECTED"
    assert res_selected.json()["offer_package_lpa"] == 36.0


def test_placement_stats_and_html_view(client: TestClient):
    stats_res = client.get("/api/placements/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_drives"] >= 2
    assert stats["total_applications"] >= 1
    assert stats["selected_offers"] >= 1
    assert stats["average_package_lpa"] > 0.0
    assert stats["highest_package_lpa"] >= 36.0

    # HTML page rendering
    html_res = client.get("/placements")
    assert html_res.status_code == 200
    assert "text/html" in html_res.headers["content-type"]
    assert (
        "Career Placements &amp; Corporate Hub" in html_res.text
        or "Career Placements" in html_res.text
    )
    assert "Google DeepMind" in html_res.text
