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

-- 16. Hostel & Residential Hall Management
CREATE TABLE IF NOT EXISTS hostel_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    block_name TEXT NOT NULL UNIQUE,
    gender_type TEXT NOT NULL DEFAULT 'COED' CHECK(gender_type IN ('MALE', 'FEMALE', 'COED')),
    total_rooms INTEGER NOT NULL DEFAULT 10 CHECK(total_rooms >= 1),
    warden_name TEXT NOT NULL,
    warden_contact TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS hostel_rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    block_id INTEGER NOT NULL REFERENCES hostel_blocks(id) ON DELETE CASCADE,
    room_number TEXT NOT NULL,
    room_type TEXT NOT NULL DEFAULT 'DOUBLE' CHECK(room_type IN ('SINGLE', 'DOUBLE', 'TRIPLE', 'DORM')),
    capacity INTEGER NOT NULL DEFAULT 2 CHECK(capacity >= 1),
    current_occupancy INTEGER NOT NULL DEFAULT 0 CHECK(current_occupancy >= 0),
    floor INTEGER NOT NULL DEFAULT 1 CHECK(floor >= 0),
    fee_per_semester REAL NOT NULL DEFAULT 1200.0 CHECK(fee_per_semester >= 0),
    status TEXT NOT NULL DEFAULT 'AVAILABLE' CHECK(status IN ('AVAILABLE', 'FULL', 'MAINTENANCE')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(block_id, room_number)
);

CREATE INDEX IF NOT EXISTS idx_rooms_block ON hostel_rooms(block_id);
CREATE INDEX IF NOT EXISTS idx_rooms_status ON hostel_rooms(status);

CREATE TABLE IF NOT EXISTS room_allocations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL REFERENCES hostel_rooms(id) ON DELETE CASCADE,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    academic_year TEXT NOT NULL,
    check_in_date DATE NOT NULL,
    check_out_date DATE,
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'CHECKED_OUT', 'CANCELLED')),
    remarks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_allocations_room ON room_allocations(room_id);
CREATE INDEX IF NOT EXISTS idx_allocations_student ON room_allocations(student_id);
CREATE INDEX IF NOT EXISTS idx_allocations_status ON room_allocations(status);

-- 17. Campus Placements & Corporate Recruitment Cell
CREATE TABLE IF NOT EXISTS placement_drives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    industry TEXT NOT NULL DEFAULT 'Technology & Software',
    job_title TEXT NOT NULL,
    job_location TEXT NOT NULL DEFAULT 'Bengaluru / Hybrid',
    package_lpa REAL NOT NULL CHECK(package_lpa > 0),
    min_gpa_required REAL NOT NULL DEFAULT 6.5 CHECK(min_gpa_required >= 0.0 AND min_gpa_required <= 10.0),
    eligible_departments TEXT NOT NULL DEFAULT 'ALL',
    drive_date DATE NOT NULL,
    registration_deadline DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('UPCOMING', 'ACTIVE', 'CLOSED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_drives_status ON placement_drives(status);
CREATE INDEX IF NOT EXISTS idx_drives_company ON placement_drives(company_name);

CREATE TABLE IF NOT EXISTS placement_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    drive_id INTEGER NOT NULL REFERENCES placement_drives(id) ON DELETE CASCADE,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    current_gpa REAL NOT NULL CHECK(current_gpa >= 0.0 AND current_gpa <= 10.0),
    resume_link TEXT,
    status TEXT NOT NULL DEFAULT 'APPLIED' CHECK(status IN ('APPLIED', 'SHORTLISTED', 'TECHNICAL_ROUND', 'SELECTED', 'REJECTED')),
    interview_date DATE,
    offer_package_lpa REAL,
    remarks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(drive_id, student_id)
);

CREATE INDEX IF NOT EXISTS idx_placements_drive ON placement_applications(drive_id);
CREATE INDEX IF NOT EXISTS idx_placements_student ON placement_applications(student_id);
CREATE INDEX IF NOT EXISTS idx_placements_status ON placement_applications(status);

-- 18. Campus Transport Fleet & Transit Logistics
CREATE TABLE IF NOT EXISTS transport_routes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_name TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL,
    destination TEXT NOT NULL,
    total_stops INTEGER NOT NULL DEFAULT 5 CHECK(total_stops > 0),
    fare_per_semester REAL NOT NULL CHECK(fare_per_semester >= 0.0),
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'INACTIVE')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_transport_routes_status ON transport_routes(status);

