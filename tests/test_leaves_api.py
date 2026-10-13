"""Unit and integration test suite for Institutional Leave & Absence Management."""

from fastapi.testclient import TestClient


def test_submit_student_leave(client: TestClient):
    payload = {
        "applicant_type": "STUDENT",
        "applicant_id": 1,
        "applicant_name": "John Doe",
        "leave_type": "SICK",
        "start_date": "2026-10-15",
        "end_date": "2026-10-18",
        "reason": "Recovering from high fever and doctor advised rest.",
    }
    res = client.post("/api/leaves", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["id"] is not None
    assert data["status"] == "PENDING"
    assert data["applicant_name"] == "John Doe"
    assert data["leave_type"] == "SICK"


def test_submit_faculty_leave(client: TestClient):
    payload = {
        "applicant_type": "FACULTY",
        "applicant_id": 1,
        "applicant_name": "Dr. Alan Turing",
        "leave_type": "ACADEMIC",
        "start_date": "2026-11-01",
        "end_date": "2026-11-04",
        "reason": "Attending international symposium on AI architecture.",
    }
    res = client.post("/api/leaves", json=payload)
    assert res.status_code == 201
    assert res.json()["applicant_type"] == "FACULTY"


def test_list_leaves_and_filtering(client: TestClient):
    res = client.get("/api/leaves?applicant_type=STUDENT&status=PENDING")
    assert res.status_code == 200
    leaves = res.json()
    assert len(leaves) >= 1
    assert all(l["applicant_type"] == "STUDENT" for l in leaves)
    assert all(l["status"] == "PENDING" for l in leaves)


def test_update_leave_status_approved_and_rejected(client: TestClient):
    # Submit a new leave
    create_res = client.post(
        "/api/leaves",
        json={
            "applicant_type": "STUDENT",
            "applicant_id": 2,
            "applicant_name": "Jane Smith",
            "leave_type": "CASUAL",
            "start_date": "2026-10-20",
            "end_date": "2026-10-22",
            "reason": "Family wedding out of state.",
        },
    )
    leave_id = create_res.json()["id"]

    # Approve
    approve_res = client.put(
        f"/api/leaves/{leave_id}/status",
        json={
            "status": "APPROVED",
            "review_remarks": "Approved. Ensure lecture notes are copied from peers.",
            "reviewed_by": "Academic Dean",
        },
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "APPROVED"
    assert approve_res.json()["reviewed_by"] == "Academic Dean"

    # Reject another
    create_res2 = client.post(
        "/api/leaves",
        json={
            "applicant_type": "STUDENT",
            "applicant_id": 2,
            "applicant_name": "Jane Smith",
            "leave_type": "CASUAL",
            "start_date": "2026-10-25",
            "end_date": "2026-10-26",
            "reason": "Unspecified personal errand.",
        },
    )
    leave_id2 = create_res2.json()["id"]

    reject_res = client.put(
        f"/api/leaves/{leave_id2}/status",
        json={
            "status": "REJECTED",
            "review_remarks": "Insufficient justification during exam revision week.",
            "reviewed_by": "Academic Dean",
        },
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "REJECTED"


def test_leave_stats_summary(client: TestClient):
    res = client.get("/api/leaves/stats/summary")
    assert res.status_code == 200
    stats = res.json()
    assert stats["total"] >= 3
    assert "pending" in stats
    assert "approved" in stats
    assert "rejected" in stats


def test_view_leaves_html_page(client: TestClient):
    res = client.get("/leaves")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "Leave & Absence Management" in res.text
