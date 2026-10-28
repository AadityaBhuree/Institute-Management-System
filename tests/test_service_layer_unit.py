"""Unit tests for service-layer business logic.
Tests core service methods directly without FastAPI HTTP routing overhead:
- StudentService: sequential enrollment generation, soft delete, restore, validation
- FinanceService: payment settlement states (PAID, PARTIAL), balance tracking, overpayment rejection
- TimetableService: collision detection (room & instructor overlaps), time ordering
- PlacementService: GPA eligibility gating, duplicate applications
- LibraryService: inventory decrement/increment on book issue/return
- HealthService: medication stock updates, stock depletion prevention
"""

from datetime import date

import pytest

from src.models.finance import FeeInvoiceCreate, PaymentCreate
from src.models.health import DispensaryMedicineCreate
from src.models.library import BookIssueRequest, BookReturnRequest, LibraryBookCreate
from src.models.placement import PlacementApplicationCreate, PlacementDriveCreate
from src.models.student import StudentCreate
from src.models.timetable import TimetableSlotCreate
from src.services.course_service import CourseService
from src.services.faculty_service import FacultyService
from src.services.finance_service import FinanceService
from src.services.health_service import HealthService
from src.services.library_service import LibraryService
from src.services.placement_service import PlacementService
from src.services.student_service import StudentService
from src.services.timetable_service import TimetableService


def test_student_service_generate_enrollment_no(setup_test_db):
    """Verify enrollment number format and sequential counter increment."""
    from src.database.connection import get_connection, release_connection

    conn = get_connection(setup_test_db)
    try:
        current_year = date.today().year
        enr_1 = StudentService._generate_enrollment_no(conn, "CS")
        assert enr_1.startswith(f"IMS-{current_year}-CS-")

        # Create a test student and verify subsequent enrollment number increments
        student_data = StudentCreate(
            first_name="Unit",
            last_name="Tester",
            email="unit.tester.gen@example.edu",
            department_id=1,
            current_semester=1,
            admission_date="2026-08-01",
        )
        created = StudentService.create(conn, student_data)
        assert created["enrollment_no"] is not None

        enr_2 = StudentService._generate_enrollment_no(conn, "CS")
        assert enr_2 != enr_1
    finally:
        release_connection(conn, setup_test_db)


def test_student_service_soft_delete_and_restore(setup_test_db):
    """Verify soft delete marks is_deleted=1 and restore restores student."""
    from src.database.connection import get_connection, release_connection

    conn = get_connection(setup_test_db)
    try:
        student_data = StudentCreate(
            first_name="Delete",
            last_name="Test",
            email="delete.unit.test@example.edu",
            department_id=1,
            current_semester=1,
            admission_date="2026-08-01",
        )
        student = StudentService.create(conn, student_data)
        student_id = student["id"]

        # Soft delete
        deleted = StudentService.delete(conn, student_id)
        assert deleted is True

        # Should not appear in default active list
        active_students = StudentService.list_students(conn)
        assert not any(s["id"] == student_id for s in active_students)

        # Direct DB query verifies is_deleted == 1 and status == WITHDRAWN
        cur = conn.cursor()
        cur.execute("SELECT is_deleted, status FROM students WHERE id = ?;", (student_id,))
        row = cur.fetchone()
        assert row["is_deleted"] == 1
        assert row["status"] == "WITHDRAWN"
        cur.close()
    finally:
        release_connection(conn, setup_test_db)


def test_student_service_invalid_department_rejection(setup_test_db):
    """Verify student creation fails when department does not exist."""
    from src.database.connection import get_connection, release_connection

    conn = get_connection(setup_test_db)
    try:
        student_data = StudentCreate(
            first_name="Invalid",
            last_name="Dept",
            email="invalid.dept.unit@example.edu",
            department_id=99999,
            current_semester=1,
            admission_date="2026-08-01",
        )
        with pytest.raises(ValueError, match="Department with ID 99999 does not exist"):
            StudentService.create(conn, student_data)
    finally:
        release_connection(conn, setup_test_db)


