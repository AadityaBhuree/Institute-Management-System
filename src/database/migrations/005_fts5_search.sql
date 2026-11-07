-- Migration 005: SQLite FTS5 Full-Text Omnisearch Virtual Tables & Triggers
-- Establishes sub-millisecond search across students, faculty, courses, library books, and announcements.

-- 1. Virtual Tables with Porter Stemmer Tokenizer
CREATE VIRTUAL TABLE IF NOT EXISTS fts_students USING fts5(
    student_id UNINDEXED,
    enrollment_no,
    name,
    email,
    status,
    tokenize='porter unicode61'
);

CREATE VIRTUAL TABLE IF NOT EXISTS fts_faculty USING fts5(
    faculty_id_col UNINDEXED,
    faculty_code,
    name,
    email,
    designation,
    tokenize='porter unicode61'
);

CREATE VIRTUAL TABLE IF NOT EXISTS fts_courses USING fts5(
    course_id UNINDEXED,
    code,
    title,
    syllabus_summary,
    tokenize='porter unicode61'
);

CREATE VIRTUAL TABLE IF NOT EXISTS fts_library_books USING fts5(
    book_id UNINDEXED,
    isbn,
    title,
    author,
    category,
    publisher,
    tokenize='porter unicode61'
);

CREATE VIRTUAL TABLE IF NOT EXISTS fts_announcements USING fts5(
    announcement_id UNINDEXED,
    title,
    content,
    category,
    target_audience,
    tokenize='porter unicode61'
);

-- 2. Populate Existing Records into FTS5 Indices
INSERT INTO fts_students (student_id, enrollment_no, name, email, status)
SELECT id, enrollment_no, first_name || ' ' || last_name, email, status
FROM students
WHERE is_deleted = 0;

INSERT INTO fts_faculty (faculty_id_col, faculty_code, name, email, designation)
SELECT id, faculty_id, first_name || ' ' || last_name, email, designation
FROM faculty;

INSERT INTO fts_courses (course_id, code, title, syllabus_summary)
SELECT id, code, title, COALESCE(syllabus_summary, '')
FROM courses;

INSERT INTO fts_library_books (book_id, isbn, title, author, category, publisher)
SELECT id, isbn, title, author, category, COALESCE(publisher, '')
FROM library_books;

INSERT INTO fts_announcements (announcement_id, title, content, category, target_audience)
SELECT id, title, content, category, target_audience
FROM announcements
WHERE is_active = 1;

-- 3. Automatic Synchronization Triggers: Students
CREATE TRIGGER IF NOT EXISTS trg_students_fts_ai AFTER INSERT ON students BEGIN
    INSERT INTO fts_students (student_id, enrollment_no, name, email, status)
    VALUES (new.id, new.enrollment_no, new.first_name || ' ' || new.last_name, new.email, new.status);
END;

CREATE TRIGGER IF NOT EXISTS trg_students_fts_ad AFTER DELETE ON students BEGIN
    DELETE FROM fts_students WHERE student_id = old.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_students_fts_au AFTER UPDATE ON students BEGIN
    DELETE FROM fts_students WHERE student_id = old.id;
    INSERT INTO fts_students (student_id, enrollment_no, name, email, status)
    VALUES (new.id, new.enrollment_no, new.first_name || ' ' || new.last_name, new.email, new.status);
END;

-- 4. Automatic Synchronization Triggers: Faculty
CREATE TRIGGER IF NOT EXISTS trg_faculty_fts_ai AFTER INSERT ON faculty BEGIN
    INSERT INTO fts_faculty (faculty_id_col, faculty_code, name, email, designation)
    VALUES (new.id, new.faculty_id, new.first_name || ' ' || new.last_name, new.email, new.designation);
END;

CREATE TRIGGER IF NOT EXISTS trg_faculty_fts_ad AFTER DELETE ON faculty BEGIN
    DELETE FROM fts_faculty WHERE faculty_id_col = old.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_faculty_fts_au AFTER UPDATE ON faculty BEGIN
    DELETE FROM fts_faculty WHERE faculty_id_col = old.id;
    INSERT INTO fts_faculty (faculty_id_col, faculty_code, name, email, designation)
    VALUES (new.id, new.faculty_id, new.first_name || ' ' || new.last_name, new.email, new.designation);
END;

-- 5. Automatic Synchronization Triggers: Courses
CREATE TRIGGER IF NOT EXISTS trg_courses_fts_ai AFTER INSERT ON courses BEGIN
    INSERT INTO fts_courses (course_id, code, title, syllabus_summary)
    VALUES (new.id, new.code, new.title, COALESCE(new.syllabus_summary, ''));
END;

CREATE TRIGGER IF NOT EXISTS trg_courses_fts_ad AFTER DELETE ON courses BEGIN
    DELETE FROM fts_courses WHERE course_id = old.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_courses_fts_au AFTER UPDATE ON courses BEGIN
    DELETE FROM fts_courses WHERE course_id = old.id;
    INSERT INTO fts_courses (course_id, code, title, syllabus_summary)
    VALUES (new.id, new.code, new.title, COALESCE(new.syllabus_summary, ''));
END;

-- 6. Automatic Synchronization Triggers: Library Books
CREATE TRIGGER IF NOT EXISTS trg_books_fts_ai AFTER INSERT ON library_books BEGIN
    INSERT INTO fts_library_books (book_id, isbn, title, author, category, publisher)
    VALUES (new.id, new.isbn, new.title, new.author, new.category, COALESCE(new.publisher, ''));
END;

CREATE TRIGGER IF NOT EXISTS trg_books_fts_ad AFTER DELETE ON library_books BEGIN
    DELETE FROM fts_library_books WHERE book_id = old.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_books_fts_au AFTER UPDATE ON library_books BEGIN
    DELETE FROM fts_library_books WHERE book_id = old.id;
    INSERT INTO fts_library_books (book_id, isbn, title, author, category, publisher)
    VALUES (new.id, new.isbn, new.title, new.author, new.category, COALESCE(new.publisher, ''));
END;

-- 7. Automatic Synchronization Triggers: Announcements
CREATE TRIGGER IF NOT EXISTS trg_announcements_fts_ai AFTER INSERT ON announcements BEGIN
    INSERT INTO fts_announcements (announcement_id, title, content, category, target_audience)
    VALUES (new.id, new.title, new.content, new.category, new.target_audience);
END;

CREATE TRIGGER IF NOT EXISTS trg_announcements_fts_ad AFTER DELETE ON announcements BEGIN
    DELETE FROM fts_announcements WHERE announcement_id = old.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_announcements_fts_au AFTER UPDATE ON announcements BEGIN
    DELETE FROM fts_announcements WHERE announcement_id = old.id;
    INSERT INTO fts_announcements (announcement_id, title, content, category, target_audience)
    VALUES (new.id, new.title, new.content, new.category, new.target_audience);
END;
