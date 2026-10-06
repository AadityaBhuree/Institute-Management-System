"""Models package export."""

from src.models.academics import (
    AttendanceBatchMark,
    AttendanceRecordOut,
    ExamCreate,
    ExamGradeBatchSubmit,
    ExamOut,
    ExamResultOut,
    SingleAttendance,
    SingleGrade,
)
from src.models.course import CourseCreate, CourseOut, CourseUpdate, EnrollmentCreate
from src.models.department import DepartmentCreate, DepartmentOut
from src.models.faculty import FacultyCreate, FacultyOut, FacultyUpdate
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
from src.models.student import StudentCreate, StudentOut, StudentUpdate

__all__ = [
    "DepartmentCreate",
    "DepartmentOut",
    "StudentCreate",
    "StudentUpdate",
    "StudentOut",
    "FacultyCreate",
    "FacultyUpdate",
    "FacultyOut",
    "CourseCreate",
    "CourseUpdate",
    "CourseOut",
    "EnrollmentCreate",
    "SingleAttendance",
    "AttendanceBatchMark",
    "AttendanceRecordOut",
    "ExamCreate",
    "ExamOut",
    "SingleGrade",
    "ExamGradeBatchSubmit",
    "ExamResultOut",
    "FeeStructureCreate",
    "FeeStructureOut",
    "FeeInvoiceCreate",
    "FeeInvoiceOut",
    "InvoiceDetailOut",
    "PaymentCreate",
    "PaymentOut",
    "FinanceSummaryOut",
]