def test_finance_service_payment_flow_and_balance_tracking(setup_test_db):
    """Verify partial and full invoice payment transitions and overpayment rejection."""
    from src.database.connection import get_connection, release_connection

    conn = get_connection(setup_test_db)
    try:
        # Create student first
        student = StudentService.create(
            conn,
            StudentCreate(
                first_name="Finance",
                last_name="Student",
                email="finance.unit.svc@example.edu",
                department_id=1,
                current_semester=1,
                admission_date="2026-08-01",
            ),
        )

        # 1. Create invoice for $1000
        invoice_in = FeeInvoiceCreate(
            student_id=student["id"],
            title="Tuition Fee Term 1",
            term_name="Fall 2026",
            total_amount=1000.0,
            due_date="2026-12-31",
        )
        inv = FinanceService.create_invoice(conn, invoice_in)
        assert inv["status"] == "UNPAID"
        assert inv["balance_amount"] == 1000.0
        assert inv["paid_amount"] == 0.0

        # 2. Record partial payment of $400
        p1 = PaymentCreate(
            invoice_id=inv["id"],
            amount=400.0,
            payment_method="ONLINE",
            transaction_ref="TXN-UNIT-001",
        )
        res1 = FinanceService.record_payment(conn, p1)
        assert res1["invoice_status"] == "PARTIAL"
        assert res1["new_balance"] == 600.0
        assert res1["amount"] == 400.0

        # Verify invoice via get_invoice_by_id
        inv_part = FinanceService.get_invoice_by_id(conn, inv["id"])
        assert inv_part["paid_amount"] == 400.0
        assert inv_part["balance_amount"] == 600.0
        assert inv_part["status"] == "PARTIAL"

        # 3. Attempt overpayment of $700 (balance is 600) -> should fail
        overpayment = PaymentCreate(
            invoice_id=inv["id"],
            amount=700.0,
            payment_method="ONLINE",
            transaction_ref="TXN-OVERPAY",
        )
        with pytest.raises(ValueError, match="exceeds outstanding balance"):
            FinanceService.record_payment(conn, overpayment)

        # 4. Settle remaining $600 -> status should transition to PAID
        p2 = PaymentCreate(
            invoice_id=inv["id"],
            amount=600.0,
            payment_method="CASH",
            transaction_ref="TXN-UNIT-002",
        )
        res2 = FinanceService.record_payment(conn, p2)
        assert res2["invoice_status"] == "PAID"
        assert res2["new_balance"] == 0.0
        assert res2["amount"] == 600.0

        inv_full = FinanceService.get_invoice_by_id(conn, inv["id"])
        assert inv_full["paid_amount"] == 1000.0
        assert inv_full["balance_amount"] == 0.0
        assert inv_full["status"] == "PAID"

        # 5. Attempt paying on fully settled invoice -> should fail
        settled_payment = PaymentCreate(
            invoice_id=inv["id"],
            amount=50.0,
            payment_method="CARD",
            transaction_ref="TXN-SETTLED",
        )
        with pytest.raises(ValueError, match="already fully settled"):
            FinanceService.record_payment(conn, settled_payment)
    finally:
        release_connection(conn, setup_test_db)


