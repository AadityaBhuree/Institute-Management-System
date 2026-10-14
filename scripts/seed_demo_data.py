"""Comprehensive realistic demonstration database seeder for Institute Management System.
Populates departments, faculty, courses, students, enrollments, attendance, examinations,
exam results, fee structures, invoices, and payment audit ledger.
"""

import datetime
import random
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_connection
from src.database.init_db import init_database
from src.models.academics import (
    AttendanceBatchMark,
    ExamCreate,
    ExamGradeBatchSubmit,
    SingleAttendance,
    SingleGrade,
)
from src.models.alumni import (
    AlumniMemberCreate,
    AlumniMentorshipRequestCreate,
    AlumniMentorshipStatusUpdate,
)
from src.models.announcement import AnnouncementCreate
from src.models.course import CourseCreate, EnrollmentCreate
from src.models.faculty import FacultyCreate
from src.models.finance import FeeInvoiceCreate, FeeStructureCreate, PaymentCreate
from src.models.hostel import HostelBlockCreate, HostelRoomCreate, RoomAllocationCreate
from src.models.leave import LeaveRequestCreate, LeaveStatusUpdate
from src.models.library import BookIssueRequest, LibraryBookCreate
from src.models.placement import (
    PlacementApplicationCreate,
    PlacementDriveCreate,
    PlacementStatusUpdate,
)
from src.models.scholarship import (
    ScholarshipApplicationCreate,
    ScholarshipReviewUpdate,
    ScholarshipSchemeCreate,
)
from src.models.student import StudentCreate
from src.models.timetable import TimetableSlotCreate
from src.models.transport import (
    TransportPassCreate,
    TransportRouteCreate,
    TransportVehicleCreate,
)
from src.services.academics_service import AcademicsService
from src.services.alumni_service import AlumniService
from src.services.announcement_service import AnnouncementService
from src.services.course_service import CourseService
from src.services.faculty_service import FacultyService
from src.services.finance_service import FinanceService
from src.services.hostel_service import HostelService
from src.services.leave_service import LeaveService
from src.services.library_service import LibraryService
from src.services.placement_service import PlacementService
from src.services.scholarship_service import ScholarshipService
from src.services.student_service import StudentService
from src.services.timetable_service import TimetableService
from src.services.transport_service import TransportService


