"""Comprehensive Automated Test Suite for Multi-Format Reports & Cohort Archival.
Validates ReportLab vector PDF transcripts, bursar receipts, medical certificates,
streaming OpenPyXL XLSX workbooks, and cold-storage SHA-256 cohort archival.
"""

import io

import openpyxl
from fastapi.testclient import TestClient


def test_export_students_excel(client: TestClient):
    """Verify downloading students roster Excel workbook with styles, freeze pane, and valid data."""
    # Enroll test scholar
    client.post(
        "/api/students",
        json={
            "first_name": "Aryabhata",
            "last_name": "Astronomer",
            "email": "aryabhata.astronomer@nalanda.edu",
            "department_id": 1,
            "dob": "2002-04-14",
            "gender": "Male",
        },
    )

    res = client.get("/api/reports/export/students/excel")
    assert res.status_code == 200
    assert (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        in res.headers["content-type"]
    )
    assert "attachment; filename=students_roster.xlsx" in res.headers["content-disposition"]
    assert res.content.startswith(b"PK\x03\x04")

    # Load and inspect spreadsheet structure
    wb = openpyxl.load_workbook(io.BytesIO(res.content))
    assert "Scholars Directory" in wb.sheetnames
    ws = wb["Scholars Directory"]
    assert ws.max_row >= 2
    header_vals = [cell.value for cell in ws[1]]
    assert "Enrollment No" in header_vals
    assert "First Name" in header_vals
    assert "Email Address" in header_vals
    assert "Department Name" in header_vals
    assert any(
        "Aryabhata" in [cell.value for cell in ws[row_idx]] for row_idx in range(2, ws.max_row + 1)
    )


def test_export_finances_excel(client: TestClient):
    """Verify downloading multi-tab bursar financial ledger and departmental summary Excel workbook."""
    # Ensure a student and invoice exist
    st_res = client.post(
        "/api/students",
        json={
            "first_name": "Chanakya",
            "last_name": "Kautilya",
            "email": "chanakya.kautilya@takshashila.edu",
            "department_id": 1,
            "dob": "2001-01-01",
            "gender": "Male",
        },
    )
    student_id = st_res.json()["id"]

    inv_res = client.post(
        "/api/finance/invoices",
        json={
            "student_id": student_id,
            "title": "Semester 1 Academic Fee",
            "term_name": "Fall 2026",
            "total_amount": 4200.0,
            "due_date": "2026-12-31",
        },
    )
    assert inv_res.status_code == 201

    res = client.get("/api/reports/export/finances/excel")
    assert res.status_code == 200
    assert "spreadsheetml.sheet" in res.headers["content-type"]
    assert "attachment; filename=financial_ledger_audit.xlsx" in res.headers["content-disposition"]

    wb = openpyxl.load_workbook(io.BytesIO(res.content))
    assert "Fee Ledger & Invoices" in wb.sheetnames
    assert "Department Fiscal Summary" in wb.sheetnames

    ws1 = wb["Fee Ledger & Invoices"]
    headers1 = [cell.value for cell in ws1[1]]
    assert "Invoice No" in headers1
    assert "Total Billed ($)" in headers1
    assert "Balance Due ($)" in headers1
    assert ws1.max_row >= 3  # header + invoice row + total audit row

    ws2 = wb["Department Fiscal Summary"]
    headers2 = [cell.value for cell in ws2[1]]
    assert "Dept Code" in headers2
    assert "Recovery Rate (%)" in headers2
    assert ws2.max_row >= 2


def test_export_attendance_excel(client: TestClient):
    """Verify downloading multi-tab attendance risk sentinel and institutional overview Excel workbook."""
    res = client.get("/api/reports/export/attendance/excel")
    assert res.status_code == 200
    assert "spreadsheetml.sheet" in res.headers["content-type"]
    assert "attachment; filename=attendance_audit.xlsx" in res.headers["content-disposition"]

    wb = openpyxl.load_workbook(io.BytesIO(res.content))
    assert "Risk Sentinel (< 75%)" in wb.sheetnames
    assert "Attendance Overview" in wb.sheetnames

    ws2 = wb["Attendance Overview"]
    assert ws2.max_row >= 3
    metric_names = [ws2.cell(row=i, column=1).value for i in range(2, ws2.max_row + 1)]
    assert "Institutional Attendance Rate" in metric_names


