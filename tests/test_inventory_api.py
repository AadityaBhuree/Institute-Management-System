"""Comprehensive Automated Pytest Suite for Campus Assets, Lab Equipment & Inventory Circulation Hub."""

from datetime import date, timedelta

from fastapi.testclient import TestClient


def _get_or_create_context(client: TestClient) -> dict:
    """Helper to ensure department, student, and faculty exist for inventory testing."""
    # Department 1 is default from init_database
    dept_id = 1

    # Enroll student
    s_res = client.post(
        "/api/students",
        json={
            "first_name": "Homi",
            "last_name": "Bhabha",
            "email": "homi.bhabha.asset@institute.edu",
            "department_id": dept_id,
            "dob": "2003-10-30",
            "gender": "Male",
        },
    )
    if s_res.status_code == 201:
        student_id = s_res.json()["id"]
    else:
        # Fetch existing
        s_list = client.get("/api/students?search=Bhabha").json()
        student_id = s_list[0]["id"]

    # Register faculty
    f_res = client.post(
        "/api/faculty",
        json={
            "first_name": "Vikram",
            "last_name": "Sarabhai",
            "email": "vikram.sarabhai.asset@institute.edu",
            "department_id": dept_id,
            "designation": "Professor & Dean",
            "status": "ACTIVE",
        },
    )
    if f_res.status_code == 201:
        faculty_id = f_res.json()["id"]
    else:
        f_list = client.get("/api/faculty?search=Vikram").json()
        faculty_id = f_list[0]["id"]

    return {
        "dept_id": dept_id,
        "student_id": student_id,
        "faculty_id": faculty_id,
    }


def test_create_asset_success_and_tag_generation(client: TestClient):
    """Verify asset registration, tag generation (AST-{DEPT}-YYYY-XXXX), and default available status."""
    ctx = _get_or_create_context(client)
    today_str = date.today().isoformat()
    payload = {
        "name": "Rigol 100MHz Digital Oscilloscope",
        "category": "LAB_EQUIPMENT",
        "department_id": ctx["dept_id"],
        "lab_room": "Circuits Lab 201",
        "serial_number": "SN-RIG-10023",
        "model_number": "DS1104Z",
        "manufacturer": "Rigol Technologies",
        "purchase_date": today_str,
        "purchase_cost": 450.00,
        "warranty_expiry": (date.today() + timedelta(days=365)).isoformat(),
        "status": "AVAILABLE",
    }
    res = client.post("/api/inventory/assets", json=payload)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["name"] == "Rigol 100MHz Digital Oscilloscope"
    assert data["status"] == "AVAILABLE"
    assert "AST-" in data["asset_tag"]
    assert data["department_name"] is not None


def test_create_asset_duplicate_serial_rejected(client: TestClient):
    """Verify unique serial number constraint triggers HTTP 400."""
    ctx = _get_or_create_context(client)
    today_str = date.today().isoformat()
    payload = {
        "name": "Keysight Multimeter",
        "category": "LAB_EQUIPMENT",
        "department_id": ctx["dept_id"],
        "lab_room": "Room 101",
        "serial_number": "SN-UNIQUE-999",
        "purchase_date": today_str,
        "purchase_cost": 250.00,
        "status": "AVAILABLE",
    }
    res1 = client.post("/api/inventory/assets", json=payload)
    assert res1.status_code == 201

    # Attempt duplicate serial
    res2 = client.post("/api/inventory/assets", json=payload)
    assert res2.status_code == 400
    assert "serial number" in res2.json()["detail"].lower()


def test_list_assets_and_filtering(client: TestClient):
    """Verify asset listing with category, status, and search filters."""
    ctx = _get_or_create_context(client)
    today_str = date.today().isoformat()
    client.post(
        "/api/inventory/assets",
        json={
            "name": "NVIDIA Jetson AGX Orin DevKit",
            "category": "COMPUTING",
            "department_id": ctx["dept_id"],
            "lab_room": "Embedded AI Lab",
            "serial_number": "SN-NV-JET-11",
            "purchase_date": today_str,
            "purchase_cost": 1999.00,
            "status": "AVAILABLE",
        },
    )
    client.post(
        "/api/inventory/assets",
        json={
            "name": "Laser Interferometer Kit",
            "category": "RESEARCH_INSTRUMENT",
            "department_id": ctx["dept_id"],
            "lab_room": "Optics Lab 305",
            "serial_number": "SN-OPT-INT-22",
            "purchase_date": today_str,
            "purchase_cost": 4200.00,
            "status": "AVAILABLE",
        },
    )

    # Filter category
    res_cat = client.get("/api/inventory/assets?category=COMPUTING")
    assert res_cat.status_code == 200
    items = res_cat.json()
    assert len(items) >= 1
    assert any(i["category"] == "COMPUTING" for i in items)

    # Search filter
    res_srch = client.get("/api/inventory/assets?search=Interferometer")
    assert res_srch.status_code == 200
    assert len(res_srch.json()) >= 1


