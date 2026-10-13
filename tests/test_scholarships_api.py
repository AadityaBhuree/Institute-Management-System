"""Unit and integration test suite for Scholarships, Grants & Financial Aid."""

from fastapi.testclient import TestClient


def test_create_scholarship_scheme_and_duplicate_name(client: TestClient):
    payload = {
        "scheme_name": "Dean's Merit Excellence Fellowship",
        "sponsor_type": "INSTITUTIONAL",
        "award_amount": 50000.0,
        "min_gpa_required": 8.5,
        "max_family_income": 600000.0,
        "eligible_category": "ALL",
        "status": "ACTIVE",
    }
    res = client.post("/api/scholarships/schemes", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["id"] is not None
    assert data["scheme_name"] == "Dean's Merit Excellence Fellowship"
    assert data["award_amount"] == 50000.0

    # Negative: duplicate scheme
    res_dup = client.post("/api/scholarships/schemes", json=payload)
    assert res_dup.status_code == 400


def test_apply_for_scholarship_success_and_gating(client: TestClient):
    # 1. Enroll eligible student
    student_res = client.post(
        "/api/students",
        json={
            "first_name": "Aruna",
            "last_name": "Roy",
            "email": "aruna.roy.aid@institute.edu",
            "department_id": 1,
            "dob": "2003-08-19",
            "gender": "Female",
        },
    )
    assert student_res.status_code == 201
    student_id = student_res.json()["id"]

    # 2. Get scheme
    schemes = client.get("/api/scholarships/schemes").json()
    scheme_id = schemes[0]["id"]

    # 3. Apply with qualifying GPA 9.1 and family income 450,000
    res = client.post(
        "/api/scholarships/apply",
        json={
            "scheme_id": scheme_id,
            "student_id": student_id,
            "current_gpa": 9.1,
            "annual_family_income": 450000.0,
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "PENDING"
    assert data["student_name"] == "Aruna Roy"


def test_apply_below_min_gpa_rejected(client: TestClient):
    # Enroll another student with lower GPA
    student_res = client.post(
        "/api/students",
        json={
            "first_name": "Vijay",
            "last_name": "Kumar",
            "email": "vijay.kumar.aid@institute.edu",
            "department_id": 1,
            "dob": "2002-11-10",
            "gender": "Male",
        },
    )
    student_id = student_res.json()["id"]

    schemes = client.get("/api/scholarships/schemes").json()
    scheme_id = schemes[0]["id"]  # requires 8.5 GPA

    res = client.post(
        "/api/scholarships/apply",
        json={
            "scheme_id": scheme_id,
            "student_id": student_id,
            "current_gpa": 7.2,
            "annual_family_income": 300000.0,
        },
    )
    assert res.status_code == 400
    assert "Academic criteria not satisfied" in res.json()["detail"]


def test_apply_exceeding_family_income_rejected(client: TestClient):
    # Enroll student with high family income
    student_res = client.post(
        "/api/students",
        json={
            "first_name": "Rohit",
            "last_name": "Singhania",
            "email": "rohit.singhania.aid@institute.edu",
            "department_id": 1,
            "dob": "2003-01-20",
            "gender": "Male",
        },
    )
    student_id = student_res.json()["id"]

    schemes = client.get("/api/scholarships/schemes").json()
    scheme_id = schemes[0]["id"]  # max income 600,000

    res = client.post(
        "/api/scholarships/apply",
        json={
            "scheme_id": scheme_id,
            "student_id": student_id,
            "current_gpa": 9.5,
            "annual_family_income": 1200000.0,
        },
    )
    assert res.status_code == 400
    assert "Financial criteria not satisfied" in res.json()["detail"]


def test_review_scholarship_approved_and_disbursed(client: TestClient):
    apps = client.get("/api/scholarships/applications").json()
    app_id = apps[0]["id"]

    # Review to DISBURSED
    res = client.put(
        f"/api/scholarships/applications/{app_id}/review",
        json={
            "status": "DISBURSED",
            "review_remarks": "Outstanding academic merit and financial eligibility verified.",
            "disbursed_amount": 50000.0,
        },
    )
    assert res.status_code == 200
    updated = res.json()
    assert updated["status"] == "DISBURSED"
    assert updated["disbursed_amount"] == 50000.0


def test_scholarship_stats_and_telemetry(client: TestClient):
    res = client.get("/api/scholarships/stats")
    assert res.status_code == 200
    stats = res.json()
    assert stats["total_schemes"] >= 1
    assert stats["total_applications"] >= 1
    assert stats["awarded_count"] >= 1
    assert stats["total_funds_disbursed"] >= 50000.0


def test_view_scholarships_html_page(client: TestClient):
    res = client.get("/scholarships")
    assert res.status_code == 200
    html = res.text
    assert (
        "Scholarships &amp; Financial Aid Hub" in html or "Scholarships & Financial Aid Hub" in html
    )
    assert (
        "Dean&#39;s Merit Excellence Fellowship" in html
        or "Dean's Merit Excellence Fellowship" in html
    )
    assert "modal-create-scheme" in html
    assert "modal-apply-scholarship" in html
    assert "modal-review-application" in html