CREATE TABLE IF NOT EXISTS transport_vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_id INTEGER REFERENCES transport_routes(id) ON DELETE SET NULL,
    vehicle_number TEXT NOT NULL UNIQUE,
    driver_name TEXT NOT NULL,
    driver_phone TEXT NOT NULL,
    capacity INTEGER NOT NULL CHECK(capacity > 0),
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'MAINTENANCE', 'RETIRED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_transport_vehicles_route ON transport_vehicles(route_id);
CREATE INDEX IF NOT EXISTS idx_transport_vehicles_status ON transport_vehicles(status);

CREATE TABLE IF NOT EXISTS transport_passes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    route_id INTEGER NOT NULL REFERENCES transport_routes(id) ON DELETE CASCADE,
    pass_number TEXT NOT NULL UNIQUE,
    pickup_stop TEXT NOT NULL,
    academic_year TEXT NOT NULL,
    valid_until DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'EXPIRED', 'CANCELLED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_transport_passes_student ON transport_passes(student_id);
CREATE INDEX IF NOT EXISTS idx_transport_passes_route ON transport_passes(route_id);
CREATE INDEX IF NOT EXISTS idx_transport_passes_status ON transport_passes(status);

-- 19. Scholarships, Grants & Financial Aid
CREATE TABLE IF NOT EXISTS scholarship_schemes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scheme_name TEXT NOT NULL UNIQUE,
    sponsor_type TEXT NOT NULL DEFAULT 'INSTITUTIONAL' CHECK(sponsor_type IN ('INSTITUTIONAL', 'GOVERNMENT', 'CORPORATE', 'ALUMNI_ENDOWMENT')),
    award_amount REAL NOT NULL CHECK(award_amount > 0.0),
    min_gpa_required REAL NOT NULL DEFAULT 7.5 CHECK(min_gpa_required >= 0.0 AND min_gpa_required <= 10.0),
    max_family_income REAL DEFAULT 800000.0 CHECK(max_family_income > 0.0),
    eligible_category TEXT NOT NULL DEFAULT 'ALL',
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'CLOSED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_scholarship_schemes_status ON scholarship_schemes(status);

CREATE TABLE IF NOT EXISTS scholarship_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scheme_id INTEGER NOT NULL REFERENCES scholarship_schemes(id) ON DELETE CASCADE,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    current_gpa REAL NOT NULL CHECK(current_gpa >= 0.0 AND current_gpa <= 10.0),
    annual_family_income REAL NOT NULL CHECK(annual_family_income >= 0.0),
    disbursed_amount REAL DEFAULT 0.0 CHECK(disbursed_amount >= 0.0),
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'APPROVED', 'DISBURSED', 'REJECTED')),
    review_remarks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(scheme_id, student_id)
);

CREATE INDEX IF NOT EXISTS idx_scholarship_apps_scheme ON scholarship_applications(scheme_id);
CREATE INDEX IF NOT EXISTS idx_scholarship_apps_student ON scholarship_applications(student_id);
CREATE INDEX IF NOT EXISTS idx_scholarship_apps_status ON scholarship_applications(status);

