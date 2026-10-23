"""Unit and integration test suite for Campus Announcements & Notice Board."""

from fastapi.testclient import TestClient


def test_create_announcement(client: TestClient):
    payload = {
        "title": "Fall Semester Final Exam Schedule Released",
        "content": "All students must review their course examination dates on the portal.",
        "category": "EXAM",
        "target_audience": "STUDENTS",
        "priority": "HIGH",
        "author_name": "Dean of Academic Affairs",
    }
    response = client.post("/api/announcements", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["title"] == payload["title"]
    assert data["priority"] == "HIGH"
    assert data["is_active"] == 1


def test_list_announcements_with_filters(client: TestClient):
    # Post a faculty notice
    client.post(
        "/api/announcements",
        json={
            "title": "Faculty Departmental Meeting",
            "content": "All faculty must attend the curriculum alignment meeting.",
            "category": "ACADEMIC",
            "target_audience": "FACULTY",
            "priority": "NORMAL",
            "author_name": "Department Head",
        },
    )

    # Filter for FACULTY
    res = client.get("/api/announcements?target_audience=FACULTY")
    assert res.status_code == 200
    notices = res.json()
    assert len(notices) >= 1
    assert any(n["target_audience"] in ("FACULTY", "ALL") for n in notices)


def test_search_announcements(client: TestClient):
    res = client.get("/api/announcements?search=Schedule")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert "Schedule" in data[0]["title"]


def test_toggle_announcement_active_and_delete(client: TestClient):
    # Create notice
    create_res = client.post(
        "/api/announcements",
        json={
            "title": "Temporary Notice to Archive",
            "content": "This notice will be toggled and deleted.",
            "category": "GENERAL",
            "target_audience": "ALL",
            "priority": "LOW",
        },
    )
    notice_id = create_res.json()["id"]

    # Toggle to inactive
    toggle_res = client.put(f"/api/announcements/{notice_id}/toggle-active?is_active=0")
    assert toggle_res.status_code == 200
    assert toggle_res.json()["is_active"] == 0

    # Delete
    del_res = client.delete(f"/api/announcements/{notice_id}")
    assert del_res.status_code == 200

    # Verify not found
    get_res = client.get(f"/api/announcements/{notice_id}")
    assert get_res.status_code == 404


def test_view_announcements_html_page(client: TestClient):
    res = client.get("/announcements")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "Campus Announcements" in res.text
