"""Institutional Digital ID Card & Public Verification API Router."""

import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from src.core.security import get_current_user, require_role
from src.database.connection import get_db
from src.models.id_card import IDCardVerificationOut
from src.services.auth_service import AuthService
from src.services.id_card_service import IDCardService

router = APIRouter(prefix="/api/id-cards", tags=["Digital ID Cards & Public Verification"])


@router.get("/student/{student_id}/pdf")
def get_student_id_card_pdf(
    student_id: int,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Generate printable CR80 vector PDF for a student's institutional identity card."""
    # RBAC: students can view their own card; faculty & admin can view any
    if current_user.get("role") == "student":
        student_user_id = current_user.get("student_id") or current_user.get("id")
        if student_user_id != student_id and current_user.get("id") != student_id:
            # Check student ID matching user record
            cur = conn.cursor()
            cur.execute("SELECT id FROM students WHERE id = ?;", (student_id,))
            row = cur.fetchone()
            cur.close()
            if not row:
                raise HTTPException(status_code=404, detail="Student not found")

    base_url = str(request.base_url).rstrip("/")
    try:
        pdf_bytes = IDCardService.generate_single_id_card_pdf(
            entity_type="STUDENT",
            entity_id=student_id,
            conn=conn,
            base_url=base_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    card_data = IDCardService.get_student_card_data(conn, student_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="ID_Card_{card_data["enrollment_no"]}.pdf"',
            "Cache-Control": "public, max-age=3600",
        },
    )


@router.get("/student/{student_id}/svg")
def get_student_id_card_svg(
    student_id: int,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Generate crisp standalone SVG card for scholar mobile portal and web embedding."""
    base_url = str(request.base_url).rstrip("/")
    try:
        svg_content = IDCardService.generate_id_card_svg(
            entity_type="STUDENT",
            entity_id=student_id,
            conn=conn,
            base_url=base_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return Response(content=svg_content, media_type="image/svg+xml")


@router.get("/faculty/{faculty_id}/pdf")
def get_faculty_id_card_pdf(
    faculty_id: int,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Generate printable CR80 vector PDF for a faculty member's institutional identity card."""
    base_url = str(request.base_url).rstrip("/")
    try:
        pdf_bytes = IDCardService.generate_single_id_card_pdf(
            entity_type="FACULTY",
            entity_id=faculty_id,
            conn=conn,
            base_url=base_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    card_data = IDCardService.get_faculty_card_data(conn, faculty_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="Faculty_ID_{card_data["enrollment_no"]}.pdf"',
            "Cache-Control": "public, max-age=3600",
        },
    )


@router.get("/faculty/{faculty_id}/svg")
def get_faculty_id_card_svg(
    faculty_id: int,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Generate crisp standalone SVG card for faculty workbench embedding."""
    base_url = str(request.base_url).rstrip("/")
    try:
        svg_content = IDCardService.generate_id_card_svg(
            entity_type="FACULTY",
            entity_id=faculty_id,
            conn=conn,
            base_url=base_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return Response(content=svg_content, media_type="image/svg+xml")


@router.get("/batch/pdf")
def get_batch_id_cards_pdf(
    department_id: Optional[int] = Query(None, description="Filter cohort by department ID"),
    cohort_year: Optional[int] = Query(None, description="Filter cohort by admission year"),
    request: Request = None,
    conn: sqlite3.Connection = Depends(get_db),
    admin_user: dict = Depends(require_role("admin")),
):
    """Generate printable A4 8-up batch sheet of CR80 identity cards with cut guides (Admin only)."""
    base_url = str(request.base_url).rstrip("/") if request else "https://ims.edu"
    try:
        pdf_bytes = IDCardService.generate_batch_id_cards_pdf(
            department_id=department_id,
            cohort_year=cohort_year,
            conn=conn,
            base_url=base_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    AuthService.log_audit(
        conn,
        action="BATCH_ID_CARD_PRINT",
        resource="id_cards",
        resource_id=f"dept_{department_id}_year_{cohort_year}",
        user_id=admin_user.get("id"),
        username=admin_user.get("username"),
        details=f"Exported batch ID cards PDF (Dept: {department_id or 'All'}, Year: {cohort_year or 'All'})",
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="Batch_ID_Cards_Print_Sheet.pdf"',
        },
    )


@router.get("/verify/{token}", response_model=IDCardVerificationOut)
def verify_id_card_token(
    token: str,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Public verification API endpoint for scanning and verifying credential authenticity."""
    result = IDCardService.verify_id_token(token, conn)
    return result