def test_export_transcript_pdf_success(client: TestClient):
    """Verify compiling vector academic transcript PDF for registered student."""
    st_res = client.post(
        "/api/students",
        json={
            "first_name": "Srinivasa",
            "last_name": "Ramanujan",
            "email": "ramanujan.math@cambridge.edu",
            "department_id": 1,
            "dob": "1997-12-22",
            "gender": "Male",
        },
    )
    student_id = st_res.json()["id"]

    res = client.get(f"/api/reports/export/transcript/{student_id}/pdf")
    assert res.status_code == 200
    assert "application/pdf" in res.headers["content-type"]
    assert (
        f"attachment; filename=transcript_student_{student_id}.pdf"
        in res.headers["content-disposition"]
    )
    assert res.content.startswith(b"%PDF-")
    assert len(res.content) > 1000  # Valid binary PDF length


def test_export_portal_transcript_pdf_alias(client: TestClient):
    """Verify student portal alias route for academic transcript PDF."""
    st_res = client.post(
        "/api/students",
        json={
            "first_name": "Subrahmanyan",
            "last_name": "Chandrasekhar",
            "email": "chandra.limit@astrophysics.edu",
            "department_id": 1,
            "dob": "1998-10-19",
            "gender": "Male",
        },
    )
    student_id = st_res.json()["id"]

    res = client.get(f"/api/portal/transcript/{student_id}/pdf")
    assert res.status_code == 200
    assert "application/pdf" in res.headers["content-type"]
    assert res.content.startswith(b"%PDF-")


def test_export_transcript_pdf_404_nonexistent(client: TestClient):
    """Verify requesting transcript for nonexistent student ID returns 404."""
    res = client.get("/api/reports/export/transcript/999999/pdf")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_export_fee_receipt_pdf_success(client: TestClient):
    """Verify compiling official bursar fee receipt vector PDF."""
    st_res = client.post(
        "/api/students",
        json={
            "first_name": "Jagadish",
            "last_name": "Bose",
            "email": "jcbose.radio@physics.edu",
            "department_id": 1,
            "dob": "1996-11-30",
            "gender": "Male",
        },
    )
    student_id = st_res.json()["id"]

    inv_res = client.post(
        "/api/finance/invoices",
        json={
            "student_id": student_id,
            "title": "Laboratory & Instrumentation Fee",
            "term_name": "Spring 2026",
            "total_amount": 2500.0,
            "due_date": "2026-11-30",
        },
    )
    invoice_id = inv_res.json()["id"]

    # Record partial payment
    client.post(
        "/api/finance/payments",
        json={
            "invoice_id": invoice_id,
            "amount": 1500.0,
            "payment_method": "UPI",
            "transaction_ref": "UPI-TXN-998877",
            "remarks": "Scholar fee partial transfer",
        },
    )

    res = client.get(f"/api/reports/export/receipt/{invoice_id}/pdf")
    assert res.status_code == 200
    assert "application/pdf" in res.headers["content-type"]
    assert (
        f"attachment; filename=fee_receipt_inv_{invoice_id}.pdf"
        in res.headers["content-disposition"]
    )
    assert res.content.startswith(b"%PDF-")
    assert len(res.content) > 1000


