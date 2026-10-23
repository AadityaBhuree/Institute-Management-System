"""Unit and integration test suite for Campus Events, Seminars & Symposium Hub."""

from fastapi.testclient import TestClient


def test_create_event_success_and_validation(client: TestClient):
    # 1. Create a valid event
    res = client.post(
        "/api/events",
        json={
            "title": "International Quantum Computing Symposium 2026",
            "category": "SYMPOSIUM",
            "department_id": 1,
            "venue": "Newton Lecture Hall 1",
            "event_date": "2026-11-20",
            "start_time": "09:00",
            "end_time": "17:00",
            "max_capacity": 150,
            "registration_fee": 0.0,
            "status": "UPCOMING",
            "description": "Exploration of quantum supremacy, NISQ algorithms, and Qiskit pipelines.",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["id"] is not None
    assert data["event_code"].startswith("EVT-2026-")
    assert data["title"] == "International Quantum Computing Symposium 2026"
    assert data["category"] == "SYMPOSIUM"
    assert data["registered_count"] == 0
    assert data["available_seats"] == 150


def test_event_time_range_rejection(client: TestClient):
    # Invalid time ordering: start_time >= end_time
    res = client.post(
        "/api/events",
        json={
            "title": "Faulty Schedule Workshop",
            "category": "WORKSHOP",
            "department_id": 1,
            "venue": "Lab B",
            "event_date": "2026-11-25",
            "start_time": "18:00",
            "end_time": "09:00",
            "max_capacity": 50,
            "registration_fee": 0.0,
            "status": "UPCOMING",
        },
    )
    assert res.status_code == 400
    assert "Start time (18:00) must be earlier than end time (09:00)" in res.json()["detail"]


def test_list_events_and_filtering(client: TestClient):
    # Create distinct category event
    client.post(
        "/api/events",
        json={
            "title": "Global Cyber Defense Hackathon",
            "category": "HACKATHON",
            "department_id": 1,
            "venue": "Security War Room",
            "event_date": "2026-12-05",
            "start_time": "08:00",
            "end_time": "20:00",
            "max_capacity": 80,
            "registration_fee": 0.0,
            "status": "UPCOMING",
        },
    )

    # Filter by category
    res_hack = client.get("/api/events?category=HACKATHON")
    assert res_hack.status_code == 200
    hacks = res_hack.json()
    assert any(h["category"] == "HACKATHON" for h in hacks)

    # Filter by search
    res_search = client.get("/api/events?search=Quantum")
    assert res_search.status_code == 200
    results = res_search.json()
    assert any("Quantum" in e["title"] for e in results)


def test_get_event_by_id_and_404(client: TestClient):
    events = client.get("/api/events").json()
    assert len(events) > 0
    event_id = events[0]["id"]

    res = client.get(f"/api/events/{event_id}")
    assert res.status_code == 200
    assert res.json()["id"] == event_id

    # Non-existent
    res_404 = client.get("/api/events/999999")
    assert res_404.status_code == 404


def test_update_event_status_lifecycle(client: TestClient):
    res_create = client.post(
        "/api/events",
        json={
            "title": "Microservices In Practice Workshop",
            "category": "WORKSHOP",
            "department_id": 1,
            "venue": "Hall C",
            "event_date": "2026-11-28",
            "start_time": "10:00",
            "end_time": "15:00",
            "max_capacity": 60,
            "status": "UPCOMING",
        },
    )
    assert res_create.status_code == 201
    evt_id = res_create.json()["id"]

    # Transition to ACTIVE
    res_act = client.put(f"/api/events/{evt_id}/status", json={"status": "ACTIVE"})
    assert res_act.status_code == 200
    assert res_act.json()["status"] == "ACTIVE"

    # Transition to COMPLETED
    res_comp = client.put(f"/api/events/{evt_id}/status", json={"status": "COMPLETED"})
    assert res_comp.status_code == 200
    assert res_comp.json()["status"] == "COMPLETED"


def test_register_student_for_event_success(client: TestClient):
    # 1. Enroll student
    student_res = client.post(
        "/api/students",
        json={
            "first_name": "Rohan",
            "last_name": "Mehta",
            "email": "rohan.events@institute.edu",
            "department_id": 1,
            "dob": "2003-08-22",
            "gender": "Male",
        },
    )
    assert student_res.status_code == 201
    student_id = student_res.json()["id"]

    # 2. Create Event
    evt_res = client.post(
        "/api/events",
        json={
            "title": "AI Alignment & Ethics Seminar",
            "category": "SEMINAR",
            "department_id": 1,
            "venue": "Seminar Hall 4",
            "event_date": "2026-12-10",
            "start_time": "11:00",
            "end_time": "13:00",
            "max_capacity": 50,
            "status": "UPCOMING",
        },
    )
    assert evt_res.status_code == 201
    evt_id = evt_res.json()["id"]

    # 3. Register Student
    reg_res = client.post(
        "/api/events/register",
        json={"event_id": evt_id, "student_id": student_id},
    )
    assert reg_res.status_code == 201
    reg = reg_res.json()
    assert reg["id"] is not None
    assert reg["registration_number"].startswith(f"REG-EVT-{evt_id:03d}-")
    assert reg["status"] == "REGISTERED"
    assert reg["certificate_issued"] == 0
    assert reg["student_name"] == "Rohan Mehta"

    # 4. Check available seats decremented
    evt_after = client.get(f"/api/events/{evt_id}").json()
    assert evt_after["registered_count"] == 1
    assert evt_after["available_seats"] == 49


def test_prevent_duplicate_event_registration(client: TestClient):
    # 1. Enroll student
    student_res = client.post(
        "/api/students",
        json={
            "first_name": "Sneha",
            "last_name": "Patil",
            "email": "sneha.events@institute.edu",
            "department_id": 1,
            "dob": "2004-01-11",
            "gender": "Female",
        },
    )
    student_id = student_res.json()["id"]

    # 2. Create event
    evt_id = client.post(
        "/api/events",
        json={
            "title": "Cloud Native Architecture Seminar",
            "category": "SEMINAR",
            "department_id": 1,
            "venue": "Hall D",
            "event_date": "2026-12-15",
            "start_time": "14:00",
            "end_time": "16:00",
            "max_capacity": 40,
        },
    ).json()["id"]

    # 3. First registration -> 201
    res1 = client.post(
        "/api/events/register",
        json={"event_id": evt_id, "student_id": student_id},
    )
    assert res1.status_code == 201

    # 4. Duplicate registration -> 400
    res2 = client.post(
        "/api/events/register",
        json={"event_id": evt_id, "student_id": student_id},
    )
    assert res2.status_code == 400
    assert "already registered" in res2.json()["detail"]


def test_event_capacity_enforcement(client: TestClient):
    # 1. Enroll 2 students
    s1 = client.post(
        "/api/students",
        json={
            "first_name": "Aman",
            "last_name": "Verma",
            "email": "aman.cap1@institute.edu",
            "department_id": 1,
            "dob": "2003-03-03",
            "gender": "Male",
        },
    ).json()["id"]
    s2 = client.post(
        "/api/students",
        json={
            "first_name": "Tina",
            "last_name": "Roy",
            "email": "tina.cap2@institute.edu",
            "department_id": 1,
            "dob": "2003-04-04",
            "gender": "Female",
        },
    ).json()["id"]

    # 2. Event with max_capacity = 1
    evt_id = client.post(
        "/api/events",
        json={
            "title": "VIP Masterclass: Deep Reinforcement Learning",
            "category": "WORKSHOP",
            "department_id": 1,
            "venue": "Private Lab 1",
            "event_date": "2026-12-22",
            "start_time": "10:00",
            "end_time": "12:00",
            "max_capacity": 1,
        },
    ).json()["id"]

    # 3. First student fills the only seat
    res_s1 = client.post("/api/events/register", json={"event_id": evt_id, "student_id": s1})
    assert res_s1.status_code == 201

    # 4. Second student rejected due to capacity limit
    res_s2 = client.post("/api/events/register", json={"event_id": evt_id, "student_id": s2})
    assert res_s2.status_code == 400
    assert "reached its maximum capacity" in res_s2.json()["detail"]


def test_update_registration_status_and_certificate(client: TestClient):
    # 1. Fetch any registration
    events = client.get("/api/events").json()
    assert len(events) > 0
    evt_id = events[0]["id"]
    regs = client.get(f"/api/events/{evt_id}/registrations").json()

    if not regs:
        # Create student and register
        s_id = client.post(
            "/api/students",
            json={
                "first_name": "Vikram",
                "last_name": "Rathore",
                "email": "vikram.cert@institute.edu",
                "department_id": 1,
                "dob": "2002-12-12",
                "gender": "Male",
            },
        ).json()["id"]
        reg = client.post(
            "/api/events/register",
            json={"event_id": evt_id, "student_id": s_id},
        ).json()
    else:
        reg = regs[0]

    reg_id = reg["id"]

    # 2. Mark attended and issue certificate
    res_att = client.put(
        f"/api/events/registrations/{reg_id}/status",
        json={"status": "ATTENDED", "certificate_issued": 1},
    )
    assert res_att.status_code == 200
    updated = res_att.json()
    assert updated["status"] == "ATTENDED"
    assert updated["certificate_issued"] == 1
    assert updated["attendance_marked_at"] is not None


def test_event_stats_and_telemetry(client: TestClient):
    res = client.get("/api/events/stats")
    assert res.status_code == 200
    stats = res.json()
    assert "total_events" in stats
    assert "upcoming_events" in stats
    assert "total_registrations" in stats
    assert "total_attended" in stats
    assert "total_certificates_issued" in stats
    assert stats["total_events"] >= 1


def test_view_events_html_page(client: TestClient):
    res = client.get("/events")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "Campus Events &amp; Symposiums" in res.text or "Campus Events & Symposiums" in res.text
    assert "Events Catalog" in res.text
