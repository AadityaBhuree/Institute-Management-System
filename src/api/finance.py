"""Finance, fee invoicing, and audit ledger API Endpoints."""

import sqlite3
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.database.connection import get_db
from src.models.finance import (
    FeeInvoiceCreate,
    FeeInvoiceOut,
    FeeStructureCreate,
    FeeStructureOut,
    FinanceSummaryOut,
    InvoiceDetailOut,
    PaymentCreate,
    PaymentOut,
)
from src.services.finance_service import FinanceService

router = APIRouter(prefix="/api/finance", tags=["Fee Invoicing & Financial Audit"])


@router.post(
    "/fee-structures",
    response_model=FeeStructureOut,
    status_code=status.HTTP_201_CREATED,
)
def create_fee_structure(
    fee_in: FeeStructureCreate,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Define official semester fee structure for a department."""
    try:
        return FinanceService.create_fee_structure(conn, fee_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/fee-structures", response_model=List[FeeStructureOut])
def list_fee_structures(
    department_id: Optional[int] = Query(None, description="Department ID filter"),
    semester: Optional[int] = Query(None, ge=1, le=8, description="Semester filter"),
    academic_year: Optional[str] = Query(None, description="Academic Year filter"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """List fee structures with department details."""
    return FinanceService.list_fee_structures(
        conn,
        department_id=department_id,
        semester=semester,
        academic_year=academic_year,
    )


@router.post("/invoices", response_model=FeeInvoiceOut, status_code=status.HTTP_201_CREATED)
def create_invoice(
    invoice_in: FeeInvoiceCreate,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Issue a new student fee invoice."""
    try:
        return FinanceService.create_invoice(conn, invoice_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/invoices", response_model=List[FeeInvoiceOut])
def list_invoices(
    student_id: Optional[int] = Query(None, description="Filter by student ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Invoice status"),
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    search: Optional[str] = Query(None, description="Search by invoice #, name, or enrollment"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve fee invoices roster with student details."""
    return FinanceService.list_invoices(
        conn,
        student_id=student_id,
        status=status_filter,
        department_id=department_id,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/invoices/{invoice_id}", response_model=InvoiceDetailOut)
def get_invoice(
    invoice_id: int,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve detailed fee invoice with transaction payment history."""
    invoice = FinanceService.get_invoice_by_id(conn, invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice ID {invoice_id} not found.",
        )
    return invoice


@router.post("/payments", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def record_payment(
    payment_in: PaymentCreate,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Record a fee payment, reduce invoice balance, and generate an official receipt."""
    try:
        return FinanceService.record_payment(conn, payment_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/payments", response_model=List[PaymentOut])
def list_payments(
    invoice_id: Optional[int] = Query(None, description="Filter by invoice ID"),
    student_id: Optional[int] = Query(None, description="Filter by student ID"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve payment ledger entries."""
    return FinanceService.list_payments(
        conn,
        invoice_id=invoice_id,
        student_id=student_id,
        limit=limit,
        offset=offset,
    )


@router.get("/summary", response_model=FinanceSummaryOut)
def get_finance_summary(
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve aggregated financial performance KPIs and recent ledger transactions."""
    return FinanceService.get_financial_summary(conn)
