-- Institute Management System - SQLite Normalized DDL Schema
-- Foreign keys and WAL mode must be enabled by connection pragmas.

PRAGMA foreign_keys = ON;

-- 1. Departments Directory
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Faculty Directory
CREATE TABLE IF NOT EXISTS faculty (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    faculty_id TEXT NOT NULL UNIQUE,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT,
    department_id INTEGER NOT NULL REFERENCES departments(id) ON DELETE RESTRICT,
    designation TEXT NOT NULL DEFAULT 'Assistant Professor',
    qualification TEXT,
    hire_date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'ON_LEAVE', 'RESIGNED', 'RETIRED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Courses Catalog
CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    department_id INTEGER NOT NULL REFERENCES departments(id) ON DELETE RESTRICT,
    credits INTEGER NOT NULL DEFAULT 3 CHECK(credits > 0),
    semester INTEGER NOT NULL DEFAULT 1 CHECK(semester BETWEEN 1 AND 8),
    capacity INTEGER NOT NULL DEFAULT 60 CHECK(capacity > 0),
    syllabus_summary TEXT,
    instructor_id INTEGER REFERENCES faculty(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Students Directory & Admissions
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    enrollment_no TEXT NOT NULL UNIQUE,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT,
    dob DATE,
    gender TEXT CHECK(gender IN ('Male', 'Female', 'Other', 'Prefer Not to Say')),
    blood_group TEXT,
    address TEXT,
    emergency_contact TEXT,
    department_id INTEGER NOT NULL REFERENCES departments(id) ON DELETE RESTRICT,
    current_semester INTEGER NOT NULL DEFAULT 1 CHECK(current_semester BETWEEN 1 AND 8),
    admission_date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'ENROLLED' CHECK(status IN ('ENROLLED', 'PENDING', 'PROBATION', 'SUSPENDED', 'GRADUATED', 'WITHDRAWN')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Course Enrollments
CREATE TABLE IF NOT EXISTS course_enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE RESTRICT,
    academic_year TEXT NOT NULL,
    semester INTEGER NOT NULL CHECK(semester BETWEEN 1 AND 8),
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'COMPLETED', 'DROPPED')),
    enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(student_id, course_id, academic_year, semester)
);

-- 6. Attendance Tracking
CREATE TABLE IF NOT EXISTS attendance_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    attendance_date DATE NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('PRESENT', 'ABSENT', 'LATE', 'EXCUSED')),
    remarks TEXT,
    recorded_by INTEGER REFERENCES faculty(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(student_id, course_id, attendance_date)
);

-- 7. Examinations
CREATE TABLE IF NOT EXISTS examinations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    exam_type TEXT NOT NULL CHECK(exam_type IN ('MIDTERM', 'FINAL', 'QUIZ', 'LAB_ASSESSMENT', 'ASSIGNMENT')),
    exam_date DATE NOT NULL,
    max_marks REAL NOT NULL DEFAULT 100.0 CHECK(max_marks > 0),
    passing_marks REAL NOT NULL DEFAULT 40.0 CHECK(passing_marks >= 0),
    weightage_percent REAL NOT NULL DEFAULT 100.0 CHECK(weightage_percent > 0 AND weightage_percent <= 100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. Exam Results & Grades
CREATE TABLE IF NOT EXISTS exam_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id INTEGER NOT NULL REFERENCES examinations(id) ON DELETE CASCADE,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    marks_obtained REAL NOT NULL CHECK(marks_obtained >= 0),
    grade_letter TEXT NOT NULL,
    remarks TEXT,
    evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(exam_id, student_id)
);

-- 9. Fee Structures
CREATE TABLE IF NOT EXISTS fee_structures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    department_id INTEGER NOT NULL REFERENCES departments(id) ON DELETE RESTRICT,
    semester INTEGER NOT NULL CHECK(semester BETWEEN 1 AND 8),
    fee_type TEXT NOT NULL,
    amount REAL NOT NULL CHECK(amount >= 0),
    academic_year TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(department_id, semester, fee_type, academic_year)
);

-- 10. Fee Invoices
CREATE TABLE IF NOT EXISTS fee_invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no TEXT NOT NULL UNIQUE,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    term_name TEXT NOT NULL,
    total_amount REAL NOT NULL CHECK(total_amount >= 0),
    paid_amount REAL NOT NULL DEFAULT 0.0 CHECK(paid_amount >= 0),
    balance_amount REAL NOT NULL CHECK(balance_amount >= 0),
    status TEXT NOT NULL DEFAULT 'UNPAID' CHECK(status IN ('PAID', 'PARTIAL', 'UNPAID', 'OVERDUE', 'CANCELLED')),
    due_date DATE NOT NULL,
    issued_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 11. Fee Payments
