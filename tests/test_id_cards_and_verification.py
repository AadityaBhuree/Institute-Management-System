"""Automated test suite for Phase 17: Digital ID Cards & Cryptographic Verification Engine.
Validates CR80 vector PDF compilation, A4 8-up batch print sheets, interactive SVGs,
HMAC-SHA256 signature tampering detection, public web verification, and RBAC policies.
"""

import time

import pytest

from src.database.connection import get_connection, release_connection
from src.services.id_card_service import IDCardService


@pytest.fixture
def sample_student(client):
    """Ensure an active enrolled student exists for ID card test operations."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, enrollment_no FROM students WHERE is_deleted = 0 LIMIT 1;")
        row = cur.fetchone()
        cur.close()
        if row:
            return dict(row)
    finally:
        release_connection(conn)

    payload = {
        "first_name": "Aditya",
        "last_name": "Sharma",
        "email": f"aditya.id.{time.time()}@example.edu",
        "department_id": 1,
        "current_semester": 1,
        "status": "ENROLLED",
        "blood_group": "O+",
        "emergency_contact": "Security: (555) 019-9111",
    }
    res = client.post("/api/students", json=payload)
    return res.json()


@pytest.fixture
def sample_faculty(client):
    """Ensure a faculty member exists for ID card test operations."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, faculty_id FROM faculty LIMIT 1;")
        row = cur.fetchone()
        cur.close()
        if row:
            return dict(row)
    finally:
        release_connection(conn)

    payload = {
        "first_name": "Alan",
        "last_name": "Turing",
        "email": f"turing.id.{time.time()}@example.edu",
        "department_id": 1,
        "designation": "Professor",
        "qualification": "Ph.D.",
    }
    res = client.post("/api/faculty", json=payload)
    return res.json()


def test_id_token_generation_and_tamper_detection():
    """Verify cryptographic HMAC-SHA256 signature generation and anti-tampering protection."""
    token = IDCardService.generate_id_token(
        entity_type="STUDENT",
        entity_id=1,
        identifier="IMS-2026-CS-0001",
        name="Aditya Sharma",
        dept_code="CS",
        valid_until="2030-06-30",
    )
    assert "." in token
    payload_b64, sig = token.split(".")
    assert len(payload_b64) > 10
    assert len(sig) == 64  # SHA-256 hex digest length

    # 1. Valid token without DB check
    result = IDCardService.verify_id_token(token)
    assert result["valid"] is True
    assert result["status"] == "VERIFIED"
    assert result["identifier"] == "IMS-2026-CS-0001"
    assert result["name"] == "Aditya Sharma"

    # 2. Tampered signature
    tampered_sig = sig[:-4] + "ffff"
    tampered_token = f"{payload_b64}.{tampered_sig}"
    tampered_result = IDCardService.verify_id_token(tampered_token)
    assert tampered_result["valid"] is False
    assert tampered_result["status"] == "TAMPERED"

    # 3. Malformed token
    malformed_result = IDCardService.verify_id_token("invalid_token_without_period")
    assert malformed_result["valid"] is False
    assert malformed_result["status"] == "MALFORMED"


def test_id_token_expiration_handling():
    """Verify expired ID credentials are detected and rejected."""
    expired_token = IDCardService.generate_id_token(
        entity_type="STUDENT",
        entity_id=1,
        identifier="IMS-2020-CS-0001",
        name="Alumnus Student",
        dept_code="CS",
        valid_until="2020-01-01",
    )
    res = IDCardService.verify_id_token(expired_token)
    assert res["valid"] is False
    assert res["status"] == "EXPIRED"
    assert "expired" in res["reason"].lower()


def test_id_token_database_status_verification(sample_student):
    """Verify active scholar and faculty records in the institutional database."""
    conn = get_connection()
    try:
        card_data = IDCardService.get_student_card_data(conn, sample_student["id"])
        token = card_data["token"]

        res = IDCardService.verify_id_token(token, conn)
        assert res["valid"] is True
        assert res["status"] == "VERIFIED"
        assert res["data"]["enrollment_no"] == sample_student["enrollment_no"]

        # Non-existent student ID in token
        fake_token = IDCardService.generate_id_token(
            entity_type="STUDENT",
            entity_id=999999,
            identifier="IMS-FAKE-999",
            name="Ghost Scholar",
            dept_code="CS",
            valid_until="2030-01-01",
        )
        fake_res = IDCardService.verify_id_token(fake_token, conn)
        assert fake_res["valid"] is False
        assert fake_res["status"] == "NOT_FOUND"
    finally:
        release_connection(conn)


def test_generate_single_student_id_card_pdf(sample_student):
    """Verify CR80 vector PDF binary compilation for a student."""
    conn = get_connection()
    try:
        pdf_bytes = IDCardService.generate_single_id_card_pdf("STUDENT", sample_student["id"], conn)
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b"%PDF-")
        assert len(pdf_bytes) > 2000
    finally:
        release_connection(conn)


