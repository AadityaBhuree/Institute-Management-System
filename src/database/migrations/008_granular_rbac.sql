-- Migration 008: Granular Dynamic Institutional RBAC & Functional Permission Matrix
-- Extends users table with custom_permissions, creates permission catalog & role mappings, and provisions default staff accounts.

PRAGMA foreign_keys = OFF;

CREATE TABLE IF NOT EXISTS users_rbac_temp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'student' CHECK(role IN ('admin', 'registrar', 'bursar', 'librarian', 'health_officer', 'placement_officer', 'faculty', 'student')),
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'inactive', 'suspended')),
    faculty_id INTEGER REFERENCES faculty(id) ON DELETE SET NULL,
    student_id INTEGER REFERENCES students(id) ON DELETE SET NULL,
    custom_permissions TEXT,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO users_rbac_temp (id, username, email, password_hash, role, status, faculty_id, student_id, last_login, created_at, updated_at)
SELECT id, username, email, password_hash, role, status, faculty_id, student_id, last_login, created_at, updated_at FROM users;

DROP TABLE users;

ALTER TABLE users_rbac_temp RENAME TO users;

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

PRAGMA foreign_keys = ON;

-- 2. System Permission Catalog Table
CREATE TABLE IF NOT EXISTS system_permissions (
    code TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_permissions_cat ON system_permissions(category);

-- 3. Role-Permission Mapping Table
CREATE TABLE IF NOT EXISTS role_default_permissions (
    role TEXT NOT NULL,
    permission_code TEXT NOT NULL REFERENCES system_permissions(code) ON DELETE CASCADE,
    PRIMARY KEY (role, permission_code)
);

CREATE INDEX IF NOT EXISTS idx_role_perms_role ON role_default_permissions(role);

-- 4. Seed Standard Permissions Catalog
INSERT OR IGNORE INTO system_permissions (code, category, name, description) VALUES
('students:read', 'STUDENTS', 'View Scholar Profiles', 'Read scholar records, profiles, and academic status.'),
('students:write', 'STUDENTS', 'Manage Scholars', 'Register, update, and enroll scholars into institutional batches.'),
('students:delete', 'STUDENTS', 'Archive / Delete Scholars', 'Soft-delete or purge scholar enrollment files.'),
('academics:read', 'ACADEMICS', 'View Academic Curricula', 'Inspect departments, courses, curricula, and timetables.'),
('academics:write', 'ACADEMICS', 'Manage Courses & Timetables', 'Create departments, courses, and schedule lecture slots.'),
('grades:read', 'EXAMINATIONS', 'View Marks & Transcripts', 'Inspect semester exam results, grade cards, and transcripts.'),
('grades:write', 'EXAMINATIONS', 'Record Grades & Transcripts', 'Submit exam marks, finalize grades, and publish transcripts.'),
('attendance:read', 'ATTENDANCE', 'View Attendance Logs', 'Inspect student attendance rosters and absence metrics.'),
('attendance:write', 'ATTENDANCE', 'Record Attendance', 'Take roll call and log daily class attendance sessions.'),
('finance:read', 'FINANCE', 'View Bursar Financials', 'Inspect tuition fee structures, invoices, and payments.'),
('finance:write', 'FINANCE', 'Manage Bursar Operations', 'Create invoices, record payments, and audit fee ledgers.'),
('library:read', 'LIBRARY', 'Search Library Catalog', 'Search monographs, textbooks, and inspect loan status.'),
('library:write', 'LIBRARY', 'Manage Library Circulation', 'Catalog monographs, checkout/return books, and assess fines.'),
('health:read', 'HEALTH', 'View Infirmary Logs', 'Inspect campus health center visits and patient records.'),
('health:write', 'HEALTH', 'Manage Clinical Care', 'Record medical encounters, dispense medication, and sign certificates.'),
('placements:read', 'PLACEMENTS', 'Browse Corporate Drives', 'View placement drives, recruitment schedules, and job openings.'),
('placements:write', 'PLACEMENTS', 'Manage Career Services', 'Post corporate drives, shortlist scholars, and log salary packages.'),
('hostel:manage', 'CAMPUS_SERVICES', 'Manage Student Housing', 'Allocate rooms, inspect occupancy, and manage hostel blocks.'),
('transport:manage', 'CAMPUS_SERVICES', 'Manage Transit Fleet', 'Configure bus routes, fleet vehicles, and transit passes.'),
('scholarships:manage', 'CAMPUS_SERVICES', 'Manage Financial Aid', 'Configure scholarship schemes, review applications, and disburse aid.'),
('events:manage', 'CAMPUS_SERVICES', 'Manage Campus Events', 'Schedule symposiums, hackathons, and handle registrations.'),
('inventory:manage', 'CAMPUS_SERVICES', 'Manage Physical Assets', 'Track laboratory equipment, campus assets, and maintenance.'),
('reports:read', 'REPORTS', 'Export Analytics & Workbooks', 'Download Excel audit workbooks and vector PDF summaries.'),
('reports:archive', 'REPORTS', 'Execute Cohort Archival', 'Perform cold storage archival on graduated scholar cohorts.'),
('id_cards:manage', 'CREDENTIALS', 'Manage Digital ID Cards', 'Compile, preview, and batch-print official institutional ID cards.'),
('system:admin', 'SYSTEM', 'System Diagnostics & Backups', 'Execute database backups, WAL optimize, and inspect telemetry.'),
('rbac:manage', 'SYSTEM', 'Manage Roles & Permissions', 'Reassign institutional staff roles and customize granular permissions.');

-- 5. Seed Default Role-Permission Mappings
-- Registrar
INSERT OR IGNORE INTO role_default_permissions (role, permission_code) VALUES
('registrar', 'students:read'),
('registrar', 'students:write'),
('registrar', 'students:delete'),
('registrar', 'academics:read'),
('registrar', 'academics:write'),
('registrar', 'grades:read'),
('registrar', 'attendance:read'),
('registrar', 'reports:read'),
('registrar', 'reports:archive'),
('registrar', 'id_cards:manage');

-- Bursar
INSERT OR IGNORE INTO role_default_permissions (role, permission_code) VALUES
('bursar', 'finance:read'),
('bursar', 'finance:write'),
('bursar', 'students:read'),
('bursar', 'scholarships:manage'),
('bursar', 'reports:read');

-- Librarian
INSERT OR IGNORE INTO role_default_permissions (role, permission_code) VALUES
('librarian', 'library:read'),
('librarian', 'library:write'),
('librarian', 'students:read');

-- Health Officer
INSERT OR IGNORE INTO role_default_permissions (role, permission_code) VALUES
('health_officer', 'health:read'),
('health_officer', 'health:write'),
('health_officer', 'students:read'),
('health_officer', 'reports:read');

-- Placement Officer
INSERT OR IGNORE INTO role_default_permissions (role, permission_code) VALUES
('placement_officer', 'placements:read'),
('placement_officer', 'placements:write'),
('placement_officer', 'students:read'),
('placement_officer', 'reports:read');

-- Faculty
INSERT OR IGNORE INTO role_default_permissions (role, permission_code) VALUES
('faculty', 'students:read'),
('faculty', 'academics:read'),
('faculty', 'grades:read'),
('faculty', 'grades:write'),
('faculty', 'attendance:read'),
('faculty', 'attendance:write');