def test_get_asset_by_id_and_404(client: TestClient):
    """Verify retrieval of detailed asset profile and 404 on missing record."""
    ctx = _get_or_create_context(client)
    today_str = date.today().isoformat()
    res = client.post(
        "/api/inventory/assets",
        json={
            "name": "Spectrum Analyzer 3GHz",
            "category": "LAB_EQUIPMENT",
            "department_id": ctx["dept_id"],
            "lab_room": "RF Lab 402",
            "serial_number": "SN-SPEC-3G",
            "purchase_date": today_str,
            "purchase_cost": 3100.00,
            "status": "AVAILABLE",
        },
    )
    asset_id = res.json()["id"]

    res_get = client.get(f"/api/inventory/assets/{asset_id}")
    assert res_get.status_code == 200
    assert res_get.json()["name"] == "Spectrum Analyzer 3GHz"

    # Non-existent asset
    res_404 = client.get("/api/inventory/assets/999999")
    assert res_404.status_code == 404


def test_update_asset_metadata(client: TestClient):
    """Verify updating asset room, model, and specifications."""
    ctx = _get_or_create_context(client)
    today_str = date.today().isoformat()
    res = client.post(
        "/api/inventory/assets",
        json={
            "name": "PicoScope 2000",
            "category": "LAB_EQUIPMENT",
            "department_id": ctx["dept_id"],
            "lab_room": "Old Lab 101",
            "purchase_date": today_str,
            "purchase_cost": 150.00,
            "status": "AVAILABLE",
        },
    )
    asset_id = res.json()["id"]

    update_payload = {
        "name": "PicoScope 2204A Ultra-Compact",
        "lab_room": "New Innovation Hub - Room 501",
        "model_number": "2204A",
    }
    res_up = client.put(f"/api/inventory/assets/{asset_id}", json=update_payload)
    assert res_up.status_code == 200
    assert res_up.json()["name"] == "PicoScope 2204A Ultra-Compact"
    assert res_up.json()["lab_room"] == "New Innovation Hub - Room 501"


def test_checkout_asset_success(client: TestClient):
    """Verify checking out available equipment to an active student updates asset status to CHECKED_OUT."""
    ctx = _get_or_create_context(client)
    today_str = date.today().isoformat()
    due_str = (date.today() + timedelta(days=7)).isoformat()

    res_asset = client.post(
        "/api/inventory/assets",
        json={
            "name": "Function Generator 25MHz",
            "category": "LAB_EQUIPMENT",
            "department_id": ctx["dept_id"],
            "lab_room": "Signals Lab",
            "serial_number": "SN-GEN-25M",
            "purchase_date": today_str,
            "purchase_cost": 320.00,
            "status": "AVAILABLE",
        },
    )
    asset_id = res_asset.json()["id"]

    chk_payload = {
        "asset_id": asset_id,
        "borrower_type": "STUDENT",
        "student_id": ctx["student_id"],
        "checkout_date": today_str,
        "due_date": due_str,
        "condition_out": "EXCELLENT",
        "notes": "Testing audio filter prototype.",
    }
    res_chk = client.post("/api/inventory/checkouts", json=chk_payload)
    assert res_chk.status_code == 201, res_chk.text
    chk_data = res_chk.json()
    assert "CHK-" in chk_data["checkout_code"]
    assert chk_data["status"] == "ACTIVE"
    assert chk_data["borrower_name"] is not None

    # Verify asset status flipped to CHECKED_OUT
    res_get = client.get(f"/api/inventory/assets/{asset_id}")
    assert res_get.json()["status"] == "CHECKED_OUT"


def test_prevent_checkout_unavailable_asset(client: TestClient):
    """Verify attempting to check out already checked out asset returns HTTP 400."""
    ctx = _get_or_create_context(client)
    today_str = date.today().isoformat()
    due_str = (date.today() + timedelta(days=7)).isoformat()

    res_asset = client.post(
        "/api/inventory/assets",
        json={
            "name": "High-Voltage Power Supply",
            "category": "LAB_EQUIPMENT",
            "department_id": ctx["dept_id"],
            "lab_room": "Power Lab",
            "serial_number": "SN-HV-PS-01",
            "purchase_date": today_str,
            "purchase_cost": 850.00,
            "status": "AVAILABLE",
        },
    )
    asset_id = res_asset.json()["id"]

    # First checkout
    client.post(
        "/api/inventory/checkouts",
        json={
            "asset_id": asset_id,
            "borrower_type": "STUDENT",
            "student_id": ctx["student_id"],
            "checkout_date": today_str,
            "due_date": due_str,
        },
    )

    # Second checkout on same asset
    res_double = client.post(
        "/api/inventory/checkouts",
        json={
            "asset_id": asset_id,
            "borrower_type": "FACULTY",
            "faculty_id": ctx["faculty_id"],
            "checkout_date": today_str,
            "due_date": due_str,
        },
    )
    assert res_double.status_code == 400
    assert "cannot be checked out" in res_double.json()["detail"].lower()