-- 20. Alumni Network & Career Mentorship Hub
CREATE TABLE IF NOT EXISTS alumni_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER REFERENCES students(id) ON DELETE SET NULL,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT,
    graduation_year INTEGER NOT NULL CHECK(graduation_year >= 1950),
    degree TEXT NOT NULL DEFAULT 'B.Tech',
    department_id INTEGER NOT NULL REFERENCES departments(id) ON DELETE RESTRICT,
    current_company TEXT NOT NULL DEFAULT 'Independent / Higher Studies',
    job_title TEXT NOT NULL DEFAULT 'Alumnus',
    city TEXT NOT NULL DEFAULT 'Bengaluru',
    linkedin_url TEXT,
    mentorship_status TEXT NOT NULL DEFAULT 'AVAILABLE' CHECK(mentorship_status IN ('AVAILABLE', 'BUSY', 'INACTIVE')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_alumni_dept ON alumni_members(department_id);
CREATE INDEX IF NOT EXISTS idx_alumni_grad_year ON alumni_members(graduation_year);
CREATE INDEX IF NOT EXISTS idx_alumni_mentorship ON alumni_members(mentorship_status);

CREATE TABLE IF NOT EXISTS alumni_mentorship_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alumni_id INTEGER NOT NULL REFERENCES alumni_members(id) ON DELETE CASCADE,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    mentorship_topic TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'REQUESTED' CHECK(status IN ('REQUESTED', 'ACCEPTED', 'COMPLETED', 'DECLINED')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mentorship_alumni ON alumni_mentorship_requests(alumni_id);
CREATE INDEX IF NOT EXISTS idx_mentorship_student ON alumni_mentorship_requests(student_id);
CREATE INDEX IF NOT EXISTS idx_mentorship_status ON alumni_mentorship_requests(status);

-- 21. Campus Events, Conferences & Symposium Hub
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN ('SEMINAR', 'WORKSHOP', 'SYMPOSIUM', 'HACKATHON', 'CULTURAL', 'SPORTS', 'CONFERENCE')),
    department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    organizer_faculty_id INTEGER REFERENCES faculty(id) ON DELETE SET NULL,
    venue TEXT NOT NULL,
    event_date DATE NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    max_capacity INTEGER NOT NULL DEFAULT 100 CHECK(max_capacity > 0),
    registration_fee REAL NOT NULL DEFAULT 0.0 CHECK(registration_fee >= 0.0),
    status TEXT NOT NULL DEFAULT 'UPCOMING' CHECK(status IN ('UPCOMING', 'ACTIVE', 'COMPLETED', 'CANCELLED')),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_events_code ON events(event_code);
CREATE INDEX IF NOT EXISTS idx_events_category ON events(category);
CREATE INDEX IF NOT EXISTS idx_events_status ON events(status);
CREATE INDEX IF NOT EXISTS idx_events_date ON events(event_date);
CREATE INDEX IF NOT EXISTS idx_events_dept ON events(department_id);

CREATE TABLE IF NOT EXISTS event_registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    registration_number TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'REGISTERED' CHECK(status IN ('REGISTERED', 'ATTENDED', 'CANCELLED')),
    certificate_issued INTEGER NOT NULL DEFAULT 0 CHECK(certificate_issued IN (0, 1)),
    attendance_marked_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(event_id, student_id)
);

CREATE INDEX IF NOT EXISTS idx_event_reg_event ON event_registrations(event_id);
CREATE INDEX IF NOT EXISTS idx_event_reg_student ON event_registrations(student_id);
CREATE INDEX IF NOT EXISTS idx_event_reg_status ON event_registrations(status);
CREATE INDEX IF NOT EXISTS idx_event_reg_num ON event_registrations(registration_number);

