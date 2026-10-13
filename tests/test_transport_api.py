"""Unit and integration test suite for Campus Transport Fleet & Transit Logistics."""

from fastapi.testclient import TestClient


def test_create_transport_route_and_validation(client: TestClient):
    # Success
    res = client.post(
        "/api/transport/routes",
        json={
            "route_name": "Route 101 - North Campus Express",
            "source": "City Central Metro Station",
            "destination": "Main Institute Gate 1",
            "total_stops": 8,
            "fare_per_semester": 4500.0,
            "status": "ACTIVE",
        },
    )
    assert res.status_code == 201
    route = res.json()
    assert route["id"] is not None
    assert route["route_name"] == "Route 101 - North Campus Express"
    assert route["fare_per_semester"] == 4500.0

    # Negative validation: duplicate route name
    res_dup = client.post(
        "/api/transport/routes",
        json={
            "route_name": "Route 101 - North Campus Express",
            "source": "City Central Metro Station",
            "destination": "Main Institute Gate 1",
            "total_stops": 8,
            "fare_per_semester": 4500.0,
            "status": "ACTIVE",
        },
    )
    assert res_dup.status_code == 400


def test_create_transport_vehicle_and_duplicate_number(client: TestClient):
    # 1. Fetch route
    routes = client.get("/api/transport/routes").json()
    route_id = routes[0]["id"]

    # 2. Register vehicle
    res = client.post(
        "/api/transport/vehicles",
        json={
            "route_id": route_id,
            "vehicle_number": "KA-01-EQ-9876",
            "driver_name": "Rajesh Sharma",
            "driver_phone": "+91-9876543210",
            "capacity": 45,
            "status": "ACTIVE",
        },
    )
    assert res.status_code == 201
    veh = res.json()
    assert veh["vehicle_number"] == "KA-01-EQ-9876"
    assert veh["capacity"] == 45

    # 3. Duplicate vehicle rejection
    res_dup = client.post(
        "/api/transport/vehicles",
        json={
            "route_id": route_id,
            "vehicle_number": "KA-01-EQ-9876",
            "driver_name": "Suresh Kumar",
            "driver_phone": "+91-9876543211",
            "capacity": 45,
            "status": "ACTIVE",
        },
    )
    assert res_dup.status_code == 400


def test_issue_transit_pass_success(client: TestClient):
    # 1. Enroll student
    student_res = client.post(
        "/api/students",
        json={
            "first_name": "Kavita",
            "last_name": "Krishnamurthy",
            "email": "kavita.transit@institute.edu",
            "department_id": 1,
            "dob": "2003-05-14",
            "gender": "Female",
        },
    )
    assert student_res.status_code == 201
    student_id = student_res.json()["id"]

    # 2. Get route
    routes = client.get("/api/transport/routes").json()
    route_id = routes[0]["id"]

    # 3. Issue transit pass
    res = client.post(
        "/api/transport/passes",
        json={
            "student_id": student_id,
            "route_id": route_id,
            "pickup_stop": "Indiranagar 100ft Road",
            "academic_year": "2026-2027",
            "valid_until": "2027-05-31",
        },
    )
    assert res.status_code == 201
    pass_data = res.json()
    assert pass_data["pass_number"].startswith("PASS-2026-")
    assert pass_data["status"] == "ACTIVE"
    assert pass_data["pickup_stop"] == "Indiranagar 100ft Road"


def test_prevent_duplicate_active_pass_same_year(client: TestClient):
    # Get existing student with pass
    passes = client.get("/api/transport/passes").json()
    assert len(passes) >= 1
    existing_pass = passes[0]

    # Attempt to issue another pass to the same student in same year
    res = client.post(
        "/api/transport/passes",
        json={
            "student_id": existing_pass["student_id"],
            "route_id": existing_pass["route_id"],
            "pickup_stop": "Another Stop",
            "academic_year": existing_pass["academic_year"],
            "valid_until": "2027-05-31",
        },
    )
    assert res.status_code == 400
    assert "already has an active transit pass" in res.json()["detail"]


def test_cancel_transit_pass(client: TestClient):
    passes = client.get("/api/transport/passes").json()
    pass_id = passes[0]["id"]

    res = client.put(f"/api/transport/passes/{pass_id}/cancel")
    assert res.status_code == 200

    # Verify pass list filter
    cancelled = client.get("/api/transport/passes?status=CANCELLED").json()
    assert any(p["id"] == pass_id for p in cancelled)


def test_transport_stats_and_telemetry(client: TestClient):
    res = client.get("/api/transport/stats")
    assert res.status_code == 200
    stats = res.json()
    assert stats["total_routes"] >= 1
    assert stats["active_routes"] >= 1
    assert stats["total_vehicles"] >= 1
    assert stats["total_capacity"] >= 45
    assert "fleet_occupancy_pct" in stats


def test_view_transport_html_page(client: TestClient):
    res = client.get("/transport")
    assert res.status_code == 200
    html = res.text
    assert (
        "Campus Transport &amp; Fleet Logistics" in html
        or "Campus Transport & Fleet Logistics" in html
    )
    assert "Route 101 - North Campus Express" in html
    assert "modal-add-route" in html
    assert "modal-add-vehicle" in html
    assert "modal-issue-pass" in html
