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
from src.models.course import CourseCreate, EnrollmentCreate
from src.models.faculty import FacultyCreate
from src.models.finance import FeeInvoiceCreate, FeeStructureCreate, PaymentCreate
from src.models.student import StudentCreate
from src.services.academics_service import AcademicsService
from src.services.course_service import CourseService
from src.services.faculty_service import FacultyService
from src.services.finance_service import FinanceService
from src.services.student_service import StudentService


def seed():
    """Execute complete database demonstration seeding idempotently."""
    print("=" * 60)
    print("[IMS ENTERPRISE] Seeding Comprehensive Demonstration Dataset")
    print("=" * 60)

    # 1. Initialize schema
    init_database()
    conn = get_connection()

    # 2. Seed or Load Faculty Members
    existing_faculty = FacultyService.list_faculty(conn)
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

    conn.close()
    print("\n" + "=" * 60)
    print("[SUCCESS] IMS Enterprise Demonstration Data Successfully Seeded!")
    print("=" * 60)


if __name__ == "__main__":
    seed()