def test_checkout_invalid_due_date_rejected(client: TestClient):
    """Verify due date earlier than checkout date triggers HTTP 400."""
    ctx = _get_or_create_context(client)
    today_str = date.today().isoformat()
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()

    res_asset = client.post(
        "/api/inventory/assets",
        json={
            "name": "LCR Meter",
            "category": "LAB_EQUIPMENT",
            "department_id": ctx["dept_id"],
            "lab_room": "Electronics Lab",
            "purchase_date": today_str,
            "purchase_cost": 290.00,
            "status": "AVAILABLE",
        },
    )
    asset_id = res_asset.json()["id"]

    res = client.post(
        "/api/inventory/checkouts",
        json={
            "asset_id": asset_id,
            "borrower_type": "STUDENT",
            "student_id": ctx["student_id"],
            "checkout_date": today_str,
            "due_date": yesterday_str,
        },
    )
    assert res.status_code == 400
    assert "earlier than checkout date" in res.json()["detail"].lower()


def test_return_asset_clean_restores_available(client: TestClient):
    """Verify normal return in GOOD condition restores asset status to AVAILABLE."""
    ctx = _get_or_create_context(client)
    today_str = date.today().isoformat()
    due_str = (date.today() + timedelta(days=5)).isoformat()

    res_asset = client.post(
        "/api/inventory/assets",
        json={
            "name": "Thermal Imaging Camera",
            "category": "RESEARCH_INSTRUMENT",
            "department_id": ctx["dept_id"],
            "lab_room": "Diagnostics Lab",
            "serial_number": "SN-THM-991",
            "purchase_date": today_str,
            "purchase_cost": 1800.00,
            "status": "AVAILABLE",
        },
    )
    asset_id = res_asset.json()["id"]

    chk_res = client.post(
        "/api/inventory/checkouts",
        json={
            "asset_id": asset_id,
            "borrower_type": "FACULTY",
            "faculty_id": ctx["faculty_id"],
            "checkout_date": today_str,
            "due_date": due_str,
            "condition_out": "EXCELLENT",
        },
    )
    chk_id = chk_res.json()["id"]

    # Return
    ret_res = client.put(
        f"/api/inventory/checkouts/{chk_id}/return",
        json={
            "returned_date": today_str,
            "condition_in": "EXCELLENT",
            "notes": "Lens clean, battery fully recharged.",
        },
    )
    assert ret_res.status_code == 200
    assert ret_res.json()["status"] == "RETURNED"

    # Asset is back to AVAILABLE
    asset_get = client.get(f"/api/inventory/assets/{asset_id}")
    assert asset_get.json()["status"] == "AVAILABLE"


def test_return_asset_damaged_triggers_maintenance(client: TestClient):
    """Verify return with condition_in == 'DAMAGED' automatically moves asset to MAINTENANCE."""
    ctx = _get_or_create_context(client)
    today_str = date.today().isoformat()
    due_str = (date.today() + timedelta(days=5)).isoformat()

    res_asset = client.post(
        "/api/inventory/assets",
        json={
            "name": "Precision Optical Sensor Kit",
            "category": "RESEARCH_INSTRUMENT",
            "department_id": ctx["dept_id"],
            "lab_room": "Sensor Bay",
            "serial_number": "SN-OPT-SENS-77",
            "purchase_date": today_str,
            "purchase_cost": 950.00,
            "status": "AVAILABLE",
        },
    )
    asset_id = res_asset.json()["id"]

    chk_res = client.post(
        "/api/inventory/checkouts",
        json={
            "asset_id": asset_id,
            "borrower_type": "STUDENT",
            "student_id": ctx["student_id"],
            "checkout_date": today_str,
            "due_date": due_str,
        },
    )
    chk_id = chk_res.json()["id"]

    # Return as DAMAGED
    ret_res = client.put(
        f"/api/inventory/checkouts/{chk_id}/return",
        json={
            "returned_date": today_str,
            "condition_in": "DAMAGED",
            "notes": "Cracked casing and misaligned photodiode array.",
        },
    )
    assert ret_res.status_code == 200

    # Asset automatically routed to MAINTENANCE
    asset_get = client.get(f"/api/inventory/assets/{asset_id}")
    assert asset_get.json()["status"] == "MAINTENANCE"