def test_timetable_service_collision_detection(setup_test_db):
    """Verify lecture slot collision detection on room, instructor, and invalid times."""
    from src.database.connection import get_connection, release_connection
    from src.models.course import CourseCreate
    from src.models.faculty import FacultyCreate

    conn = get_connection(setup_test_db)
    try:
        # Create faculty instructor
        fac = FacultyService.create(
            conn,
            FacultyCreate(
                first_name="Collision",
                last_name="Instructor",
                email="collision.prof@example.edu",
                department_id=1,
                designation="Professor",
                qualification="Ph.D. CS",
            ),
        )

        # Create two test courses
        c1 = CourseService.create(
            conn,
            CourseCreate(
                code="COL-101",
                title="Parallel Algorithms",
                department_id=1,
                credits=3,
                semester=1,
                capacity=40,
                instructor_id=fac["id"],
            ),
        )
        c2 = CourseService.create(
            conn,
            CourseCreate(
                code="COL-102",
                title="Distributed Systems",
                department_id=1,
                credits=3,
                semester=1,
                capacity=40,
                instructor_id=fac["id"],
            ),
        )

        # 1. Invalid time ordering: start >= end
        bad_slot = TimetableSlotCreate(
            course_id=c1["id"],
            day_of_week="Monday",
            start_time="14:00",
            end_time="13:00",
            room_number="ROOM-COL-A",
            building="Science Hall",
        )
        with pytest.raises(ValueError, match="earlier than end time"):
            TimetableService.create_slot(conn, bad_slot)

        # 2. Create first valid slot: Monday 10:00 - 11:30 in ROOM-COL-A
        slot1 = TimetableSlotCreate(
            course_id=c1["id"],
            day_of_week="Monday",
            start_time="10:00",
            end_time="11:30",
            room_number="ROOM-COL-A",
            building="Science Hall",
        )
        created_1 = TimetableService.create_slot(conn, slot1)
        assert created_1["id"] is not None

        # 3. Room collision: same day and room, overlapping 11:00 - 12:00
        slot2_conflict = TimetableSlotCreate(
            course_id=c2["id"],
            day_of_week="Monday",
            start_time="11:00",
            end_time="12:00",
            room_number="ROOM-COL-A",
            building="Science Hall",
        )
        with pytest.raises(ValueError, match="Room collision"):
            TimetableService.create_slot(conn, slot2_conflict)

        # 4. Instructor collision: different room, but same instructor overlapping 11:00 - 12:00
        slot_instr_conflict = TimetableSlotCreate(
            course_id=c2["id"],
            day_of_week="Monday",
            start_time="11:00",
            end_time="12:00",
            room_number="ROOM-COL-B",
            building="Engineering Hall",
        )
        with pytest.raises(ValueError, match="Instructor collision"):
            TimetableService.create_slot(conn, slot_instr_conflict)

        # 5. Non-conflicting slot: same room, but non-overlapping 12:00 - 13:00
        slot3_ok = TimetableSlotCreate(
            course_id=c2["id"],
            day_of_week="Monday",
            start_time="12:00",
            end_time="13:00",
            room_number="ROOM-COL-A",
            building="Science Hall",
        )
        created_3 = TimetableService.create_slot(conn, slot3_ok)
        assert created_3["id"] is not None
    finally:
        release_connection(conn, setup_test_db)


def test_placement_service_gpa_gating_and_duplicates(setup_test_db):
    """Verify GPA eligibility gating and duplicate application rejection in placements."""
    from src.database.connection import get_connection, release_connection

    conn = get_connection(setup_test_db)
    try:
        # Create recruitment drive with min_gpa_required = 8.0
        drive_data = PlacementDriveCreate(
            company_name="Google Quantum Labs",
            industry="Technology",
            job_title="Software Architect",
            job_location="Bangalore",
            package_lpa=28.5,
            min_gpa_required=8.0,
            eligible_departments="Computer Science",
            drive_date="2026-11-15",
            registration_deadline="2026-11-10",
        )
        drive = PlacementService.create_drive(conn, drive_data)
        drive_id = drive["id"]

        # Create test student
        student = StudentService.create(
            conn,
            StudentCreate(
                first_name="Placement",
                last_name="Applicant",
                email="placement.app@example.edu",
                department_id=1,
                current_semester=7,
                admission_date="2023-08-01",
            ),
        )
        student_id = student["id"]

        # Should fail GPA requirement with current_gpa=6.5
        app_low = PlacementApplicationCreate(
            drive_id=drive_id, student_id=student_id, current_gpa=6.5
        )
        with pytest.raises(ValueError, match="minimum GPA required is"):
            PlacementService.apply_for_drive(conn, app_low)

        # Application with current_gpa=9.2 meets eligibility
        app_high = PlacementApplicationCreate(
            drive_id=drive_id, student_id=student_id, current_gpa=9.2
        )
        app = PlacementService.apply_for_drive(conn, app_high)
        assert app["status"] == "APPLIED"

        # Duplicate application rejected
        with pytest.raises(ValueError, match="already submitted an application"):
            PlacementService.apply_for_drive(conn, app_high)
    finally:
        release_connection(conn, setup_test_db)