def test_generate_single_faculty_id_card_pdf(sample_faculty):
    """Verify CR80 vector PDF binary compilation for a faculty instructor."""
    conn = get_connection()
    try:
        pdf_bytes = IDCardService.generate_single_id_card_pdf("FACULTY", sample_faculty["id"], conn)
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b"%PDF-")
        assert len(pdf_bytes) > 2000
    finally:
        release_connection(conn)


def test_generate_batch_id_cards_pdf(sample_student):
    """Verify batch 8-up A4 printable sheet generation."""
    conn = get_connection()
    try:
        pdf_bytes = IDCardService.generate_batch_id_cards_pdf(
            department_id=None,
            cohort_year=None,
            conn=conn,
        )
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b"%PDF-")
        assert len(pdf_bytes) > 3000
    finally:
        release_connection(conn)


def test_generate_id_card_svg(sample_student):
    """Verify standalone interactive SVG card compilation."""
    conn = get_connection()
    try:
        svg = IDCardService.generate_id_card_svg("STUDENT", sample_student["id"], conn)
        assert isinstance(svg, str)
        assert "<svg" in svg
        assert 'viewBox="0 0 428 270"' in svg
        assert "</svg>" in svg
        assert "INSTITUTE OF TECHNOLOGY" in svg
    finally:
        release_connection(conn)


# ============================================================================
# REST API & Web Page Integration Tests
# ============================================================================


def test_api_student_id_card_pdf(client, sample_student):
    """Verify GET /api/id-cards/student/{id}/pdf returns CR80 PDF."""
    response = client.get(f"/api/id-cards/student/{sample_student['id']}/pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "inline;" in response.headers.get("content-disposition", "")
    assert response.content.startswith(b"%PDF-")


def test_api_student_id_card_svg(client, sample_student):
    """Verify GET /api/id-cards/student/{id}/svg returns SVG image."""
    response = client.get(f"/api/id-cards/student/{sample_student['id']}/svg")
    assert response.status_code == 200
    assert "image/svg+xml" in response.headers["content-type"]
    assert "<svg" in response.text


def test_api_faculty_id_card_pdf_and_svg(client, sample_faculty):
    """Verify faculty ID card PDF and SVG endpoints."""
    fac_id = sample_faculty["id"]
    res_pdf = client.get(f"/api/id-cards/faculty/{fac_id}/pdf")
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"

    res_svg = client.get(f"/api/id-cards/faculty/{fac_id}/svg")
    assert res_svg.status_code == 200
    assert "image/svg+xml" in res_svg.headers["content-type"]


def test_api_batch_id_cards_admin_only(client, student_client, sample_student):
    """Verify only administrators can access batch ID card print sheets."""
    # Admin client -> 200 OK
    res_admin = client.get("/api/id-cards/batch/pdf")
    assert res_admin.status_code == 200
    assert res_admin.headers["content-type"] == "application/pdf"
    assert "Batch_ID_Cards_Print_Sheet.pdf" in res_admin.headers["content-disposition"]

    # Student client -> 403 Forbidden
    res_student = student_client.get("/api/id-cards/batch/pdf")
    assert res_student.status_code == 403


def test_api_public_token_verification(anon_client, sample_student):
    """Verify public verification endpoint GET /api/id-cards/verify/{token} without auth."""
    conn = get_connection()
    try:
        card_data = IDCardService.get_student_card_data(conn, sample_student["id"])
        valid_token = card_data["token"]
    finally:
        release_connection(conn)

    # Valid token
    res = anon_client.get(f"/api/id-cards/verify/{valid_token}")
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["status"] == "VERIFIED"
    assert data["identifier"] == sample_student["enrollment_no"]

    # Tampered token
    tampered = valid_token[:-4] + "dead"
    res_bad = anon_client.get(f"/api/id-cards/verify/{tampered}")
    assert res_bad.status_code == 200
    bad_data = res_bad.json()
    assert bad_data["valid"] is False
    assert bad_data["status"] == "TAMPERED"


def test_web_public_id_verification_page(anon_client, sample_student):
    """Verify scanning QR code opens public verification badge page GET /verify/id/{token}."""
    conn = get_connection()
    try:
        card_data = IDCardService.get_student_card_data(conn, sample_student["id"])
        valid_token = card_data["token"]
    finally:
        release_connection(conn)

    res = anon_client.get(f"/verify/id/{valid_token}")
    assert res.status_code == 200
    assert "AUTHENTIC VERIFIED CREDENTIAL" in res.text
    assert sample_student["enrollment_no"] in res.text

    # Tampered token displays rejection notice
    tampered = valid_token[:-4] + "beef"
    res_bad = anon_client.get(f"/verify/id/{tampered}")
    assert res_bad.status_code == 200
    assert "Verification Rejected" in res_bad.text