CREATE TABLE IF NOT EXISTS fee_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL REFERENCES fee_invoices(id) ON DELETE CASCADE,
    payment_no TEXT NOT NULL UNIQUE,
    amount REAL NOT NULL CHECK(amount > 0),
    payment_method TEXT NOT NULL CHECK(payment_method IN ('ONLINE', 'CASH', 'BANK_TRANSFER', 'CHEQUE', 'UPI')),
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    transaction_ref TEXT,
    notes TEXT,
    received_by TEXT DEFAULT 'Bursar Office'
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_faculty_dept ON faculty(department_id);
CREATE INDEX IF NOT EXISTS idx_courses_dept ON courses(department_id);
CREATE INDEX IF NOT EXISTS idx_students_dept ON students(department_id);
CREATE INDEX IF NOT EXISTS idx_students_status ON students(status);
CREATE INDEX IF NOT EXISTS idx_enrollment_student ON course_enrollments(student_id);
CREATE INDEX IF NOT EXISTS idx_enrollment_course ON course_enrollments(course_id);
CREATE INDEX IF NOT EXISTS idx_attendance_course_date ON attendance_records(course_id, attendance_date);
CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance_records(student_id);
CREATE INDEX IF NOT EXISTS idx_exam_course ON examinations(course_id);
CREATE INDEX IF NOT EXISTS idx_exam_results_exam ON exam_results(exam_id);
CREATE INDEX IF NOT EXISTS idx_invoices_student ON fee_invoices(student_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON fee_invoices(status);
CREATE INDEX IF NOT EXISTS idx_payments_invoice ON fee_payments(invoice_id);

-- 12. Campus Announcements Bulletin Board
CREATE TABLE IF NOT EXISTS announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN ('ACADEMIC', 'EXAM', 'FEES', 'EVENT', 'URGENT', 'GENERAL')),
    target_audience TEXT NOT NULL DEFAULT 'ALL' CHECK(target_audience IN ('ALL', 'STUDENTS', 'FACULTY')),
    priority TEXT NOT NULL DEFAULT 'NORMAL' CHECK(priority IN ('HIGH', 'NORMAL', 'LOW')),
    author_name TEXT NOT NULL DEFAULT 'Office of Academic Affairs',
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at DATE
);

CREATE INDEX IF NOT EXISTS idx_announcements_active ON announcements(is_active);
CREATE INDEX IF NOT EXISTS idx_announcements_category ON announcements(category);
CREATE INDEX IF NOT EXISTS idx_announcements_target ON announcements(target_audience);

-- 13. Institutional Leave & Absence Management
CREATE TABLE IF NOT EXISTS leave_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    applicant_type TEXT NOT NULL CHECK(applicant_type IN ('STUDENT', 'FACULTY')),
    applicant_id INTEGER NOT NULL,
    applicant_name TEXT NOT NULL,
    leave_type TEXT NOT NULL CHECK(leave_type IN ('SICK', 'CASUAL', 'ACADEMIC', 'EMERGENCY', 'MATERNITY', 'DUTY')),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'APPROVED', 'REJECTED')),
    review_remarks TEXT,
    reviewed_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_leaves_applicant ON leave_requests(applicant_type, applicant_id);
CREATE INDEX IF NOT EXISTS idx_leaves_status ON leave_requests(status);

-- 14. Academic Timetable & Lecture Scheduling
CREATE TABLE IF NOT EXISTS timetable_slots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    day_of_week TEXT NOT NULL CHECK(day_of_week IN ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday')),
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    room_number TEXT NOT NULL,
    building TEXT DEFAULT 'Main Academic Block',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(day_of_week, start_time, room_number)
);

CREATE INDEX IF NOT EXISTS idx_timetable_course ON timetable_slots(course_id);
CREATE INDEX IF NOT EXISTS idx_timetable_day ON timetable_slots(day_of_week);
CREATE INDEX IF NOT EXISTS idx_timetable_room ON timetable_slots(room_number);

-- 15. Campus Library & Resource Circulation
CREATE TABLE IF NOT EXISTS library_books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    isbn TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN ('COMPUTER_SCIENCE', 'ENGINEERING', 'MANAGEMENT', 'BIOTECH', 'MATHEMATICS', 'LITERATURE', 'GENERAL')),
    total_copies INTEGER NOT NULL DEFAULT 1 CHECK(total_copies >= 1),
    available_copies INTEGER NOT NULL DEFAULT 1 CHECK(available_copies >= 0),
    shelf_location TEXT NOT NULL DEFAULT 'Main Stack A-1',
    publisher TEXT,
    edition TEXT DEFAULT '1st Ed',
    publication_year INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_books_isbn ON library_books(isbn);
CREATE INDEX IF NOT EXISTS idx_books_category ON library_books(category);

CREATE TABLE IF NOT EXISTS book_loans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL REFERENCES library_books(id) ON DELETE RESTRICT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    return_date DATE,
    fine_amount REAL NOT NULL DEFAULT 0.0 CHECK(fine_amount >= 0),
    status TEXT NOT NULL DEFAULT 'ISSUED' CHECK(status IN ('ISSUED', 'RETURNED', 'OVERDUE')),
    remarks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_loans_book ON book_loans(book_id);
CREATE INDEX IF NOT EXISTS idx_loans_student ON book_loans(student_id);
CREATE INDEX IF NOT EXISTS idx_loans_status ON book_loans(status);
