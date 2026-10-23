"""Comprehensive Automated Pytest Suite for Campus Health, Student Clinic & Infirmary Hub."""

from datetime import date, timedelta

from fastapi.testclient import TestClient


def _get_or_create_context(client: TestClient) -> dict:
    """Helper to ensure department, student, and faculty exist for health center testing."""
    dept_id = 1

    # Enroll student
    s_res = client.post(
        "/api/students",
        json={
            "first_name": "Charaka",
            "last_name": "Ayur",
            "email": "charaka.health@institute.edu",
            "department_id": dept_id,
            "dob": "2003-05-15",
            "gender": "Male",
        },
    )
    if s_res.status_code == 201:
        student_id = s_res.json()["id"]
    else:
        s_list = client.get("/api/students?search=Charaka").json()
        student_id = s_list[0]["id"]

    # Register faculty
    f_res = client.post(
        "/api/faculty",
        json={
            "first_name": "Sushruta",
            "last_name": "Chikitsa",
            "email": "sushruta.health@institute.edu",
            "department_id": dept_id,
            "designation": "Professor of Surgery",
            "status": "ACTIVE",
        },
    )
    if f_res.status_code == 201:
        faculty_id = f_res.json()["id"]
    else:
        f_list = client.get("/api/faculty?search=Sushruta").json()
        faculty_id = f_list[0]["id"]

    return {
        "dept_id": dept_id,
        "student_id": student_id,
        "faculty_id": faculty_id,
    }


def test_create_dispensary_medicine_and_code_generation(client: TestClient):
    """Verify medicine batch creation with auto-generated code and low stock evaluation."""
    today_str = (date.today() + timedelta(days=365)).isoformat()
    payload = {
        "name": "Azithromycin 500mg",
        "category": "ANTIBIOTIC",
        "form": "TABLET",
        "stock_quantity": 80,
        "unit": "Tablets",
        "reorder_level": 20,
        "batch_number": "BATCH-AZI-101",
        "expiry_date": today_str,
    }
    res = client.post("/api/health-center/medicines", json=payload)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["name"] == "Azithromycin 500mg"
    assert "MED-STK-" in data["item_code"]
    assert data["is_low_stock"] is False
    assert data["stock_quantity"] == 80


