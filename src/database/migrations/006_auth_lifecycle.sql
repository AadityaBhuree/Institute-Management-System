-- Migration 006: Identity Lifecycle, Password Reset Tokens & Two-Factor Authentication
-- Tables for cryptographic password reset tokens, RFC 6238 TOTP secrets, and active sessions.

CREATE TABLE IF NOT EXISTS password_resets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN NOT NULL DEFAULT 0 CHECK(used IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pwd_resets_hash ON password_resets(token_hash);
CREATE INDEX IF NOT EXISTS idx_pwd_resets_user ON password_resets(user_id);
CREATE INDEX IF NOT EXISTS idx_pwd_resets_expires ON password_resets(expires_at);

CREATE TABLE IF NOT EXISTS user_totp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    totp_secret TEXT NOT NULL,
    is_enabled BOOLEAN NOT NULL DEFAULT 0 CHECK(is_enabled IN (0, 1)),
    backup_codes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_totp_user ON user_totp(user_id);

CREATE TABLE IF NOT EXISTS user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL UNIQUE,
    ip_address TEXT,
    user_agent TEXT,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_revoked BOOLEAN NOT NULL DEFAULT 0 CHECK(is_revoked IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_sessions_id ON user_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id);
