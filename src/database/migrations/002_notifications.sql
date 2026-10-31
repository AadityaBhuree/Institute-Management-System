-- Migration 002: Institutional Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipient_role TEXT NOT NULL CHECK(recipient_role IN ('ALL', 'ADMIN', 'FACULTY', 'STUDENT')),
    recipient_id INTEGER,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN ('ACADEMIC', 'FINANCE', 'HEALTH', 'PLACEMENT', 'SYSTEM', 'GENERAL')),
    priority TEXT NOT NULL DEFAULT 'NORMAL' CHECK(priority IN ('LOW', 'NORMAL', 'HIGH', 'URGENT')),
    is_read BOOLEAN NOT NULL DEFAULT 0 CHECK(is_read IN (0, 1)),
    action_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_notifications_recipient ON notifications(recipient_role, recipient_id, is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications(created_at DESC);