def test_create_dispensary_medicine_duplicate_code_rejected(client: TestClient):
    """Verify unique medicine item_code constraint returns HTTP 400."""
    today_str = (date.today() + timedelta(days=365)).isoformat()
    payload = {
        "item_code": "MED-CUSTOM-DUP",
        "name": "Dextromethorphan Syrup",
        "category": "OTHER",
        "form": "SYRUP",
        "stock_quantity": 25,
        "unit": "Bottles",
        "reorder_level": 10,
        "batch_number": "BATCH-DXM-01",
        "expiry_date": today_str,
    }
    res1 = client.post("/api/health-center/medicines", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/health-center/medicines", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]


def test_update_dispensary_stock_and_low_stock_trigger(client: TestClient):
    """Verify inventory stock updates, low stock flags, and prevention of negative stock."""
    today_str = (date.today() + timedelta(days=365)).isoformat()
    med_res = client.post(
        "/api/health-center/medicines",
        json={
            "name": "Diclofenac Gel",
            "category": "ANALGESIC",
            "form": "OINTMENT",
            "stock_quantity": 30,
            "unit": "Tubes",
            "reorder_level": 15,
            "batch_number": "BATCH-DIC-05",
            "expiry_date": today_str,
        },
    )
    assert med_res.status_code == 201
    med_id = med_res.json()["id"]

    # Restock +20
    restock_res = client.put(
        f"/api/health-center/medicines/{med_id}/stock",
        json={"quantity_change": 20, "reason": "Supplier shipment"},
    )
    assert restock_res.status_code == 200
    assert restock_res.json()["stock_quantity"] == 50
    assert restock_res.json()["is_low_stock"] is False

    # Dispense -40 (stock drops to 10 <= reorder 15 -> low stock!)
    dispense_res = client.put(
        f"/api/health-center/medicines/{med_id}/stock",
        json={"quantity_change": -40, "reason": "Clinical dispensation"},
    )
    assert dispense_res.status_code == 200
    assert dispense_res.json()["stock_quantity"] == 10
    assert dispense_res.json()["is_low_stock"] is True

    # Attempt to decrement by 20 when only 10 available -> HTTP 400
    invalid_res = client.put(
        f"/api/health-center/medicines/{med_id}/stock",
        json={"quantity_change": -20, "reason": "Excessive deduction"},
    )
    assert invalid_res.status_code == 400
    assert "Cannot reduce stock" in invalid_res.json()["detail"]


def test_create_and_update_health_profile_student(client: TestClient):
    """Verify student health profile registration and upsert behavior."""
    ctx = _get_or_create_context(client)
    payload = {
        "person_type": "STUDENT",
        "student_id": ctx["student_id"],
        "blood_group": "B+",
        "allergies": "Amoxicillin, Pollen",
        "chronic_conditions": "None",
        "emergency_contact_name": "Arun Ayur",
        "emergency_contact_phone": "+91 99887 76655",
        "emergency_contact_relation": "Father",
        "insurance_provider": "Care Health Student Plan",
        "insurance_policy_number": "CARE-2026-9921",
    }
    res = client.post("/api/health-center/profiles", json=payload)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["person_type"] == "STUDENT"
    assert data["blood_group"] == "B+"
    assert data["allergies"] == "Amoxicillin, Pollen"
    assert data["person_name"] is not None

    # Upsert: update allergies
    payload["allergies"] = "Amoxicillin only"
    res_update = client.post("/api/health-center/profiles", json=payload)
    assert res_update.status_code == 201
    assert res_update.json()["allergies"] == "Amoxicillin only"
    assert res_update.json()["id"] == data["id"]

    # Fetch by person
    fetch_res = client.get(f"/api/health-center/profiles/student/{ctx['student_id']}")
    assert fetch_res.status_code == 200
    assert fetch_res.json()["allergies"] == "Amoxicillin only"


def test_create_health_profile_faculty(client: TestClient):
    """Verify faculty health profile creation."""
    ctx = _get_or_create_context(client)
    payload = {
        "person_type": "FACULTY",
        "faculty_id": ctx["faculty_id"],
        "blood_group": "O-",
        "allergies": "None",
        "chronic_conditions": "Mild Hypertension",
        "emergency_contact_name": "Radha Chikitsa",
        "emergency_contact_phone": "+91 98765 12345",
        "emergency_contact_relation": "Spouse",
    }
    res = client.post("/api/health-center/profiles", json=payload)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["person_type"] == "FACULTY"
    assert data["blood_group"] == "O-"
    assert data["chronic_conditions"] == "Mild Hypertension"


def test_create_health_profile_validation_errors(client: TestClient):
    """Verify validation: missing matching ID or nonexistent entity rejected."""
    # Student type without student_id
    res1 = client.post(
        "/api/health-center/profiles",
        json={
            "person_type": "STUDENT",
            "blood_group": "A+",
            "emergency_contact_name": "Parent",
            "emergency_contact_phone": "1234567",
        },
    )
    assert res1.status_code == 422

    # Nonexistent student id
    res2 = client.post(
        "/api/health-center/profiles",
        json={
            "person_type": "STUDENT",
            "student_id": 999999,
            "blood_group": "A+",
            "emergency_contact_name": "Parent",
            "emergency_contact_phone": "1234567",
        },
    )
    assert res2.status_code == 400
    assert "does not exist" in res2.json()["detail"]


def test_create_medical_encounter_with_prescriptions_and_stock_decrement(client: TestClient):
    """Verify clinical consultation logging, vital signs recording, and automatic dispensary stock decrement."""
    ctx = _get_or_create_context(client)
    today_str = date.today().isoformat()

    # Create medicine with 50 units
    med_res = client.post(
        "/api/health-center/medicines",
        json={
            "name": "Cough Relief Expectorant",
            "category": "OTHER",
            "form": "SYRUP",
            "stock_quantity": 50,
            "unit": "Bottles",
            "reorder_level": 10,
            "batch_number": "BATCH-EXP-99",
            "expiry_date": (date.today() + timedelta(days=200)).isoformat(),
        },
    )
    assert med_res.status_code == 201
    med_id = med_res.json()["id"]

    encounter_payload = {
        "patient_type": "STUDENT",
        "student_id": ctx["student_id"],
        "visit_date": today_str,
        "doctor_name": "Dr. Sarah Johnson, MD",
        "chief_complaint": "Persistent dry cough and mild fever",
        "symptoms": "Noisy breathing, throat tickle, temp 100.2F",
        "diagnosis": "Acute Bronchitis (Mild)",
        "blood_pressure": "116/74",
        "pulse_bpm": 80,
        "temperature_f": 100.2,
        "triage_severity": "NORMAL",
        "treatment_given": "Hydration advice, oral expectorant dispensed",
        "follow_up_date": (date.today() + timedelta(days=3)).isoformat(),
        "prescriptions": [
            {
                "medicine_id": med_id,
                "medicine_name": "Cough Relief Expectorant",
                "dosage": "10ml",
                "frequency": "Twice daily after meals",
                "duration_days": 5,
                "quantity_dispensed": 2,
            }
        ],
    }

    res = client.post("/api/health-center/encounters", json=encounter_payload)
    assert res.status_code == 201, res.text
    data = res.json()
    assert "ENC-" in data["encounter_code"]
    assert data["chief_complaint"] == "Persistent dry cough and mild fever"
    assert len(data["prescriptions"]) == 1
    assert data["prescriptions"][0]["quantity_dispensed"] == 2

    # Verify dispensary medicine stock decremented by 2 (50 -> 48)
    med_check = client.get(f"/api/health-center/medicines/{med_id}").json()
    assert med_check["stock_quantity"] == 48


def test_create_medical_encounter_insufficient_stock_rejected(client: TestClient):
    """Verify encounter rejected if requested prescription quantity exceeds dispensary inventory."""
    ctx = _get_or_create_context(client)
    today_str = date.today().isoformat()

    med_res = client.post(
        "/api/health-center/medicines",
        json={
            "name": "Rare Antidote Vial",
            "category": "OTHER",
            "form": "INJECTION",
            "stock_quantity": 2,
            "unit": "Vials",
            "reorder_level": 1,
            "batch_number": "BATCH-RARE-01",
            "expiry_date": (date.today() + timedelta(days=100)).isoformat(),
        },
    )
    med_id = med_res.json()["id"]

    encounter_payload = {
        "patient_type": "STUDENT",
        "student_id": ctx["student_id"],
        "visit_date": today_str,
        "doctor_name": "Dr. Sarah Johnson, MD",
        "chief_complaint": "Toxic allergen reaction",
        "diagnosis": "Systemic Allergy",
        "triage_severity": "EMERGENCY",
        "prescriptions": [
            {
                "medicine_id": med_id,
                "medicine_name": "Rare Antidote Vial",
                "dosage": "1 vial",
                "frequency": "Stat",
                "duration_days": 1,
                "quantity_dispensed": 5,  # Only 2 available!
            }
        ],
    }

    res = client.post("/api/health-center/encounters", json=encounter_payload)
    assert res.status_code == 400
    assert "Insufficient stock" in res.json()["detail"]


def test_get_encounter_by_id_and_404(client: TestClient):
    """Verify retrieving encounter details and handling of nonexistent ID."""
    ctx = _get_or_create_context(client)
    res = client.post(
        "/api/health-center/encounters",
        json={
            "patient_type": "FACULTY",
            "faculty_id": ctx["faculty_id"],
            "visit_date": date.today().isoformat(),
            "doctor_name": "Dr. Sarah Johnson, MD",
            "chief_complaint": "Tension headache",
            "diagnosis": "Tension Cephalea",
            "triage_severity": "NORMAL",
            "prescriptions": [],
        },
    )
    enc_id = res.json()["id"]

    get_res = client.get(f"/api/health-center/encounters/{enc_id}")
    assert get_res.status_code == 200
    assert get_res.json()["patient_type"] == "FACULTY"

    # Nonexistent
    assert client.get("/api/health-center/encounters/99999").status_code == 404


def test_list_encounters_and_filtering(client: TestClient):
    """Verify listing encounters with triage and patient_type filters."""
    res_student = client.get("/api/health-center/encounters?patient_type=STUDENT")
    assert res_student.status_code == 200
    for e in res_student.json():
        assert e["patient_type"] == "STUDENT"

    res_emergency = client.get("/api/health-center/encounters?triage_severity=EMERGENCY")
    assert res_emergency.status_code == 200
    for e in res_emergency.json():
        assert e["triage_severity"] == "EMERGENCY"


def test_issue_medical_certificate_and_code_generation(client: TestClient):
    """Verify medical sick leave certificate issuance with sequential number MED-YYYY-XXXX."""
    ctx = _get_or_create_context(client)
    today = date.today()

    enc_res = client.post(
        "/api/health-center/encounters",
        json={
            "patient_type": "STUDENT",
            "student_id": ctx["student_id"],
            "visit_date": today.isoformat(),
            "doctor_name": "Dr. Sarah Johnson, MD",
            "chief_complaint": "Gastroenteritis with dehydration",
            "diagnosis": "Acute Gastroenteritis",
            "triage_severity": "URGENT",
            "prescriptions": [],
        },
    )
    enc_id = enc_res.json()["id"]

    cert_payload = {
        "encounter_id": enc_id,
        "rest_from_date": today.isoformat(),
        "rest_to_date": (today + timedelta(days=3)).isoformat(),
        "fit_to_resume_date": (today + timedelta(days=4)).isoformat(),
        "diagnosis_summary": "Acute Gastroenteritis & Dehydration",
        "doctor_remarks": "Strict bed rest and oral rehydration therapy required.",
    }

    cert_res = client.post("/api/health-center/certificates", json=cert_payload)
    assert cert_res.status_code == 201, cert_res.text
    cert = cert_res.json()
    assert "MED-" in cert["certificate_number"]
    assert cert["status"] == "ISSUED"
    assert cert["patient_name"] is not None


def test_prevent_duplicate_active_medical_certificate(client: TestClient):
    """Verify only one active medical certificate can be issued per encounter."""
    ctx = _get_or_create_context(client)
    today = date.today()

    enc_res = client.post(
        "/api/health-center/encounters",
        json={
            "patient_type": "STUDENT",
            "student_id": ctx["student_id"],
            "visit_date": today.isoformat(),
            "doctor_name": "Dr. Sarah Johnson, MD",
            "chief_complaint": "Conjunctivitis infection",
            "diagnosis": "Acute Bacterial Conjunctivitis",
            "triage_severity": "NORMAL",
            "prescriptions": [],
        },
    )
    enc_id = enc_res.json()["id"]

    cert_payload = {
        "encounter_id": enc_id,
        "rest_from_date": today.isoformat(),
        "rest_to_date": (today + timedelta(days=2)).isoformat(),
        "fit_to_resume_date": (today + timedelta(days=3)).isoformat(),
        "diagnosis_summary": "Bacterial Conjunctivitis (Infectious)",
    }
    res1 = client.post("/api/health-center/certificates", json=cert_payload)
    assert res1.status_code == 201

    # Second certificate for same encounter rejected
    res2 = client.post("/api/health-center/certificates", json=cert_payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]


def test_medical_certificate_invalid_dates_rejected(client: TestClient):
    """Verify rest_to_date preceding rest_from_date triggers 422 validation error."""
    ctx = _get_or_create_context(client)
    today = date.today()

    enc_res = client.post(
        "/api/health-center/encounters",
        json={
            "patient_type": "STUDENT",
            "student_id": ctx["student_id"],
            "visit_date": today.isoformat(),
            "doctor_name": "Dr. Sarah Johnson, MD",
            "chief_complaint": "Mild sprain",
            "diagnosis": "Ligament Strain",
            "triage_severity": "NORMAL",
            "prescriptions": [],
        },
    )
    enc_id = enc_res.json()["id"]

    invalid_cert = {
        "encounter_id": enc_id,
        "rest_from_date": today.isoformat(),
        "rest_to_date": (today - timedelta(days=2)).isoformat(),  # Past date before from!
        "fit_to_resume_date": today.isoformat(),
        "diagnosis_summary": "Ligament Strain",
    }
    res = client.post("/api/health-center/certificates", json=invalid_cert)
    assert res.status_code == 422


def test_revoke_medical_certificate(client: TestClient):
    """Verify revoking an active medical certificate."""
    ctx = _get_or_create_context(client)
    today = date.today()

    enc_res = client.post(
        "/api/health-center/encounters",
        json={
            "patient_type": "STUDENT",
            "student_id": ctx["student_id"],
            "visit_date": today.isoformat(),
            "doctor_name": "Dr. Sarah Johnson, MD",
            "chief_complaint": "Early discharge",
            "diagnosis": "Mild Malaise",
            "triage_severity": "NORMAL",
            "prescriptions": [],
        },
    )
    enc_id = enc_res.json()["id"]

    cert_res = client.post(
        "/api/health-center/certificates",
        json={
            "encounter_id": enc_id,
            "rest_from_date": today.isoformat(),
            "rest_to_date": (today + timedelta(days=2)).isoformat(),
            "fit_to_resume_date": (today + timedelta(days=3)).isoformat(),
            "diagnosis_summary": "Mild Malaise",
        },
    )
    cert_id = cert_res.json()["id"]

    # Revoke
    revoke_res = client.put(f"/api/health-center/certificates/{cert_id}/revoke")
    assert revoke_res.status_code == 200
    assert revoke_res.json()["status"] == "REVOKED"


def test_health_stats_telemetry(client: TestClient):
    """Verify health telemetry endpoint returns structured KPI metrics."""
    res = client.get("/api/health-center/stats")
    assert res.status_code == 200
    data = res.json()
    assert "total_encounters" in data
    assert "student_visits" in data
    assert "faculty_visits" in data
    assert "active_sick_leaves" in data
    assert "low_stock_medicines" in data
    assert "total_profiles_registered" in data
    assert data["total_encounters"] >= 1


def test_view_health_center_html_page(client: TestClient):
    """Verify GET /health-center returns 200 HTML with KPI cards, tables, and action modals."""
    res = client.get("/health-center")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    html = res.text
    assert "Campus Health &amp; Infirmary Hub" in html or "Campus Health & Infirmary Hub" in html
    assert "Total Consultations" in html
    assert "Active Medical Sick Leaves" in html
    assert "Dispensary Stock Alerts" in html
    assert "modal-log-encounter" in html
    assert "modal-add-profile" in html
    assert "modal-add-medicine" in html
    assert "modal-issue-certificate" in html