def seed():
    """Execute complete database demonstration seeding idempotently."""
    print("=" * 60)
    print("[IMS ENTERPRISE] Seeding Comprehensive Demonstration Dataset")
    print("=" * 60)

    # 1. Initialize schema
    init_database()
    conn = get_connection()
    today = datetime.date.today()

    # 2. Seed or Load Faculty Members
    existing_faculty = FacultyService.list_faculty(conn)
    faculty_records = existing_faculty
    faculty_ids = [f["id"] for f in existing_faculty]

    if not faculty_ids:
        print("\n[+] Seeding Faculty Roster...")
        faculty_data = [
            (
                "Dr. Alan",
                "Turing",
                "alan.turing@institute.edu",
                "+1-555-0101",
                1,
                "Professor",
                "Ph.D. Cambridge",
            ),
            (
                "Dr. Ada",
                "Lovelace",
                "ada.lovelace@institute.edu",
                "+1-555-0102",
                1,
                "Associate Professor",
                "Ph.D. London",
            ),
            (
                "Dr. Claude",
                "Shannon",
                "claude.shannon@institute.edu",
                "+1-555-0103",
                2,
                "Professor",
                "Ph.D. MIT",
            ),
            (
                "Dr. Nikola",
                "Tesla",
                "nikola.tesla@institute.edu",
                "+1-555-0104",
                2,
                "Assistant Professor",
                "M.Tech Graz",
            ),
            (
                "Dr. James",
                "Watt",
                "james.watt@institute.edu",
                "+1-555-0105",
                3,
                "Professor",
                "D.Sc. Glasgow",
            ),
            (
                "Dr. Isambard",
                "Brunel",
                "isambard.brunel@institute.edu",
                "+1-555-0106",
                4,
                "Professor",
                "Ph.D. Paris",
            ),
            (
                "Dr. Michael",
                "Porter",
                "michael.porter@institute.edu",
                "+1-555-0107",
                5,
                "Professor",
                "Ph.D. Harvard",
            ),
            (
                "Dr. Grace",
                "Hopper",
                "grace.hopper@institute.edu",
                "+1-555-0108",
                1,
                "Distinguished Lecturer",
                "Ph.D. Yale",
            ),
        ]
        for first, last, email, phone, dept_id, title, qual in faculty_data:
            try:
                f = FacultyService.create(
                    conn,
                    FacultyCreate(
                        first_name=first,
                        last_name=last,
                        email=email,
                        phone=phone,
                        department_id=dept_id,
                        designation=title,
                        qualification=qual,
                    ),
                )
                faculty_ids.append(f["id"])
                print(f"   * Added Faculty: {first} {last} ({title})")
            except ValueError:
                pass
    else:
        print(f"\n[INFO] {len(faculty_ids)} faculty members already present in directory.")

    # 3. Seed or Load Courses
    existing_courses = CourseService.list_courses(conn)
    course_ids = [c["id"] for c in existing_courses]

    if len(course_ids) < 5:
        print("\n[+] Seeding Course Catalog...")
        courses_data = [
            (
                "CS101",
                "Introduction to Computing & Algorithms",
                1,
                4,
                1,
                50,
                faculty_ids[0] if faculty_ids else None,
            ),
            (
                "CS201",
                "Data Structures & Modern Algorithms",
                1,
                4,
                3,
                45,
                faculty_ids[1] if len(faculty_ids) > 1 else None,
            ),
            (
                "CS301",
                "Operating Systems & Concurrency",
                1,
                3,
                5,
                40,
                faculty_ids[7] if len(faculty_ids) > 7 else None,
            ),
            (
                "EC101",
                "Circuit Theory & Network Analysis",
                2,
                4,
                1,
                45,
                faculty_ids[2] if len(faculty_ids) > 2 else None,
            ),
            (
                "EC201",
                "Digital Signal Processing",
                2,
                3,
                3,
                40,
                faculty_ids[3] if len(faculty_ids) > 3 else None,
            ),
            (
                "ME101",
                "Engineering Mechanics & Statics",
                3,
                4,
                1,
                45,
                faculty_ids[4] if len(faculty_ids) > 4 else None,
            ),
            (
                "CE101",
                "Structural Mechanics & Materials",
                4,
                4,
                1,
                40,
                faculty_ids[5] if len(faculty_ids) > 5 else None,
            ),
            (
                "MBA101",
                "Managerial Economics & Strategy",
                5,
                3,
                1,
                55,
                faculty_ids[6] if len(faculty_ids) > 6 else None,
            ),
        ]
        for code, title, dept_id, credits_val, sem, cap, inst_id in courses_data:
            try:
                c = CourseService.create(
                    conn,
                    CourseCreate(
                        code=code,
                        title=title,
                        department_id=dept_id,
                        credits=credits_val,
                        semester=sem,
                        capacity=cap,
                        instructor_id=inst_id,
                    ),
                )
                if c["id"] not in course_ids:
                    course_ids.append(c["id"])
                print(f"   * Added Course: {code} - {title}")
            except ValueError:
                pass
    else:
        print(f"\n[INFO] {len(course_ids)} courses already present in catalog.")

    # 4. Seed or Load Scholars
    student_records = StudentService.list_students(conn, limit=200)

    if len(student_records) < 10:
        print("\n[+] Seeding Student Admissions...")
        students_data = [
            ("Aarav", "Verma", "aarav.verma@example.edu", "+1-555-0201", "2004-05-14", 1, 1),
            ("Ananya", "Iyer", "ananya.iyer@example.edu", "+1-555-0202", "2004-09-20", 1, 1),
            ("Dev", "Patel", "dev.patel@example.edu", "+1-555-0203", "2003-11-10", 1, 3),
            ("Diya", "Nair", "diya.nair@example.edu", "+1-555-0204", "2003-03-25", 1, 3),
            ("Ishaan", "Gupta", "ishaan.gupta@example.edu", "+1-555-0205", "2002-07-08", 1, 5),
            ("Khushi", "Mehta", "khushi.mehta@example.edu", "+1-555-0206", "2004-12-15", 2, 1),
            ("Manish", "Reddy", "manish.reddy@example.edu", "+1-555-0207", "2004-02-18", 2, 1),
            ("Neha", "Joshi", "neha.joshi@example.edu", "+1-555-0208", "2003-08-30", 2, 3),
            ("Pranav", "Chopra", "pranav.chopra@example.edu", "+1-555-0209", "2004-06-22", 3, 1),
            ("Rhea", "Sen", "rhea.sen@example.edu", "+1-555-0210", "2004-10-05", 3, 1),
            ("Siddharth", "Malhotra", "siddharth.m@example.edu", "+1-555-0211", "2004-04-12", 4, 1),
            ("Tanvi", "Bhatia", "tanvi.b@example.edu", "+1-555-0212", "2004-01-19", 4, 1),
            ("Varun", "Kapoor", "varun.k@example.edu", "+1-555-0213", "2001-09-14", 5, 1),
            ("Zoya", "Khan", "zoya.k@example.edu", "+1-555-0214", "2002-05-18", 5, 1),
        ]
        for first, last, email, phone, dob, dept_id, sem in students_data:
            try:
                s = StudentService.create(
                    conn,
                    StudentCreate(
                        first_name=first,
                        last_name=last,
                        email=email,
                        phone=phone,
                        dob=dob,
                        department_id=dept_id,
                        current_semester=sem,
                    ),
                )
                student_records.append(s)
                print(f"   * Enrolled Scholar: {first} {last} ({s['enrollment_no']})")
            except ValueError:
                pass
    else:
        print(f"\n[INFO] {len(student_records)} students already enrolled in registry.")

    # 5. Ensure Student Course Enrollments
    print("\n[+] Verifying Curriculum Enrollments...")
    enrolled_count = 0
    for s in student_records:
        dept = s["department_id"]
        sem = s["current_semester"]
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM courses WHERE department_id = ? AND semester = ?;",
            (dept, sem),
        )
        matched_courses = cursor.fetchall()
        cursor.close()

        for c_row in matched_courses:
            try:
                CourseService.enroll_student(
                    conn,
                    EnrollmentCreate(
                        student_id=s["id"],
                        course_id=c_row["id"],
                        academic_year="2026-2027",
                        semester=sem,
                    ),
                )
                enrolled_count += 1
            except ValueError:
                pass
    print(f"   * Curriculum mappings updated ({enrolled_count} new enrollments processed).")

    # 6. Seed Attendance Sessions if needed
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS total FROM attendance_records;")
    att_count = cursor.fetchone()["total"]
    cursor.close()

    if att_count < 10:
        print("\n[+] Recording Historical Attendance Registers...")
        today = datetime.date.today()
        sample_dates = [(today - datetime.timedelta(days=d)).isoformat() for d in [14, 7, 3, 1]]

        for c_id in course_ids[:4]:
            enrolled_res = CourseService.list_course_students(conn, c_id)
            if not enrolled_res:
                continue
            for dt in sample_dates:
                records = []
                for st in enrolled_res:
                    st_stat = random.choices(
                        ["PRESENT", "ABSENT", "LATE"], weights=[0.8, 0.1, 0.1]
                    )[0]
                    records.append(SingleAttendance(student_id=st["id"], status=st_stat))
                try:
                    AcademicsService.mark_attendance_batch(
                        conn,
                        AttendanceBatchMark(
                            course_id=c_id,
                            attendance_date=dt,
                            records=records,
                        ),
                    )
                except ValueError:
                    pass
        print("   * Daily attendance session archives created.")
    else:
        print(f"\n[INFO] {att_count} attendance records already logged.")

    # 7. Seed Examinations & Grades if needed
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS total FROM exam_results;")
    results_count = cursor.fetchone()["total"]
    cursor.close()

    if results_count == 0:
        exams_list = AcademicsService.list_examinations(conn)
        if not exams_list and course_ids:
            for c_id in course_ids[:3]:
                enrolled_students = CourseService.list_course_students(conn, c_id)
                if not enrolled_students:
                    continue
                exam = AcademicsService.create_examination(
                    conn,
                    ExamCreate(
                        course_id=c_id,
                        title="Course Unit Evaluation - Midterm",
                        exam_type="MIDTERM",
                        exam_date=(today - datetime.timedelta(days=7)).isoformat(),
                        max_marks=100.0,
                        passing_marks=40.0,
                        weightage_percent=30.0,
                    ),
                )
                exams_list.append(exam)

        for ex in exams_list:
            enrolled_students = CourseService.list_course_students(conn, ex["course_id"])
            if not enrolled_students:
                continue
            grades_batch = [
                SingleGrade(
                    student_id=st["id"],
                    marks_obtained=round(random.uniform(62.0, 96.0), 1),
                    remarks="Strong analytical understanding",
                )
                for st in enrolled_students
            ]
            try:
                AcademicsService.submit_exam_grades_batch(
                    conn,
                    ex["id"],
                    ExamGradeBatchSubmit(exam_id=ex["id"], grades=grades_batch),
                )
                print(f"   * Exam #{ex['id']} graded ({len(grades_batch)} scholars evaluated).")
            except Exception:
                pass
    else:
        print(f"\n[INFO] {results_count} exam grading dossiers already on record.")

    # 8. Seed Fee Structures if needed
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS total FROM fee_structures;")
    fs_count = cursor.fetchone()["total"]
    cursor.close()

    if fs_count == 0:
        print("\n[+] Setting Up Departmental Fee Schedules...")
        fee_structures = [
            (1, 1, "Tuition & Computational Services", 3200.0),
            (1, 3, "Advanced Engineering & Lab Access", 3400.0),
            (2, 1, "Electronics Lab & Tuition", 3100.0),
            (3, 1, "Mechanical Workshop & Tuition", 2900.0),
            (5, 1, "Executive Management Tuition", 4500.0),
        ]
        for dept_id, sem, f_type, amt in fee_structures:
            try:
                FinanceService.create_fee_structure(
                    conn,
                    FeeStructureCreate(
                        department_id=dept_id,
                        semester=sem,
                        fee_type=f_type,
                        amount=amt,
                        academic_year="2026-2027",
                    ),
                )
            except ValueError:
                pass
        print("   * Departmental fee schedules recorded.")
    else:
        print(f"\n[INFO] {fs_count} fee structures already active.")

    # 9. Seed Invoices and Real Payments if needed
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS total FROM fee_invoices;")
    inv_count = cursor.fetchone()["total"]
    cursor.close()

    if inv_count == 0 and student_records:
        print("\n[+] Issuing Invoices & Recording Bursar Ledger Receipts...")
        for idx, s in enumerate(student_records[:10]):
            amt = 3200.0 if s["department_id"] == 1 else 3000.0
            # Varied due dates: some in future, one in past to test OVERDUE
            due = (
                (today - datetime.timedelta(days=15)).isoformat()
                if idx == 0
                else (today + datetime.timedelta(days=25)).isoformat()
            )
            inv = FinanceService.create_invoice(
                conn,
                FeeInvoiceCreate(
                    student_id=s["id"],
                    title="Fall 2026 Academic Fee & Campus Services",
                    term_name="Fall 2026",
                    total_amount=amt,
                    due_date=due,
                ),
            )

            # Record payments for varied statuses
            if idx % 3 == 0:
                # Full payment
                FinanceService.record_payment(
                    conn,
                    PaymentCreate(
                        invoice_id=inv["id"],
                        amount=amt,
                        payment_method="ONLINE",
                        transaction_ref=f"TXN-STRIPE-{idx}992",
                        notes="Settled via student online portal",
                    ),
                )
            elif idx % 3 == 1:
                # Partial payment
                FinanceService.record_payment(
                    conn,
                    PaymentCreate(
                        invoice_id=inv["id"],
                        amount=round(amt / 2, 2),
                        payment_method="UPI",
                        transaction_ref=f"UPI-INSTANT-{idx}14",
                        notes="Installment 1 received",
                    ),
                )

        print("   * Student invoices and payment transactions populated.")
    else:
        print(f"\n[INFO] {inv_count} fee invoices already in ledger.")

    # 10. Seed Campus Announcements
    existing_notices = AnnouncementService.list_announcements(conn)
    if not existing_notices:
        print("\n[+] Seeding Campus Announcements & Bulletins...")
        sample_notices = [
            (
                "Fall 2026 End-Semester Examination Schedule Released",
                "The official schedule for midterms and final examinations has been posted. Please review course examination timings in your Scholar Portal.",
                "EXAM",
                "STUDENTS",
                "HIGH",
                "Office of the Controller of Examinations",
            ),
            (
                "Bursar Office: Semester Tuition Clearance Deadline",
                "All enrolled students must clear outstanding term invoices or submit installment requests before the 30th of the month.",
                "FEES",
                "STUDENTS",
                "HIGH",
                "University Bursar Office",
            ),
            (
                "Annual National Robotics & AI Symposium 2026",
                "The Department of Computer Science & Engineering invites all scholars and faculty to submit research abstracts for the upcoming symposium.",
                "EVENT",
                "ALL",
                "NORMAL",
                "Department of Computer Science",
            ),
            (
                "Faculty Curriculum Senate: Board of Studies Meeting",
                "Quarterly review meeting regarding syllabus updates, elective course credits, and lab accreditation.",
                "ACADEMIC",
                "FACULTY",
                "NORMAL",
                "Dean of Academic Affairs",
            ),
        ]
        for title, content, cat, aud, prio, author in sample_notices:
            AnnouncementService.create(
                conn,
                AnnouncementCreate(
                    title=title,
                    content=content,
                    category=cat,
                    target_audience=aud,
                    priority=prio,
                    author_name=author,
                ),
            )
        print("   * Campus bulletins and notices populated.")

    # 11. Seed Lecture Timetable Slots
    existing_slots = TimetableService.list_slots(conn)
    if not existing_slots and course_ids:
        print("\n[+] Seeding Weekly Academic Lecture Timetable...")
        schedule_templates = [
            ("Monday", "09:00", "10:30", "LH-101", "Main Academic Block"),
            ("Monday", "11:00", "12:30", "LH-102", "Main Academic Block"),
            ("Tuesday", "09:00", "10:30", "LH-101", "Main Academic Block"),
            ("Tuesday", "14:00", "15:30", "Lab-201", "Turing Computing Wing"),
            ("Wednesday", "10:00", "11:30", "LH-103", "Main Academic Block"),
            ("Thursday", "09:00", "10:30", "LH-102", "Main Academic Block"),
            ("Friday", "11:00", "12:30", "LH-101", "Main Academic Block"),
        ]
        for idx, (day, start, end, room, bld) in enumerate(schedule_templates):
            c_id = course_ids[idx % len(course_ids)]
            try:
                TimetableService.create_slot(
                    conn,
                    TimetableSlotCreate(
                        course_id=c_id,
                        day_of_week=day,
                        start_time=start,
                        end_time=end,
                        room_number=room,
                        building=bld,
                    ),
                )
            except Exception:
                pass
        print("   * Weekly lecture matrix populated.")

    # 12. Seed Institutional Leave Requests
    existing_leaves = LeaveService.list_leaves(conn)
    student_records = StudentService.list_students(conn)
    if not existing_leaves and student_records:
        print("\n[+] Seeding Institutional Leave & Absence Records...")
        s1 = student_records[0]
        s2 = student_records[1] if len(student_records) > 1 else student_records[0]

        leave_samples = [
            (
                "STUDENT",
                s1["id"],
                f"{s1['first_name']} {s1['last_name']}",
                "SICK",
                (today - datetime.timedelta(days=10)).isoformat(),
                (today - datetime.timedelta(days=7)).isoformat(),
                "Recovering from seasonal viral flu under physician care.",
                "APPROVED",
                "Medical certificate verified and approved.",
            ),
            (
                "STUDENT",
                s2["id"],
                f"{s2['first_name']} {s2['last_name']}",
                "CASUAL",
                (today + datetime.timedelta(days=3)).isoformat(),
                (today + datetime.timedelta(days=5)).isoformat(),
                "Attending elder sister's wedding ceremony.",
                "PENDING",
                None,
            ),
        ]
        if faculty_records:
            f1 = faculty_records[0]
            leave_samples.append((
                "FACULTY",
                f1["id"],
                f"{f1['first_name']} {f1['last_name']}",
                "ACADEMIC",
                (today + datetime.timedelta(days=12)).isoformat(),
                (today + datetime.timedelta(days=15)).isoformat(),
                "Presenting peer-reviewed paper at IEEE International Computing Conference.",
                "APPROVED",
                "Duty leave sanctioned. Substitute instructor arranged.",
            ))

        for app_type, app_id, name, l_type, s_date, e_date, rsn, st, rem in leave_samples:
            created = LeaveService.submit_leave(
                conn,
                LeaveRequestCreate(
                    applicant_type=app_type,
                    applicant_id=app_id,
                    applicant_name=name,
                    leave_type=l_type,
                    start_date=s_date,
                    end_date=e_date,
                    reason=rsn,
                ),
            )
            if st != "PENDING":
                LeaveService.update_status(
                    conn,
                    created["id"],
                    LeaveStatusUpdate(
                        status=st,
                        review_remarks=rem,
                        reviewed_by="Academic Dean",
                    ),
                )
        print("   * Student and faculty leave petitions populated.")

    # 13. Seed Campus Library Monograph Catalog & Circulation Loans
    existing_books = LibraryService.list_books(conn)
    if not existing_books and student_records:
        print("\n[+] Seeding Library Monograph Catalog & Circulation...")
        book_data = [
            (
                "978-0131103627",
                "The C Programming Language",
                "Brian W. Kernighan, Dennis M. Ritchie",
                "COMPUTER_SCIENCE",
                5,
                "Stack CS-A1",
                "Prentice Hall",
                "2nd Ed",
                1988,
            ),
            (
                "978-0262033848",
                "Introduction to Algorithms",
                "Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, Clifford Stein",
                "COMPUTER_SCIENCE",
                8,
                "Stack CS-B2",
                "MIT Press",
                "3rd Ed",
                2009,
            ),
            (
                "978-0132350884",
                "Clean Code: A Handbook of Agile Software Craftsmanship",
                "Robert C. Martin",
                "COMPUTER_SCIENCE",
                6,
                "Stack CS-C3",
                "Prentice Hall",
                "1st Ed",
                2008,
            ),
            (
                "978-0073380377",
                "Microelectronic Circuits",
                "Adel S. Sedra, Kenneth C. Smith",
                "ENGINEERING",
                4,
                "Stack EE-A1",
                "Oxford University Press",
                "7th Ed",
                2014,
            ),
            (
                "978-0134444321",
                "Principles of Neural Science",
                "Eric R. Kandel, James H. Schwartz",
                "BIOTECH",
                3,
                "Stack BIO-D4",
                "McGraw-Hill",
                "5th Ed",
                2012,
            ),
        ]
        created_books = []
        for isbn, title, author, cat, copies, loc, pub, ed, yr in book_data:
            b = LibraryService.create_book(
                conn,
                LibraryBookCreate(
                    isbn=isbn,
                    title=title,
                    author=author,
                    category=cat,
                    total_copies=copies,
                    shelf_location=loc,
                    publisher=pub,
                    edition=ed,
                    publication_year=yr,
                ),
            )
            created_books.append(b)

        # Issue active loan to student
        if created_books and len(student_records) > 0:
            LibraryService.issue_book(
                conn,
                BookIssueRequest(
                    book_id=created_books[0]["id"],
                    student_id=student_records[0]["id"],
                    issue_date=(today - datetime.timedelta(days=5)).isoformat(),
                    due_date=(today + datetime.timedelta(days=9)).isoformat(),
                    remarks="Assigned for Advanced Systems Lab",
                ),
            )
        print("   * Library books and circulation loans populated.")

    # 14. Seed Campus Residential Halls & Allocations
    existing_blocks = HostelService.list_blocks(conn)
    if not existing_blocks and student_records:
        print("\n[+] Seeding Campus Residential Halls & Bed Allocations...")
        block1 = HostelService.create_block(
            conn,
            HostelBlockCreate(
                block_name="Ramanujan Hall of Residence",
                gender_type="MALE",
                total_rooms=20,
                warden_name="Prof. S. Chandrasekhar",
                warden_contact="+91 94444 11223",
            ),
        )
        block2 = HostelService.create_block(
            conn,
            HostelBlockCreate(
                block_name="Kalpana Chawla Hall of Residence",
                gender_type="FEMALE",
                total_rooms=20,
                warden_name="Dr. Sunita Williams",
                warden_contact="+91 94444 22334",
            ),
        )

        r1 = HostelService.create_room(
            conn,
            HostelRoomCreate(
                block_id=block1["id"],
                room_number="101",
                room_type="SINGLE",
                capacity=1,
                floor=1,
                fee_per_semester=1800.0,
            ),
        )
        HostelService.create_room(
            conn,
            HostelRoomCreate(
                block_id=block1["id"],
                room_number="102",
                room_type="DOUBLE",
                capacity=2,
                floor=1,
                fee_per_semester=1200.0,
            ),
        )
        HostelService.create_room(
            conn,
            HostelRoomCreate(
                block_id=block2["id"],
                room_number="201",
                room_type="DOUBLE",
                capacity=2,
                floor=2,
                fee_per_semester=1200.0,
            ),
        )

        # Allocate room 101 to student 0
        if len(student_records) > 0:
            HostelService.allocate_room(
                conn,
                RoomAllocationCreate(
                    room_id=r1["id"],
                    student_id=student_records[0]["id"],
                    academic_year="2026-2027",
                    check_in_date=(today - datetime.timedelta(days=30)).isoformat(),
                    remarks="Room key issued, biometric registered.",
                ),
            )
        print("   * Residential blocks, rooms, and bed allocations populated.")

    # 15. Seed Corporate Placement Drives & Candidate Applications
    existing_drives = PlacementService.list_drives(conn)
    if not existing_drives and student_records:
        print("\n[+] Seeding Corporate Placement Drives & Applications...")
        d1 = PlacementService.create_drive(
            conn,
            PlacementDriveCreate(
                company_name="Google DeepMind",
                industry="Artificial Intelligence & Cloud",
                job_title="Research Systems Software Engineer",
                job_location="Bengaluru / Hybrid",
                package_lpa=36.0,
                min_gpa_required=8.0,
                eligible_departments="CSE, ECE",
                drive_date=(today + datetime.timedelta(days=25)).isoformat(),
                registration_deadline=(today + datetime.timedelta(days=10)).isoformat(),
                status="ACTIVE",
            ),
        )
        d2 = PlacementService.create_drive(
            conn,
            PlacementDriveCreate(
                company_name="NVIDIA Corporation",
                industry="GPU Computing & Semiconductors",
                job_title="CUDA Systems Architect",
                job_location="Bengaluru / On-Site",
                package_lpa=32.0,
                min_gpa_required=7.5,
                eligible_departments="CSE, ECE",
                drive_date=(today + datetime.timedelta(days=35)).isoformat(),
                registration_deadline=(today + datetime.timedelta(days=15)).isoformat(),
                status="ACTIVE",
            ),
        )
        PlacementService.create_drive(
            conn,
            PlacementDriveCreate(
                company_name="Microsoft Azure",
                industry="Distributed Cloud Systems",
                job_title="Cloud Infrastructure Engineer",
                job_location="Hyderabad / Hybrid",
                package_lpa=28.5,
                min_gpa_required=7.0,
                eligible_departments="ALL",
                drive_date=(today + datetime.timedelta(days=45)).isoformat(),
                registration_deadline=(today + datetime.timedelta(days=20)).isoformat(),
                status="UPCOMING",
            ),
        )

        # Register applications
        if len(student_records) > 0:
            app1 = PlacementService.apply_for_drive(
                conn,
                PlacementApplicationCreate(
                    drive_id=d1["id"],
                    student_id=student_records[0]["id"],
                    current_gpa=9.40,
                    resume_link="https://dossier.org/scholar1_resume.pdf",
                    remarks="Honours scholar in distributed computing",
                ),
            )
            # Advance to SELECTED
            PlacementService.update_application_status(
                conn,
                app1["id"],
                PlacementStatusUpdate(
                    status="SELECTED",
                    interview_date=(today - datetime.timedelta(days=2)).isoformat(),
                    offer_package_lpa=38.0,
                    remarks="Exceptional architecture interview, signing bonus extended",
                ),
            )

        if len(student_records) > 1:
            app2 = PlacementService.apply_for_drive(
                conn,
                PlacementApplicationCreate(
                    drive_id=d2["id"],
                    student_id=student_records[1]["id"],
                    current_gpa=8.65,
                    resume_link="https://dossier.org/scholar2_resume.pdf",
                    remarks="Parallel systems and GPU lab specialist",
                ),
            )
            PlacementService.update_application_status(
                conn,
                app2["id"],
                PlacementStatusUpdate(
                    status="TECHNICAL_ROUND",
                    interview_date=(today + datetime.timedelta(days=5)).isoformat(),
                    remarks="Shortlisted for live algorithmic systems round",
                ),
            )
        print("   * Corporate placement drives, candidate applications, and offers populated.")

    # 16. Seed Campus Transport Fleet & Passes
    existing_routes = TransportService.list_routes(conn)
    if not existing_routes:
        print("\n[+] Seeding Campus Transport Fleet & Routes...")
        r1 = TransportService.create_route(
            conn,
            TransportRouteCreate(
                route_name="Route 101 - North Tech Express",
                source="North Metro Terminal",
                destination="Central Campus Gate 1",
                total_stops=6,
                fare_per_semester=12000.0,
                status="ACTIVE",
            ),
        )
        r2 = TransportService.create_route(
            conn,
            TransportRouteCreate(
                route_name="Route 202 - Southern Suburbs & Ring Road",
                source="South Suburb Station",
                destination="Central Campus Gate 2",
                total_stops=8,
                fare_per_semester=14500.0,
                status="ACTIVE",
            ),
        )

        TransportService.create_vehicle(
            conn,
            TransportVehicleCreate(
                route_id=r1["id"],
                vehicle_number="KA-01-EQ-9801",
                driver_name="Rajesh Kumar",
                driver_phone="+1-555-8801",
                capacity=50,
                status="ACTIVE",
            ),
        )
        TransportService.create_vehicle(
            conn,
            TransportVehicleCreate(
                route_id=r2["id"],
                vehicle_number="KA-01-EQ-9802",
                driver_name="Mahesh Shinde",
                driver_phone="+1-555-8802",
                capacity=40,
                status="ACTIVE",
            ),
        )

        if len(student_records) > 0:
            TransportService.issue_transit_pass(
                conn,
                TransportPassCreate(
                    student_id=student_records[0]["id"],
                    route_id=r1["id"],
                    pickup_stop="Tech Corridor",
                    academic_year="2026-2027",
                    valid_until=(today + datetime.timedelta(days=180)).isoformat(),
                ),
            )
        print("   * Transport routes, fleet vehicles, and transit passes populated.")

    # 17. Seed Scholarships & Financial Grants
    existing_schemes = ScholarshipService.list_schemes(conn)
    if not existing_schemes:
        print("\n[+] Seeding Scholarships, Grants & Financial Aid...")
        s1 = ScholarshipService.create_scheme(
            conn,
            ScholarshipSchemeCreate(
                scheme_name="Presidential Merit Fellowship",
                sponsor_type="INSTITUTIONAL",
                award_amount=100000.0,
                min_gpa_required=9.0,
                max_family_income=1200000.0,
                eligible_category="MERIT_SCHOLARS",
                status="ACTIVE",
            ),
        )
        s2 = ScholarshipService.create_scheme(
            conn,
            ScholarshipSchemeCreate(
                scheme_name="Need-Based Financial Equity Grant",
                sponsor_type="GOVERNMENT",
                award_amount=65000.0,
                min_gpa_required=7.5,
                max_family_income=500000.0,
                eligible_category="NEED_BASED",
                status="ACTIVE",
            ),
        )

        if len(student_records) > 0:
            app1 = ScholarshipService.apply_for_scholarship(
                conn,
                ScholarshipApplicationCreate(
                    scheme_id=s1["id"],
                    student_id=student_records[0]["id"],
                    current_gpa=9.40,
                    annual_family_income=450000.0,
                ),
            )
            ScholarshipService.review_application(
                conn,
                app1["id"],
                ScholarshipReviewUpdate(
                    status="DISBURSED",
                    review_remarks="Exceptional academic performance and faculty recommendations. Grant fully disbursed.",
                    disbursed_amount=100000.0,
                ),
            )

        if len(student_records) > 1:
            app2 = ScholarshipService.apply_for_scholarship(
                conn,
                ScholarshipApplicationCreate(
                    scheme_id=s2["id"],
                    student_id=student_records[1]["id"],
                    current_gpa=8.65,
                    annual_family_income=380000.0,
                ),
            )
            ScholarshipService.review_application(
                conn,
                app2["id"],
                ScholarshipReviewUpdate(
                    status="APPROVED",
                    review_remarks="Income eligibility and GPA verified. Approved for upcoming disbursement cycle.",
                    disbursed_amount=None,
                ),
            )
        print(
            "   * Scholarship grant schemes, student applications, and bursar disbursements populated."
        )

    # 18. Seed Alumni Network & Career Mentorship
    existing_alumni = AlumniService.list_alumni(conn)
    if not existing_alumni:
        print("\n[+] Seeding Alumni Network & Mentorship Directory...")
        dept_id = faculty_records[0]["department_id"] if faculty_records else 1

        a1 = AlumniService.register_alumnus(
            conn,
            AlumniMemberCreate(
                student_id=None,
                full_name="Priya Nair",
                email="priya.nair@alumni.edu",
                phone="+1-555-9011",
                graduation_year=2020,
                degree="B.Tech Computer Science",
                department_id=dept_id,
                current_company="Google",
                job_title="Staff Infrastructure Engineer",
                city="Sunnyvale, CA",
                linkedin_url="https://linkedin.com/in/priyanair-mock",
                mentorship_status="AVAILABLE",
            ),
        )
        AlumniService.register_alumnus(
            conn,
            AlumniMemberCreate(
                student_id=None,
                full_name="Dev Malhotra",
                email="dev.malhotra@alumni.edu",
                phone="+1-555-9012",
                graduation_year=2021,
                degree="B.Tech Electronics & Comm",
                department_id=dept_id,
                current_company="NVIDIA",
                job_title="Senior Hardware Systems Architect",
                city="Santa Clara, CA",
                linkedin_url="https://linkedin.com/in/devmalhotra-mock",
                mentorship_status="BUSY",
            ),
        )
        AlumniService.register_alumnus(
            conn,
            AlumniMemberCreate(
                student_id=None,
                full_name="Ananya Deshmukh",
                email="ananya.deshmukh@alumni.edu",
                phone="+1-555-9013",
                graduation_year=2019,
                degree="B.Tech Computer Science",
                department_id=dept_id,
                current_company="Stripe",
                job_title="VP of Engineering",
                city="San Francisco, CA",
                linkedin_url="https://linkedin.com/in/ananyad-mock",
                mentorship_status="AVAILABLE",
            ),
        )

        if len(student_records) > 0:
            req1 = AlumniService.request_mentorship(
                conn,
                AlumniMentorshipRequestCreate(
                    alumni_id=a1["id"],
                    student_id=student_records[0]["id"],
                    mentorship_topic="Distributed Consensus & Large-Scale Systems Interview Prep",
                    notes="Preparing for cloud infrastructure roles; seeking guidance on large-scale system design.",
                ),
            )
            AlumniService.update_mentorship_status(
                conn,
                req1["id"],
                AlumniMentorshipStatusUpdate(
                    status="ACCEPTED",
                    notes="Session scheduled for Friday 5:00 PM PST. Review Raft paper beforehand.",
                ),
            )
        print("   * Alumni directory members and student career mentorship connections populated.")

    conn.close()
    print("\n" + "=" * 60)
    print("[SUCCESS] IMS Enterprise Demonstration Data Successfully Seeded!")
    print("=" * 60)


if __name__ == "__main__":
    seed()