-- 22. Campus Assets, Laboratory Equipment & Inventory Circulation Hub
CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_tag TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN ('LAB_EQUIPMENT', 'COMPUTING', 'AV_MULTIMEDIA', 'RESEARCH_INSTRUMENT', 'FURNITURE', 'OTHER')),
    department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    lab_room TEXT NOT NULL,
    serial_number TEXT UNIQUE,
    model_number TEXT,
    manufacturer TEXT,
    purchase_date DATE NOT NULL,
    purchase_cost REAL NOT NULL CHECK(purchase_cost >= 0.0),
    warranty_expiry DATE,
    status TEXT NOT NULL DEFAULT 'AVAILABLE' CHECK(status IN ('AVAILABLE', 'CHECKED_OUT', 'MAINTENANCE', 'DECOMMISSIONED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_assets_tag ON assets(asset_tag);
CREATE INDEX IF NOT EXISTS idx_assets_dept ON assets(department_id);
CREATE INDEX IF NOT EXISTS idx_assets_category ON assets(category);
CREATE INDEX IF NOT EXISTS idx_assets_status ON assets(status);
CREATE INDEX IF NOT EXISTS idx_assets_room ON assets(lab_room);

CREATE TABLE IF NOT EXISTS asset_checkouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    checkout_code TEXT NOT NULL UNIQUE,
    asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE RESTRICT,
    borrower_type TEXT NOT NULL CHECK(borrower_type IN ('STUDENT', 'FACULTY')),
    student_id INTEGER REFERENCES students(id) ON DELETE SET NULL,
    faculty_id INTEGER REFERENCES faculty(id) ON DELETE SET NULL,
    checkout_date DATE NOT NULL,
    due_date DATE NOT NULL,
    returned_date DATE,
    condition_out TEXT NOT NULL DEFAULT 'GOOD' CHECK(condition_out IN ('NEW', 'EXCELLENT', 'GOOD', 'FAIR')),
    condition_in TEXT CHECK(condition_in IN ('EXCELLENT', 'GOOD', 'FAIR', 'DAMAGED')),
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'RETURNED', 'OVERDUE')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_asset_checkouts_code ON asset_checkouts(checkout_code);
CREATE INDEX IF NOT EXISTS idx_asset_checkouts_asset ON asset_checkouts(asset_id);
CREATE INDEX IF NOT EXISTS idx_asset_checkouts_student ON asset_checkouts(student_id);
CREATE INDEX IF NOT EXISTS idx_asset_checkouts_faculty ON asset_checkouts(faculty_id);
CREATE INDEX IF NOT EXISTS idx_asset_checkouts_status ON asset_checkouts(status);

CREATE TABLE IF NOT EXISTS asset_maintenance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    maintenance_code TEXT NOT NULL UNIQUE,
    asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    maintenance_type TEXT NOT NULL CHECK(maintenance_type IN ('CALIBRATION', 'PREVENTATIVE', 'REPAIR', 'FIRMWARE_UPGRADE', 'INSPECTION')),
    scheduled_date DATE NOT NULL,
    completed_date DATE,
    technician_name TEXT NOT NULL,
    cost REAL NOT NULL DEFAULT 0.0 CHECK(cost >= 0.0),
    status TEXT NOT NULL DEFAULT 'SCHEDULED' CHECK(status IN ('SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')),
    resolution_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_asset_maint_code ON asset_maintenance(maintenance_code);
CREATE INDEX IF NOT EXISTS idx_asset_maint_asset ON asset_maintenance(asset_id);
CREATE INDEX IF NOT EXISTS idx_asset_maint_status ON asset_maintenance(status);

-- 23. Campus Health, Student Clinic & Infirmary Hub
CREATE TABLE IF NOT EXISTS health_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_type TEXT NOT NULL CHECK(person_type IN ('STUDENT', 'FACULTY')),
    student_id INTEGER REFERENCES students(id) ON DELETE CASCADE,
    faculty_id INTEGER REFERENCES faculty(id) ON DELETE CASCADE,
    blood_group TEXT NOT NULL CHECK(blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')),
    allergies TEXT NOT NULL DEFAULT 'None',
    chronic_conditions TEXT NOT NULL DEFAULT 'None',
    emergency_contact_name TEXT NOT NULL,
    emergency_contact_phone TEXT NOT NULL,
    emergency_contact_relation TEXT NOT NULL DEFAULT 'Parent',
    insurance_provider TEXT,
    insurance_policy_number TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        (person_type = 'STUDENT' AND student_id IS NOT NULL AND faculty_id IS NULL) OR
        (person_type = 'FACULTY' AND faculty_id IS NOT NULL AND student_id IS NULL)
    ),
    UNIQUE(student_id),
    UNIQUE(faculty_id)
);

CREATE INDEX IF NOT EXISTS idx_health_profiles_student ON health_profiles(student_id);
CREATE INDEX IF NOT EXISTS idx_health_profiles_faculty ON health_profiles(faculty_id);
CREATE INDEX IF NOT EXISTS idx_health_profiles_blood ON health_profiles(blood_group);
CREATE INDEX IF NOT EXISTS idx_health_profiles_type ON health_profiles(person_type);

CREATE TABLE IF NOT EXISTS dispensary_medicines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN ('ANALGESIC', 'ANTIBIOTIC', 'ANTIHISTAMINE', 'ANTISEPTIC', 'ANTACID', 'FIRST_AID', 'SUPPLEMENT', 'OTHER')),
    form TEXT NOT NULL DEFAULT 'TABLET' CHECK(form IN ('TABLET', 'CAPSULE', 'SYRUP', 'OINTMENT', 'INJECTION', 'BANDAGE', 'DROPS', 'SACHET', 'OTHER')),
    stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK(stock_quantity >= 0),
    unit TEXT NOT NULL DEFAULT 'Units',
    reorder_level INTEGER NOT NULL DEFAULT 10 CHECK(reorder_level >= 0),
    expiry_date DATE NOT NULL,
    batch_number TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dispensary_code ON dispensary_medicines(item_code);
CREATE INDEX IF NOT EXISTS idx_dispensary_category ON dispensary_medicines(category);
CREATE INDEX IF NOT EXISTS idx_dispensary_stock ON dispensary_medicines(stock_quantity);