def test_export_fee_receipt_pdf_404(client: TestClient):
    """Verify requesting receipt for nonexistent invoice returns 404."""
    res = client.get("/api/reports/export/receipt/999999/pdf")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_export_medical_certificate_pdf(client: TestClient):
    """Verify compiling clinical medical certificate vector PDF."""
    st_res = client.post(
        "/api/students",
        json={
            "first_name": "C. V.",
            "last_name": "Raman",
            "email": "cvraman.spectroscopy@optics.edu",
            "department_id": 1,
            "dob": "1995-11-07",
            "gender": "Male",
        },
    )
    student_id = st_res.json()["id"]

    # Log encounter
    enc_res = client.post(
        "/api/health-center/encounters",
        json={
            "patient_type": "STUDENT",
            "student_id": student_id,
            "visit_date": "2026-11-20",
            "doctor_name": "Dr. Charaka",
            "chief_complaint": "High fever and viral fatigue",
            "symptoms": "High fever, viral fatigue",
            "diagnosis": "Seasonal Influenza A",
            "temperature_f": 101.4,
            "pulse_bpm": 88,
            "blood_pressure": "120/80",
        },
    )
    assert enc_res.status_code == 201
    encounter_id = enc_res.json()["id"]

    # Issue certificate
    cert_res = client.post(
        "/api/health-center/certificates",
        json={
            "encounter_id": encounter_id,
            "rest_from_date": "2026-11-20",
            "rest_to_date": "2026-11-23",
            "fit_to_resume_date": "2026-11-24",
            "diagnosis_summary": "Seasonal Influenza A",
            "doctor_remarks": "Strict bed rest advised. Avoid strenuous academic activity.",
        },
    )
    assert cert_res.status_code == 201
    cert_id = cert_res.json()["id"]

    res = client.get(f"/api/reports/export/medical-certificate/{cert_id}/pdf")
    assert res.status_code == 200
    assert "application/pdf" in res.headers["content-type"]
    assert f"attachment; filename=medical_cert_{cert_id}.pdf" in res.headers["content-disposition"]
    assert res.content.startswith(b"%PDF-")


def test_cohort_archival_and_integrity_verification_lifecycle(client: TestClient):
    """Verify end-to-end policy archival of graduated scholars with SHA-256 integrity seal."""
    # Enroll scholar with graduated status
    st_res = client.post(
        "/api/students",
        json={
            "first_name": "Prasanta",
            "last_name": "Mahalanobis",
            "email": "pcm.stats@isi.edu",
            "department_id": 1,
            "dob": "1994-06-29",
            "gender": "Male",
            "status": "GRADUATED",
            "current_semester": 8,
            "admission_date": "2020-08-01",
        },
    )
    assert st_res.status_code == 201
    student_id = st_res.json()["id"]

    # Execute cohort archival for 2024
    res = client.post(
        "/api/reports/archival/cohort",
        json={
            "graduation_year": 2024,
            "department_id": 1,
            "notes": "Convocation 2024 official archival batch",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "COMPLETED"
    assert data["graduation_year"] == 2024
    assert data["archived_count"] >= 1

    archived_record = next(
        (r for r in data["archived_records"] if r["original_student_id"] == student_id),
        None,
    )
    assert archived_record is not None
    assert archived_record["enrollment_no"] is not None
    assert len(archived_record["integrity_hash"]) == 64  # Valid SHA-256 hex string
    archive_id = archived_record["id"]

    # Student status in active registry is now GRADUATED
    st_check = client.get(f"/api/students/{student_id}")
    assert st_check.status_code == 200
    assert st_check.json()["status"] == "GRADUATED"

    # List archived records
    list_res = client.get("/api/reports/archival/records?graduation_year=2024")
    assert list_res.status_code == 200
    assert any(r["id"] == archive_id for r in list_res.json())

    # Get single archived record with decoded snapshot
    detail_res = client.get(f"/api/reports/archival/records/{archive_id}")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert "snapshot" in detail_data
    assert detail_data["snapshot"]["student"]["id"] == student_id

    # Cryptographically verify the SHA-256 seal
    verify_res = client.get(f"/api/reports/archival/records/{archive_id}/verify")
    assert verify_res.status_code == 200
    v_data = verify_res.json()
    assert v_data["is_valid"] is True
    assert v_data["stored_hash"] == v_data["computed_hash"]


def test_cohort_archival_rbac_boundaries(anon_client: TestClient, student_client: TestClient):
    """Verify unauthorized or unprivileged roles cannot execute archival or view records."""
    # Anonymous client rejected
    res_anon = anon_client.post(
        "/api/reports/archival/cohort",
        json={"graduation_year": 2025},
    )
    assert res_anon.status_code == 401

    # Student role rejected with 403 Forbidden
    res_student = student_client.post(
        "/api/reports/archival/cohort",
        json={"graduation_year": 2025},
    )
    assert res_student.status_code == 403

    # Student cannot view cold storage index
    res_student_list = student_client.get("/api/reports/archival/records")
    assert res_student_list.status_code == 403
