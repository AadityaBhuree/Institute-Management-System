"""Finance, fee structures, invoices, and payments schemas."""

from typing import List, Optional

from pydantic import BaseModel, Field


class FeeStructureCreate(BaseModel):
    department_id: int = Field(..., gt=0)
    semester: int = Field(..., ge=1, le=8)
    fee_type: str = Field(..., min_length=2, max_length=50)
    amount: float = Field(..., ge=0)
    academic_year: str = Field("2026-2027")


class FeeStructureOut(FeeStructureCreate):
    id: int
    department_name: Optional[str] = None
    created_at: Optional[str] = None


class FeeInvoiceCreate(BaseModel):
    student_id: int = Field(..., gt=0)
    title: str = Field("Semester Tuition & Institutional Fee")
    term_name: str = Field("Fall 2026")
    total_amount: float = Field(..., gt=0)
    due_date: str = Field(..., description="YYYY-MM-DD")


class FeeInvoiceOut(BaseModel):
    id: int
    invoice_no: str
    student_id: int
    student_name: Optional[str] = None
    enrollment_no: Optional[str] = None
    title: str
    term_name: str
    total_amount: float
    paid_amount: float
    balance_amount: float
    status: str
    due_date: str
    issued_date: str
    created_at: Optional[str] = None


class PaymentCreate(BaseModel):
    invoice_id: int = Field(..., gt=0)
    amount: float = Field(..., gt=0)
    payment_method: str = Field("ONLINE", description="ONLINE, CASH, BANK_TRANSFER, CHEQUE, UPI")
    transaction_ref: Optional[str] = None
    notes: Optional[str] = None
    received_by: Optional[str] = "Bursar Counter"


class PaymentOut(PaymentCreate):
    id: int
    payment_no: str
    payment_date: str
    invoice_no: Optional[str] = None
    student_name: Optional[str] = None
    new_balance: Optional[float] = None
    invoice_status: Optional[str] = None


class InvoiceDetailOut(FeeInvoiceOut):
    payments: List[PaymentOut] = []


class FinanceSummaryOut(BaseModel):
    total_billed: float
    total_collected: float
    total_outstanding: float
    collection_rate: float
    total_invoices: int
    paid_count: int
    partial_count: int
    unpaid_count: int
    overdue_count: int
    recent_payments: List[PaymentOut] = []