CREATE TABLE IF NOT EXISTS medical_encounters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    encounter_code TEXT NOT NULL UNIQUE,
    patient_type TEXT NOT NULL CHECK(patient_type IN ('STUDENT', 'FACULTY')),
    student_id INTEGER REFERENCES students(id) ON DELETE SET NULL,
    faculty_id INTEGER REFERENCES faculty(id) ON DELETE SET NULL,
    visit_date DATE NOT NULL,
    doctor_name TEXT NOT NULL,
    chief_complaint TEXT NOT NULL,
    symptoms TEXT,
    diagnosis TEXT NOT NULL,
    blood_pressure TEXT,
    pulse_bpm INTEGER CHECK(pulse_bpm IS NULL OR (pulse_bpm > 0 AND pulse_bpm < 300)),
    temperature_f REAL CHECK(temperature_f IS NULL OR (temperature_f > 80.0 AND temperature_f < 115.0)),
    triage_severity TEXT NOT NULL DEFAULT 'NORMAL' CHECK(triage_severity IN ('NORMAL', 'URGENT', 'EMERGENCY')),
    treatment_given TEXT,
    follow_up_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        (patient_type = 'STUDENT' AND student_id IS NOT NULL AND faculty_id IS NULL) OR
        (patient_type = 'FACULTY' AND faculty_id IS NOT NULL AND student_id IS NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_encounters_code ON medical_encounters(encounter_code);
CREATE INDEX IF NOT EXISTS idx_encounters_student ON medical_encounters(student_id);
CREATE INDEX IF NOT EXISTS idx_encounters_faculty ON medical_encounters(faculty_id);
CREATE INDEX IF NOT EXISTS idx_encounters_date ON medical_encounters(visit_date);
CREATE INDEX IF NOT EXISTS idx_encounters_triage ON medical_encounters(triage_severity);
CREATE INDEX IF NOT EXISTS idx_encounters_type ON medical_encounters(patient_type);

CREATE TABLE IF NOT EXISTS encounter_prescriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    encounter_id INTEGER NOT NULL REFERENCES medical_encounters(id) ON DELETE CASCADE,
    medicine_id INTEGER REFERENCES dispensary_medicines(id) ON DELETE SET NULL,
    medicine_name TEXT NOT NULL,
    dosage TEXT NOT NULL,
    frequency TEXT NOT NULL,
    duration_days INTEGER NOT NULL DEFAULT 3 CHECK(duration_days > 0),
    quantity_dispensed INTEGER NOT NULL DEFAULT 1 CHECK(quantity_dispensed >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_prescriptions_encounter ON encounter_prescriptions(encounter_id);
CREATE INDEX IF NOT EXISTS idx_prescriptions_med ON encounter_prescriptions(medicine_id);

CREATE TABLE IF NOT EXISTS medical_certificates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    certificate_number TEXT NOT NULL UNIQUE,
    encounter_id INTEGER NOT NULL REFERENCES medical_encounters(id) ON DELETE RESTRICT,
    patient_type TEXT NOT NULL CHECK(patient_type IN ('STUDENT', 'FACULTY')),
    student_id INTEGER REFERENCES students(id) ON DELETE SET NULL,
    faculty_id INTEGER REFERENCES faculty(id) ON DELETE SET NULL,
    rest_from_date DATE NOT NULL,
    rest_to_date DATE NOT NULL,
    fit_to_resume_date DATE NOT NULL,
    diagnosis_summary TEXT NOT NULL,
    doctor_remarks TEXT,
    status TEXT NOT NULL DEFAULT 'ISSUED' CHECK(status IN ('ISSUED', 'REVOKED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        (patient_type = 'STUDENT' AND student_id IS NOT NULL AND faculty_id IS NULL) OR
        (patient_type = 'FACULTY' AND faculty_id IS NOT NULL AND student_id IS NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_med_cert_num ON medical_certificates(certificate_number);
CREATE INDEX IF NOT EXISTS idx_med_cert_encounter ON medical_certificates(encounter_id);
CREATE INDEX IF NOT EXISTS idx_med_cert_student ON medical_certificates(student_id);
CREATE INDEX IF NOT EXISTS idx_med_cert_faculty ON medical_certificates(faculty_id);
CREATE INDEX IF NOT EXISTS idx_med_cert_status ON medical_certificates(status);