def test_schedule_maintenance_success_and_lifecycle(client: TestClient):
    """Verify scheduling maintenance work orders, status updates, and restoration to service upon completion."""
    ctx = _get_or_create_context(client)
    today_str = date.today().isoformat()

    res_asset = client.post(
        "/api/inventory/assets",
        json={
            "name": "Ultrasonic Flaw Detector",
            "category": "LAB_EQUIPMENT",
            "department_id": ctx["dept_id"],
            "lab_room": "NDT Testing Lab",
            "purchase_date": today_str,
            "purchase_cost": 2200.00,
            "status": "AVAILABLE",
        },
    )
    asset_id = res_asset.json()["id"]

    # Schedule calibration
    m_res = client.post(
        "/api/inventory/maintenance",
        json={
            "asset_id": asset_id,
            "maintenance_type": "CALIBRATION",
            "scheduled_date": today_str,
            "technician_name": "NDT Calibration Specialist",
            "cost": 150.00,
            "status": "IN_PROGRESS",
            "resolution_notes": "Annual ISO-9001 calibration check.",
        },
    )
    assert m_res.status_code == 201
    m_data = m_res.json()
    assert "MNT-" in m_data["maintenance_code"]
    m_id = m_data["id"]

    # In progress flips asset to MAINTENANCE
    assert client.get(f"/api/inventory/assets/{asset_id}").json()["status"] == "MAINTENANCE"

    # Complete maintenance
    comp_res = client.put(
        f"/api/inventory/maintenance/{m_id}/status",
        json={
            "status": "COMPLETED",
            "completed_date": today_str,
            "cost": 150.00,
            "resolution_notes": "Calibration passed within 0.02% tolerance.",
        },
    )
    assert comp_res.status_code == 200
    assert comp_res.json()["status"] == "COMPLETED"

    # Asset restored to AVAILABLE
    assert client.get(f"/api/inventory/assets/{asset_id}").json()["status"] == "AVAILABLE"


def test_prevent_maintenance_on_checked_out_asset(client: TestClient):
    """Verify cannot book maintenance on equipment currently in borrower possession."""
    ctx = _get_or_create_context(client)
    today_str = date.today().isoformat()
    due_str = (date.today() + timedelta(days=7)).isoformat()

    res_asset = client.post(
        "/api/inventory/assets",
        json={
            "name": "Digital Multimeter Fluke 87V",
            "category": "LAB_EQUIPMENT",
            "department_id": ctx["dept_id"],
            "lab_room": "General Lab",
            "purchase_date": today_str,
            "purchase_cost": 480.00,
            "status": "AVAILABLE",
        },
    )
    asset_id = res_asset.json()["id"]

    client.post(
        "/api/inventory/checkouts",
        json={
            "asset_id": asset_id,
            "borrower_type": "STUDENT",
            "student_id": ctx["student_id"],
            "checkout_date": today_str,
            "due_date": due_str,
        },
    )

    res_maint = client.post(
        "/api/inventory/maintenance",
        json={
            "asset_id": asset_id,
            "maintenance_type": "REPAIR",
            "scheduled_date": today_str,
            "technician_name": "Lab Tech",
        },
    )
    assert res_maint.status_code == 400
    assert "currently checked out" in res_maint.json()["detail"].lower()


def test_inventory_stats_and_telemetry(client: TestClient):
    """Verify inventory telemetry calculates total count, valuation, loans, and maintenance correctly."""
    today_str = date.today().isoformat()
    client.post(
        "/api/inventory/assets",
        json={
            "name": "Test Asset A",
            "category": "LAB_EQUIPMENT",
            "purchase_date": today_str,
            "purchase_cost": 1000.00,
            "status": "AVAILABLE",
            "lab_room": "Lab 1",
        },
    )
    client.post(
        "/api/inventory/assets",
        json={
            "name": "Test Asset B",
            "category": "COMPUTING",
            "purchase_date": today_str,
            "purchase_cost": 2500.00,
            "status": "AVAILABLE",
            "lab_room": "Lab 2",
        },
    )

    res = client.get("/api/inventory/assets/stats")
    assert res.status_code == 200
    stats = res.json()
    assert stats["total_assets"] >= 2
    assert stats["total_valuation"] >= 3500.00
    assert "active_checkouts" in stats
    assert "in_maintenance" in stats
    assert "overdue_checkouts" in stats


def test_view_inventory_html_page(client: TestClient):
    """Verify SSR web route /inventory renders Glassmorphism layout and tabs without error."""
    res = client.get("/inventory")
    assert res.status_code == 200
    html = res.text
    assert (
        "Campus Assets &amp; Lab Equipment Hub" in html
        or "Campus Assets & Lab Equipment Hub" in html
    )
    assert "Equipment Registry" in html
    assert "Circulation Loans" in html
    assert "Maintenance &amp; Calibration" in html or "Maintenance & Calibration" in html
    assert "modal-register-asset" in html
    assert "modal-checkout-asset" in html
    assert "modal-return-asset" in html
    assert "modal-schedule-maintenance" in html
