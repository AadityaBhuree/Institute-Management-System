-- Migration 003: Secure Document & Media Storage
CREATE TABLE IF NOT EXISTS uploaded_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id TEXT UNIQUE NOT NULL,
    original_name TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    category TEXT NOT NULL DEFAULT 'GENERAL' CHECK(category IN ('AVATAR', 'RESUME', 'MEDICAL', 'PROOF', 'GENERAL')),
    file_path TEXT NOT NULL,
    uploaded_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_uploaded_docs_file_id ON uploaded_documents(file_id);
CREATE INDEX IF NOT EXISTS idx_uploaded_docs_category ON uploaded_documents(category);
CREATE INDEX IF NOT EXISTS idx_uploaded_docs_created ON uploaded_documents(created_at DESC);

