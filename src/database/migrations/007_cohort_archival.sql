-- Migration 007: Scholar Cohort Archival & Cold Storage
-- Policy-driven archival workflow moving graduated/alumni scholar records to cold storage tables with cryptographic integrity hashes.

CREATE TABLE IF NOT EXISTS archived_students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_student_id INTEGER NOT NULL,
    enrollment_no TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    email TEXT,
    department_code TEXT NOT NULL,
    graduation_year INTEGER NOT NULL,
    final_cgpa REAL DEFAULT 0.0,
    total_credits INTEGER DEFAULT 0,
    archive_payload_json TEXT NOT NULL,
    integrity_hash TEXT NOT NULL,
    archived_by TEXT NOT NULL,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_archived_students_year ON archived_students(graduation_year);
CREATE INDEX IF NOT EXISTS idx_archived_students_dept ON archived_students(department_code);
CREATE INDEX IF NOT EXISTS idx_archived_students_hash ON archived_students(integrity_hash);
