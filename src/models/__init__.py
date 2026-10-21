"""Models package export with complete domain models and schemas."""

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
from src.models.alumni import (
    AlumniMemberCreate,
    AlumniMemberOut,
    AlumniMentorshipRequestCreate,
    AlumniMentorshipRequestOut,
    AlumniMentorshipStatusUpdate,
)
from src.models.announcement import AnnouncementCreate, AnnouncementOut
from src.models.asset import (
    AssetCheckoutCreate,
    AssetCheckoutOut,
    AssetCreate,
    AssetMaintenanceCreate,
    AssetMaintenanceOut,
    AssetOut,
    AssetReturnUpdate,
    AssetStatsOut,
)
from src.models.common import ErrorResponse, MessageResponse
from src.models.course import CourseCreate, CourseOut, CourseUpdate, EnrollmentCreate
from src.models.department import DepartmentCreate, DepartmentOut
from src.models.event import (
    EventCreate,
    EventOut,
    EventRegistrationCreate,
    EventRegistrationOut,
    EventStatsOut,
)
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
from src.models.health import (
    DispensaryMedicineCreate,
    DispensaryMedicineOut,
    HealthProfileCreate,
    HealthProfileOut,
    HealthStatsOut,
    MedicalCertificateCreate,
    MedicalCertificateOut,
    MedicalEncounterCreate,
    MedicalEncounterOut,
    PrescriptionItemCreate,
)
from src.models.hostel import (
    HostelBlockCreate,
    HostelBlockOut,
    HostelRoomCreate,
    HostelRoomOut,
    RoomAllocationCreate,
    RoomAllocationOut,
    RoomCheckoutRequest,
)
from src.models.leave import LeaveRequestCreate, LeaveRequestOut, LeaveStatusUpdate
from src.models.library import (
    BookIssueRequest,
    BookLoanOut,
    BookReturnRequest,
    LibraryBookCreate,
    LibraryBookOut,
    LibraryStatsOut,
)
from src.models.placement import (
    PlacementApplicationCreate,
    PlacementApplicationOut,
    PlacementDriveCreate,
    PlacementDriveOut,
    PlacementStatsOut,
    PlacementStatusUpdate,
)
from src.models.scholarship import (
    ScholarshipApplicationCreate,
    ScholarshipApplicationOut,
    ScholarshipReviewUpdate,
    ScholarshipSchemeCreate,
    ScholarshipSchemeOut,
    ScholarshipStatsOut,
)
from src.models.student import StudentCreate, StudentOut, StudentUpdate
from src.models.timetable import TimetableSlotCreate, TimetableSlotOut
from src.models.transport import (
    TransportPassCreate,
    TransportPassOut,
    TransportRouteCreate,
    TransportRouteOut,
    TransportStatsOut,
    TransportVehicleCreate,
    TransportVehicleOut,
)

__all__ = [
    # Common
    "ErrorResponse",
    "MessageResponse",
    # Departments
    "DepartmentCreate",
    "DepartmentOut",
    # Students & Admissions
    "StudentCreate",
    "StudentUpdate",
    "StudentOut",
    # Faculty
    "FacultyCreate",
    "FacultyUpdate",
    "FacultyOut",
    # Courses
    "CourseCreate",
    "CourseUpdate",
    "CourseOut",
    "EnrollmentCreate",
    # Academics & Grading
    "SingleAttendance",
    "AttendanceBatchMark",
    "AttendanceRecordOut",
    "ExamCreate",
    "ExamOut",
    "SingleGrade",
    "ExamGradeBatchSubmit",
    "ExamResultOut",
    # Finance
    "FeeStructureCreate",
    "FeeStructureOut",
    "FeeInvoiceCreate",
    "FeeInvoiceOut",
    "InvoiceDetailOut",
    "PaymentCreate",
    "PaymentOut",
    "FinanceSummaryOut",
    # Notice Board
    "AnnouncementCreate",
    "AnnouncementOut",
    # Timetable
    "TimetableSlotCreate",
    "TimetableSlotOut",
    # Leaves
    "LeaveRequestCreate",
    "LeaveStatusUpdate",
    "LeaveRequestOut",
    # Library
    "LibraryBookCreate",
    "LibraryBookOut",
    "BookIssueRequest",
    "BookReturnRequest",
    "BookLoanOut",
    "LibraryStatsOut",
    # Hostel
    "HostelBlockCreate",
    "HostelBlockOut",
    "HostelRoomCreate",
    "HostelRoomOut",
    "RoomAllocationCreate",
    "RoomCheckoutRequest",
    "RoomAllocationOut",
    # Placements
    "PlacementDriveCreate",
    "PlacementDriveOut",
    "PlacementApplicationCreate",
    "PlacementStatusUpdate",
    "PlacementApplicationOut",
    "PlacementStatsOut",
    # Transport
    "TransportRouteCreate",
    "TransportRouteOut",
    "TransportVehicleCreate",
    "TransportVehicleOut",
    "TransportPassCreate",
    "TransportPassOut",
    "TransportStatsOut",
    # Scholarships
    "ScholarshipSchemeCreate",
    "ScholarshipSchemeOut",
    "ScholarshipApplicationCreate",
    "ScholarshipReviewUpdate",
    "ScholarshipApplicationOut",
    "ScholarshipStatsOut",
    # Alumni
    "AlumniMemberCreate",
    "AlumniMemberOut",
    "AlumniMentorshipRequestCreate",
    "AlumniMentorshipStatusUpdate",
    "AlumniMentorshipRequestOut",
    # Events
    "EventCreate",
    "EventOut",
    "EventRegistrationCreate",
    "EventRegistrationOut",
    "EventStatsOut",
    # Inventory
    "AssetCreate",
    "AssetOut",
    "AssetCheckoutCreate",
    "AssetReturnUpdate",
    "AssetCheckoutOut",
    "AssetMaintenanceCreate",
    "AssetMaintenanceOut",
    "AssetStatsOut",
    # Health Center
    "HealthProfileCreate",
    "HealthProfileOut",
    "DispensaryMedicineCreate",
    "DispensaryMedicineOut",
    "PrescriptionItemCreate",
    "MedicalEncounterCreate",
    "MedicalEncounterOut",
    "MedicalCertificateCreate",
    "MedicalCertificateOut",
    "HealthStatsOut",
]
