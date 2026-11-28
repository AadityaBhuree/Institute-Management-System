"""Institutional Reports, Multi-Format Exports & Cohort Archival API Router."""

import sqlite3
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response

from src.core.security import require_any_permission
from src.database.connection import get_db
from src.models.archival import (
    ArchivalIntegrityResponse,
    ArchivedStudentItem,
    CohortArchivalRequest,
    CohortArchivalResponse,
)
from src.services.archival_service import ArchivalService
from src.services.excel_service import ExcelService
from src.services.pdf_service import PDFService
from src.services.reports_service import ReportsService

router = APIRouter(prefix="/api/reports", tags=["Reports & Analytics"])
portal_router = APIRouter(prefix="/api/portal", tags=["Reports & Analytics"])


@router.get("/analytics-summary")
def get_analytics_summary(
    department_id: Optional[int] = Query(None, description="Filter analytics by department ID"),
    conn: sqlite3.Connection = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve full institutional telemetry, attendance risk sentinel, and financial recovery metrics."""
    return ReportsService.get_analytics_summary(conn, department_id=department_id)


# ==============================================================================
# CSV EXPORT ENDPOINTS
# ==============================================================================


@router.get("/export/students/csv")
def export_students_csv(
    department_id: Optional[int] = Query(None, description="Filter export by department ID"),
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    """Download registered scholar directory as a standardized CSV file."""
    csv_data = ReportsService.export_students_csv(conn, department_id=department_id)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=students_roster.csv"},
    )


@router.get("/export/attendance-risk/csv")
def export_attendance_risk_csv(
    department_id: Optional[int] = Query(None, description="Filter export by department ID"),
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    """Download attendance sentinel at-risk (< 75%) scholar report as CSV."""
    csv_data = ReportsService.export_attendance_risk_csv(conn, department_id=department_id)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance_risk_sentinel.csv"},
    )


@router.get("/export/finances/csv")
def export_finances_csv(
    department_id: Optional[int] = Query(None, description="Filter export by department ID"),
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    """Download bursar fee ledger and student invoice audit as CSV."""
    csv_data = ReportsService.export_financial_ledger_csv(conn, department_id=department_id)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=financial_ledger_audit.csv"},
    )


# ==============================================================================
# EXCEL (.XLSX) STREAMING EXPORT ENDPOINTS
# ==============================================================================


@router.get("/export/students/excel")
def export_students_excel(
    department_id: Optional[int] = Query(None, description="Filter export by department ID"),
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    """Download styled multi-column Excel spreadsheet of scholar registry."""
    xlsx_bytes = ExcelService.export_students_excel(conn, department_id=department_id)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=students_roster.xlsx"},
    )


@router.get("/export/finances/excel")
def export_finances_excel(
    department_id: Optional[int] = Query(None, description="Filter export by department ID"),
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    """Download multi-tab styled Excel workbook of bursar fee invoices & departmental fiscal recovery."""
    xlsx_bytes = ExcelService.export_finances_excel(conn, department_id=department_id)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=financial_ledger_audit.xlsx"},
    )


@router.get("/export/attendance/excel")
def export_attendance_excel(
    department_id: Optional[int] = Query(None, description="Filter export by department ID"),
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    """Download multi-tab styled Excel workbook of attendance risk sentinels and institutional benchmarks."""
    xlsx_bytes = ExcelService.export_attendance_excel(conn, department_id=department_id)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=attendance_audit.xlsx"},
    )


# ==============================================================================
# BINARY VECTOR PDF COMPILATION ENDPOINTS
# ==============================================================================


@router.get("/export/transcript/{student_id}/pdf")
def export_transcript_pdf(
    student_id: int,
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    """Download official sealed vector academic transcript PDF."""
    try:
        pdf_bytes = PDFService.generate_transcript_pdf(conn, student_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=transcript_student_{student_id}.pdf"
        },
    )


@portal_router.get("/transcript/{student_id}/pdf")
def export_portal_transcript_pdf(
    student_id: int,
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    """Download official academic transcript PDF via scholar portal route."""
    return export_transcript_pdf(student_id=student_id, conn=conn)


@router.get("/export/receipt/{invoice_id}/pdf")
def export_receipt_pdf(
    invoice_id: int,
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    """Download official bursar payment receipt vector PDF."""
    try:
        pdf_bytes = PDFService.generate_fee_receipt_pdf(conn, invoice_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=fee_receipt_inv_{invoice_id}.pdf"},
    )


@router.get("/export/medical-certificate/{certificate_id}/pdf")
def export_medical_certificate_pdf(
    certificate_id: int,
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    """Download clinical medical clearance certificate vector PDF."""
    try:
        pdf_bytes = PDFService.generate_medical_certificate_pdf(conn, certificate_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=medical_cert_{certificate_id}.pdf"},
    )


# ==============================================================================
# COHORT ARCHIVAL & CRYPTOGRAPHIC VERIFICATION ENDPOINTS (ADMIN ONLY)
# ==============================================================================


@router.post(
    "/archival/cohort",
    response_model=CohortArchivalResponse,
    status_code=status.HTTP_200_OK,
)
def archive_graduated_cohort(
    payload: CohortArchivalRequest,
    conn: sqlite3.Connection = Depends(get_db),
    admin_user: dict = Depends(require_any_permission("reports:archive", "system:admin")),
) -> Dict[str, Any]:
    """Execute cold storage archival for a graduated student cohort with SHA-256 seals (Admin only)."""
    return ArchivalService.archive_cohort(
        conn,
        graduation_year=payload.graduation_year,
        archived_by=admin_user["username"],
        department_id=payload.department_id,
        notes=payload.notes,
    )


@router.get(
    "/archival/records",
    response_model=List[ArchivedStudentItem],
)
def list_archived_records(
    graduation_year: Optional[int] = Query(None, description="Filter by cohort graduation year"),
    conn: sqlite3.Connection = Depends(get_db),
    admin_user: dict = Depends(require_any_permission("reports:archive", "system:admin")),
) -> List[Dict[str, Any]]:
    """Retrieve index of all cold-storage archived scholar records (Admin only)."""
    return ArchivalService.list_archived_records(conn, graduation_year=graduation_year)


@router.get(
    "/archival/records/{archive_id}",
)
def get_archived_record(
    archive_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    admin_user: dict = Depends(require_any_permission("reports:archive", "system:admin")),
) -> Dict[str, Any]:
    """Retrieve full archived record including decoded JSON dossier snapshot (Admin only)."""
    record = ArchivalService.get_archived_record(conn, archive_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Archived record #{archive_id} not found",
        )
    return record


@router.get(
    "/archival/records/{archive_id}/verify",
    response_model=ArchivalIntegrityResponse,
)
def verify_archived_record_integrity(
    archive_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    admin_user: dict = Depends(require_any_permission("reports:archive", "system:admin")),
) -> Dict[str, Any]:
    """Cryptographically verify the SHA-256 seal of an archived scholar snapshot (Admin only)."""
    try:
        return ArchivalService.verify_archive_integrity(conn, archive_id)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