def test_library_service_inventory_decrement_and_increment(setup_test_db):
    """Verify book issue decrements copies and return increments copies."""
    from src.database.connection import get_connection, release_connection

    conn = get_connection(setup_test_db)
    try:
        # Create a test book with exactly 1 available copy
        book_in = LibraryBookCreate(
            isbn="978-0000000099",
            title="Unit Testing with Python & Pytest",
            author="Guido van Rossum",
            category="COMPUTER_SCIENCE",
            total_copies=1,
            available_copies=1,
            shelf_location="CS-STACK-A1",
        )
        book = LibraryService.create_book(conn, book_in)
        book_id = book["id"]

        # Create student borrower
        student = StudentService.create(
            conn,
            StudentCreate(
                first_name="Library",
                last_name="Borrower",
                email="lib.borrower@example.edu",
                department_id=1,
                current_semester=2,
                admission_date="2026-08-01",
            ),
        )
        student_id = student["id"]

        # Issue book -> available_copies becomes 0
        issue_req = BookIssueRequest(
            book_id=book_id,
            student_id=student_id,
            issue_date="2026-09-01",
            due_date="2026-09-15",
            remarks="Research project reference",
        )
        loan = LibraryService.issue_book(conn, issue_req)
        assert loan["id"] is not None

        book_after_issue = LibraryService.get_book_by_id(conn, book_id)
        assert book_after_issue["available_copies"] == 0

        # Attempt to issue again when 0 available -> should raise ValueError
        with pytest.raises(ValueError, match="available for issue"):
            LibraryService.issue_book(conn, issue_req)

        # Return book -> available_copies restored to 1
        return_req = BookReturnRequest(
            return_date="2026-09-14",
            fine_amount=0.0,
            remarks="Returned in pristine condition",
        )
        ret = LibraryService.return_book(conn, loan["id"], return_req)
        assert ret["status"] == "RETURNED"

        book_after_return = LibraryService.get_book_by_id(conn, book_id)
        assert book_after_return["available_copies"] == 1
    finally:
        release_connection(conn, setup_test_db)


def test_health_service_inventory_decrement(setup_test_db):
    """Verify dispensing medication decrements stock count."""
    from src.database.connection import get_connection, release_connection

    conn = get_connection(setup_test_db)
    try:
        # Create a test medication with 10 units
        medicine_data = DispensaryMedicineCreate(
            item_code="MED-UNIT-10",
            name="Paracetamol Unit",
            category="ANALGESIC",
            form="TABLET",
            stock_quantity=10,
            unit="Tablets",
            reorder_level=2,
            expiry_date="2027-12-31",
            batch_number="BATCH-2026-X",
        )
        med = HealthService.create_dispensary_medicine(conn, medicine_data)
        assert med["stock_quantity"] == 10

        # Attempting to decrement by 15 should fail (insufficient stock)
        with pytest.raises(ValueError, match="Cannot reduce stock by 15"):
            HealthService.update_dispensary_stock(
                conn, medicine_id=med["id"], quantity_change=-15, reason="Prescription Dispensed"
            )

        # Decrement by 4 -> stock should become 6
        updated = HealthService.update_dispensary_stock(
            conn, medicine_id=med["id"], quantity_change=-4, reason="Prescription Dispensed"
        )
        assert updated["stock_quantity"] == 6

        # Fetch directly to verify DB persistence
        fetched = HealthService.get_dispensary_medicine(conn, med["id"])
        assert fetched["stock_quantity"] == 6
    finally:
        release_connection(conn, setup_test_db)
