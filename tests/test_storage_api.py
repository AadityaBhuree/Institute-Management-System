"""Comprehensive Test Suite for Secure Document & Media Storage Subsystem.
Tests upload validation, magic-byte inspection, dangerous file rejection,
streaming downloads, RBAC boundaries, and path traversal protection.
"""

import io

from src.core.config import MAX_UPLOAD_SIZE_BYTES


def test_upload_png_image_success(client):
    """Verify uploading a valid PNG image with binary header inspection."""
    png_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 64
    files = {"file": ("student_avatar.png", io.BytesIO(png_content), "image/png")}
    data = {"category": "AVATAR"}

    res = client.post("/api/storage/upload", files=files, data=data)
    assert res.status_code == 201
    payload = res.json()
    assert payload["status"] == "SUCCESS"
    doc = payload["document"]
    assert doc["mime_type"] == "image/png"
    assert doc["category"] == "AVATAR"
    assert doc["original_name"] == "student_avatar.png"
    assert doc["file_id"].startswith("doc_")
    assert doc["file_url"] == f"/api/storage/files/{doc['file_id']}"


def test_upload_pdf_document_success(client):
    """Verify uploading a valid PDF document with %PDF- header."""
    pdf_content = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    files = {"file": ("placement_resume.pdf", io.BytesIO(pdf_content), "application/pdf")}
    data = {"category": "RESUME"}

    res = client.post("/api/storage/upload", files=files, data=data)
    assert res.status_code == 201
    doc = res.json()["document"]
    assert doc["mime_type"] == "application/pdf"
    assert doc["category"] == "RESUME"


def test_stream_uploaded_file_success(client):
    """Verify downloading / streaming a stored file returns accurate bytes and headers."""
    content = b"%PDF-1.4\n%test pdf stream content\n%%EOF"
    files = {"file": ("test_cert.pdf", io.BytesIO(content), "application/pdf")}
    res_upload = client.post("/api/storage/upload", files=files, data={"category": "MEDICAL"})
    assert res_upload.status_code == 201
    file_id = res_upload.json()["document"]["file_id"]

    res_stream = client.get(f"/api/storage/files/{file_id}")
    assert res_stream.status_code == 200
    assert res_stream.content == content
    assert res_stream.headers["content-type"] == "application/pdf"
    assert res_stream.headers.get("x-content-type-options") == "nosniff"


def test_reject_disguised_executable(client):
    """Verify executable binary disguised as a PNG image is rejected by magic byte inspection."""
    # Windows PE executable header: MZ
    disguised_exe = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00" + b"\x00" * 50
    files = {"file": ("malicious.png", io.BytesIO(disguised_exe), "image/png")}

    res = client.post("/api/storage/upload", files=files)
    assert res.status_code == 400
    assert "File content signature does not match" in res.json()["detail"]


def test_reject_forbidden_extension(client):
    """Verify script and executable extensions are blocked fail-closed."""
    script_content = b"#!/bin/bash\necho 'hello world'\n"
    files = {"file": ("script.sh", io.BytesIO(script_content), "text/plain")}

    res = client.post("/api/storage/upload", files=files)
    assert res.status_code == 400
    assert "strictly prohibited" in res.json()["detail"]


def test_reject_empty_file(client):
    """Verify 0-byte file is rejected."""
    files = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
    res = client.post("/api/storage/upload", files=files)
    assert res.status_code == 400
    assert "Uploaded file is empty" in res.json()["detail"]


def test_reject_oversized_file(client):
    """Verify files exceeding maximum permitted upload size return HTTP 413."""
    oversized = b"%PDF-" + b"0" * (MAX_UPLOAD_SIZE_BYTES + 2048)
    files = {"file": ("huge.pdf", io.BytesIO(oversized), "application/pdf")}

    res = client.post("/api/storage/upload", files=files)
    assert res.status_code == 413
    assert "exceeds maximum permitted limit" in res.json()["detail"]


def test_stream_nonexistent_file_404(client):
    """Verify streaming a non-existent file returns 404."""
    res = client.get("/api/storage/files/doc_nonexistent_99999999")
    assert res.status_code == 404


def test_path_traversal_attack_rejected(client):
    """Verify path traversal characters are blocked."""
    res = client.get("/api/storage/files/..%2F..%2F..%2Fetc%2Fpasswd")
    assert res.status_code in (404, 400)


def test_list_and_delete_documents_workflow(client, student_client):
    """Verify document listing with role gating and owner/admin deletion permissions."""
    # 1. Admin uploads document
    pdf_content = b"%PDF-1.5\n%admin document\n%%EOF"
    upload_res = client.post(
        "/api/storage/upload",
        files={"file": ("admin_policy.pdf", io.BytesIO(pdf_content), "application/pdf")},
        data={"category": "GENERAL"},
    )
    assert upload_res.status_code == 201
    file_id = upload_res.json()["document"]["file_id"]

    # 2. List documents as admin -> sees document
    admin_list = client.get("/api/storage/documents")
    assert admin_list.status_code == 200
    assert any(d["file_id"] == file_id for d in admin_list.json()["documents"])

    # 3. Student attempts to delete admin's document -> 403 Forbidden
    student_delete = student_client.delete(f"/api/storage/files/{file_id}")
    assert student_delete.status_code == 403

    # 4. Admin deletes document -> 200 OK
    admin_delete = client.delete(f"/api/storage/files/{file_id}")
    assert admin_delete.status_code == 200
    assert admin_delete.json()["status"] == "DELETED"

    # 5. Subsequent download returns 404
    assert client.get(f"/api/storage/files/{file_id}").status_code == 404

