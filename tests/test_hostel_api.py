"""Unit and integration test suite for Hostel & Residential Life Hall Management."""

from fastapi.testclient import TestClient


def test_create_hostel_block_and_duplicate_rejection(client: TestClient):
    payload = {
        "block_name": "Ramanujan Graduate Residence",
        "gender_type": "MALE",
        "total_rooms": 15,
        "warden_name": "Prof. S. Chandrasekhar",
        "warden_contact": "+91 94444 11223",
    }
    res = client.post("/api/hostel/blocks", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["id"] is not None
    assert data["block_name"] == "Ramanujan Graduate Residence"

    # Duplicate block name rejection
    dup_res = client.post("/api/hostel/blocks", json=payload)
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.json()["detail"]


def test_create_hostel_room_and_list(client: TestClient):
    # Fetch block ID
    blocks_res = client.get("/api/hostel/blocks")
    assert blocks_res.status_code == 200
    block_id = blocks_res.json()[0]["id"]

    # Create Room 101 (Single)
    res_single = client.post(
        "/api/hostel/rooms",
        json={
            "block_id": block_id,
            "room_number": "101",
            "room_type": "SINGLE",
            "capacity": 1,
            "floor": 1,
            "fee_per_semester": 1800.0,
        },
    )
    assert res_single.status_code == 201
    assert res_single.json()["room_number"] == "101"
    assert res_single.json()["capacity"] == 1

    # Duplicate room number in same block rejected
    dup_res = client.post(
        "/api/hostel/rooms",
        json={
            "block_id": block_id,
            "room_number": "101",
            "room_type": "DOUBLE",
            "capacity": 2,
            "floor": 1,
            "fee_per_semester": 1200.0,
        },
    )
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.json()["detail"]


def test_allocate_room_and_occupancy_increment(client: TestClient):
    # 1. Enroll student
    student_res = client.post(
        "/api/students",
        json={
            "first_name": "Homi",
            "last_name": "Bhabha",
            "email": "homi.bhabha.hostel@institute.edu",
            "department_id": 1,
            "dob": "2003-10-30",
            "gender": "Male",
        },
    )
    assert student_res.status_code == 201
    student_id = student_res.json()["id"]

    # 2. Get Single Room 101
    rooms = client.get("/api/hostel/rooms").json()
    room_101 = next(r for r in rooms if r["room_number"] == "101")
    room_id = room_101["id"]

    # 3. Allocate bed
    alloc_res = client.post(
        "/api/hostel/allocate",
        json={
            "room_id": room_id,
            "student_id": student_id,
            "academic_year": "2026-2027",
            "check_in_date": "2026-10-10",
            "remarks": "Assigned key and locker card",
        },
    )
    assert alloc_res.status_code == 201
    alloc_data = alloc_res.json()
    assert alloc_data["status"] == "ACTIVE"
    assert alloc_data["room_id"] == room_id
    assert alloc_data["student_id"] == student_id

    # 4. Verify room occupancy is 1 and status transitioned to FULL
    updated_room = client.get("/api/hostel/rooms").json()
    r = next(item for item in updated_room if item["id"] == room_id)
    assert r["current_occupancy"] == 1
    assert r["status"] == "FULL"


def test_prevent_double_allocation_and_full_room(client: TestClient):
    # Retrieve student and room from previous test
    students = client.get("/api/students").json()
    homi = next(s for s in students if s["email"] == "homi.bhabha.hostel@institute.edu")
    rooms = client.get("/api/hostel/rooms").json()
    room_101 = next(r for r in rooms if r["room_number"] == "101")

    # Attempt to allocate another room to Homi in same academic year
    dup_student_alloc = client.post(
        "/api/hostel/allocate",
        json={
            "room_id": room_101["id"],
            "student_id": homi["id"],
            "academic_year": "2026-2027",
            "check_in_date": "2026-10-10",
        },
    )
    assert dup_student_alloc.status_code == 400
    detail = dup_student_alloc.json()["detail"]
    assert "full capacity" in detail or "already has an active" in detail


def test_checkout_room_and_occupancy_decrement(client: TestClient):
    # Fetch active allocations
    allocs_res = client.get("/api/hostel/allocations?status=ACTIVE")
    assert allocs_res.status_code == 200
    allocs = allocs_res.json()
    assert len(allocs) >= 1
    alloc = allocs[0]
    alloc_id = alloc["id"]
    room_id = alloc["room_id"]

    # Process checkout
    co_res = client.post(
        f"/api/hostel/checkout/{alloc_id}",
        json={"check_out_date": "2026-10-15", "remarks": "Clearance completed"},
    )
    assert co_res.status_code == 200
    assert co_res.json()["status"] == "CHECKED_OUT"

    # Verify room is now AVAILABLE with occupancy 0
    updated_rooms = client.get("/api/hostel/rooms").json()
    target_room = next(r for r in updated_rooms if r["id"] == room_id)
    assert target_room["current_occupancy"] == 0
    assert target_room["status"] == "AVAILABLE"


def test_hostel_stats_and_html_view(client: TestClient):
    stats_res = client.get("/api/hostel/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_blocks"] >= 1
    assert stats["total_rooms"] >= 1
    assert stats["total_beds"] >= 1

    # Test SSR HTML Page
    html_res = client.get("/hostel")
    assert html_res.status_code == 200
    has_title = (
        "Hostel &amp; Residential Life" in html_res.text
        or "Hostel & Residential Life" in html_res.text
    )
    assert has_title
    assert "Ramanujan Graduate Residence" in html_res.text
