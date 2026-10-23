"""Unit and integration test suite for Academic Timetable & Lecture Scheduling."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def sample_course_id(client: TestClient):
    """Ensure at least one course exists and return its ID."""
    # Ensure a faculty member exists
    fac_res = client.post(
        "/api/faculty",
        json={
            "first_name": "Timetable",
            "last_name": "Instructor",
            "email": "tt.instructor@example.edu",
            "phone": "+1 555-9988",
            "department_id": 1,
            "designation": "Associate Professor",
            "qualification": "Ph.D. Computer Systems",
        },
    )
    if fac_res.status_code == 201:
        instructor_id = fac_res.json()["id"]
    else:
        existing = client.get("/api/faculty?search=Timetable").json()
        instructor_id = existing[0]["id"]

    # Ensure course exists
    course_res = client.post(
        "/api/courses",
        json={
            "code": "TT-101",
            "title": "Discrete Mathematics & Systems",
            "department_id": 1,
            "credits": 3,
            "semester": 1,
            "capacity": 50,
            "instructor_id": instructor_id,
        },
    )
    if course_res.status_code == 201:
        return course_res.json()["id"]
    else:
        existing_courses = client.get("/api/courses?search=TT-101").json()
        return existing_courses[0]["id"]


def test_create_timetable_slot_success(client: TestClient, sample_course_id: int):
    payload = {
        "course_id": sample_course_id,
        "day_of_week": "Monday",
        "start_time": "09:00",
        "end_time": "10:30",
        "room_number": "LH-101",
        "building": "Main Academic Block",
    }
    res = client.post("/api/timetable", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["id"] is not None
    assert data["course_id"] == sample_course_id
    assert data["day_of_week"] == "Monday"
    assert data["room_number"] == "LH-101"


def test_room_collision_prevention(client: TestClient, sample_course_id: int):
    # Try to schedule another slot in LH-101 during overlapping time on Monday
    payload = {
        "course_id": sample_course_id,
        "day_of_week": "Monday",
        "start_time": "10:00",
        "end_time": "11:30",
        "room_number": "LH-101",
        "building": "Main Academic Block",
    }
    res = client.post("/api/timetable", json=payload)
    assert res.status_code == 400
    assert "Room collision" in res.json()["detail"]


def test_invalid_time_range_rejection(client: TestClient, sample_course_id: int):
    payload = {
        "course_id": sample_course_id,
        "day_of_week": "Tuesday",
        "start_time": "11:00",
        "end_time": "10:00",
        "room_number": "LH-102",
    }
    res = client.post("/api/timetable", json=payload)
    assert res.status_code == 400
    assert "start time" in res.json()["detail"].lower()


def test_list_slots_and_weekly_matrix(client: TestClient, sample_course_id: int):
    # List slots
    res = client.get("/api/timetable?day_of_week=Monday")
    assert res.status_code == 200
    slots = res.json()
    assert len(slots) >= 1
    assert slots[0]["day_of_week"] == "Monday"

    # Matrix
    matrix_res = client.get("/api/timetable/matrix")
    assert matrix_res.status_code == 200
    matrix = matrix_res.json()
    assert "Monday" in matrix
    assert "Tuesday" in matrix
    assert len(matrix["Monday"]) >= 1


def test_delete_timetable_slot(client: TestClient, sample_course_id: int):
    # Create slot to delete
    create_res = client.post(
        "/api/timetable",
        json={
            "course_id": sample_course_id,
            "day_of_week": "Friday",
            "start_time": "14:00",
            "end_time": "15:30",
            "room_number": "Lab-301",
        },
    )
    assert create_res.status_code == 201
    slot_id = create_res.json()["id"]

    # Delete
    del_res = client.delete(f"/api/timetable/{slot_id}")
    assert del_res.status_code == 200

    # Verify not found
    get_res = client.get(f"/api/timetable/{slot_id}")
    assert get_res.status_code == 404


def test_view_timetable_html_page(client: TestClient):
    res = client.get("/timetable")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "Academic Lecture Timetable" in res.text
