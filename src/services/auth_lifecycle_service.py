"""Identity Lifecycle, Password Self-Service, and Two-Factor Authentication Service."""

import datetime
import hashlib
import json
import logging
import secrets
import sqlite3
from typing import Any, Dict, List, Optional

from src.core.security import hash_password
from src.core.totp import TOTPManager
from src.database.connection import transaction
from src.services.auth_service import AuthService
from src.services.email_service import EmailService

logger = logging.getLogger("ims")


class AuthLifecycleService:
    """Manages password recovery tokens, RFC 6238 TOTP enrollment, and session management."""

    # ---------------------------------------------------------
    # 1. Password Reset Token Subsystem
    # ---------------------------------------------------------

    @staticmethod
    def request_password_reset(
        conn: sqlite3.Connection,
        email: str,
    ) -> Optional[str]:
        """Generate a single-use 30-minute password reset token and queue email notice."""
        cur = conn.cursor()
        cur.execute(
            "SELECT id, username, email FROM users WHERE email = ? AND status = 'active';",
            (email.strip(),),
        )
        user = cur.fetchone()
        cur.close()

        if not user:
            # Silent return to prevent user enumeration attacks
            return None

        user_id = user["id"]
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        expires_at = (datetime.datetime.now() + datetime.timedelta(minutes=30)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        with transaction(conn) as cursor:
            cursor.execute(
                """
                INSERT INTO password_resets (user_id, token_hash, expires_at, used)
                VALUES (?, ?, ?, 0);
                """,
                (user_id, token_hash, expires_at),
            )

        # Trigger notification email
        reset_link = f"/reset-password?token={raw_token}"
        EmailService.send_email_async(
            recipient=user["email"],
            subject="IMS Account Security: Password Recovery Request",
            body_text=(
                f"Hello {user['username']},\n\n"
                f"A password reset request was submitted for your IMS account.\n"
                f"Use the following link within 30 minutes to reset your credentials:\n{reset_link}\n\n"
                f"If you did not make this request, please disregard this email."
            ),
            template_name="password_reset",
        )

        AuthService.log_audit(
            conn,
            action="PASSWORD_RESET_REQUESTED",
            resource="user",
            resource_id=str(user_id),
            details=f"Reset token issued for user {user['username']}",
        )

        return raw_token

    @staticmethod
    def reset_password(
        conn: sqlite3.Connection,
        raw_token: str,
        new_password: str,
    ) -> bool:
        """Validate token and update password hash with PBKDF2."""
        token_hash = hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, user_id, expires_at, used
            FROM password_resets
            WHERE token_hash = ?;
            """,
            (token_hash,),
        )
        row = cur.fetchone()
        cur.close()

        if not row:
            raise ValueError("Invalid password reset token.")
        if row["used"]:
            raise ValueError("Password reset token has already been consumed.")

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if row["expires_at"] < now_str:
            raise ValueError("Password reset token has expired.")

        user_id = row["user_id"]
        new_hashed = hash_password(new_password)

        with transaction(conn) as cursor:
            # 1. Update user password
            cursor.execute(
                """
                UPDATE users
                SET password_hash = ?
                WHERE id = ?;
                """,
                (new_hashed, user_id),
            )
            # 2. Mark token consumed
            cursor.execute(
                """
                UPDATE password_resets
                SET used = 1
                WHERE id = ?;
                """,
                (row["id"],),
            )
            # 3. Terminate active sessions for security
            cursor.execute(
                """
                UPDATE user_sessions
                SET is_revoked = 1
                WHERE user_id = ?;
                """,
                (user_id,),
            )

        AuthService.log_audit(
            conn,
            action="PASSWORD_RESET_COMPLETED",
            resource="user",
            resource_id=str(user_id),
            details="Password successfully updated via recovery token",
        )
        return True

    # ---------------------------------------------------------
    # 2. Two-Factor Authentication (RFC 6238 TOTP)
    # ---------------------------------------------------------

    @staticmethod
    def setup_totp(
        conn: sqlite3.Connection,
        user_id: int,
        username: str,
    ) -> Dict[str, Any]:
        """Generate new TOTP secret and backup recovery codes."""
        secret = TOTPManager.generate_secret()
        backup_codes = TOTPManager.generate_backup_codes(8)
        hashed_codes = [
            hashlib.sha256(c.replace("-", "").upper().encode("utf-8")).hexdigest()
            for c in backup_codes
        ]
        codes_json = json.dumps(hashed_codes)

        with transaction(conn) as cursor:
            cursor.execute(
                """
                INSERT INTO user_totp (user_id, totp_secret, is_enabled, backup_codes)
                VALUES (?, ?, 0, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    totp_secret = excluded.totp_secret,
                    is_enabled = 0,
                    backup_codes = excluded.backup_codes;
                """,
                (user_id, secret, codes_json),
            )

        uri = TOTPManager.get_provisioning_uri(secret, account_name=username)
        return {
            "secret": secret,
            "provisioning_uri": uri,
            "backup_codes": backup_codes,
        }

    @staticmethod
    def verify_and_enable_totp(
        conn: sqlite3.Connection,
        user_id: int,
        code: str,
    ) -> bool:
        """Verify initial TOTP token to activate 2FA protection."""
        cur = conn.cursor()
        cur.execute("SELECT totp_secret, is_enabled FROM user_totp WHERE user_id = ?;", (user_id,))
        row = cur.fetchone()
        cur.close()

        if not row:
            raise ValueError("No TOTP setup found. Please initiate 2FA setup first.")

        if not TOTPManager.verify_totp(row["totp_secret"], code):
            return False

        with transaction(conn) as cursor:
            cursor.execute(
                """
                UPDATE user_totp
                SET is_enabled = 1
                WHERE user_id = ?;
                """,
                (user_id,),
            )

        AuthService.log_audit(
            conn,
            action="TOTP_ENABLED",
            resource="user",
            resource_id=str(user_id),
            details="Two-factor authentication successfully verified and enabled",
        )
        return True

    @staticmethod
    def verify_totp_or_backup(
        conn: sqlite3.Connection,
        user_id: int,
        code: str,
    ) -> bool:
        """Verify 6-digit TOTP code or consume an emergency backup code."""
        cur = conn.cursor()
        cur.execute(
            """
            SELECT totp_secret, is_enabled, backup_codes
            FROM user_totp
            WHERE user_id = ?;
            """,
            (user_id,),
        )
        row = cur.fetchone()
        cur.close()

        if not row or not row["is_enabled"]:
            return True  # 2FA not enabled for this user

        # 1. Check TOTP 6-digit code
        clean_code = code.strip()
        if len(clean_code) == 6 and clean_code.isdigit():
            if TOTPManager.verify_totp(row["totp_secret"], clean_code):
                return True

        # 2. Check emergency recovery backup code
        normalized_code = clean_code.replace("-", "").upper()
        code_hash = hashlib.sha256(normalized_code.encode("utf-8")).hexdigest()
        stored_codes: List[str] = json.loads(row["backup_codes"] or "[]")

        if code_hash in stored_codes:
            stored_codes.remove(code_hash)
            with transaction(conn) as cursor:
                cursor.execute(
                    """
                    UPDATE user_totp
                    SET backup_codes = ?
                    WHERE user_id = ?;
                    """,
                    (json.dumps(stored_codes), user_id),
                )
            AuthService.log_audit(
                conn,
                action="TOTP_BACKUP_CODE_USED",
                resource="user",
                resource_id=str(user_id),
                details="Emergency one-time backup recovery code consumed",
            )
            return True

        return False

    @staticmethod
    def disable_totp(conn: sqlite3.Connection, user_id: int) -> bool:
        """Deactivate two-factor authentication for an account."""
        with transaction(conn) as cursor:
            cursor.execute("DELETE FROM user_totp WHERE user_id = ?;", (user_id,))

        AuthService.log_audit(
            conn,
            action="TOTP_DISABLED",
            resource="user",
            resource_id=str(user_id),
            details="Two-factor authentication deactivated",
        )
        return True

    @staticmethod
    def get_totp_status(conn: sqlite3.Connection, user_id: int) -> Dict[str, bool]:
        """Inspect two-factor status and backup code availability."""
        cur = conn.cursor()
        cur.execute("SELECT is_enabled, backup_codes FROM user_totp WHERE user_id = ?;", (user_id,))
        row = cur.fetchone()
        cur.close()

        if not row:
            return {"is_enabled": False, "has_backup_codes": False}

        stored_codes = json.loads(row["backup_codes"] or "[]")
        return {
            "is_enabled": bool(row["is_enabled"]),
            "has_backup_codes": len(stored_codes) > 0,
        }

    # ---------------------------------------------------------
    # 3. Active Session Management
    # ---------------------------------------------------------

    @staticmethod
    def register_session(
        conn: sqlite3.Connection,
        user_id: int,
        session_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """Record an active session upon login."""
        try:
            with transaction(conn) as cursor:
                cursor.execute(
                    """
                    INSERT INTO user_sessions (user_id, session_id, ip_address, user_agent, is_revoked)
                    VALUES (?, ?, ?, ?, 0)
                    ON CONFLICT(session_id) DO UPDATE SET
                        last_active = CURRENT_TIMESTAMP,
                        is_revoked = 0;
                    """,
                    (user_id, session_id, ip_address, user_agent),
                )
        except Exception as e:
            logger.warning("Failed to register session record: %s", e)

    @staticmethod
    def list_sessions(
        conn: sqlite3.Connection,
        user_id: int,
        current_session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List active non-revoked sessions for an account."""
        cur = conn.cursor()
        cur.execute(
            """
            SELECT session_id, ip_address, user_agent, last_active
            FROM user_sessions
            WHERE user_id = ? AND is_revoked = 0
            ORDER BY last_active DESC;
            """,
            (user_id,),
        )
        rows = cur.fetchall()
        cur.close()

        results = []
        for r in rows:
            results.append(
                {
                    "session_id": r["session_id"],
                    "ip_address": r["ip_address"] or "Unknown",
                    "user_agent": r["user_agent"] or "Unknown Device",
                    "last_active": str(r["last_active"]),
                    "is_current": (r["session_id"] == current_session_id)
                    if current_session_id
                    else False,
                }
            )
        return results

    @staticmethod
    def revoke_session(
        conn: sqlite3.Connection,
        user_id: int,
        session_id: str,
    ) -> bool:
        """Terminate a specific remote device session."""
        with transaction(conn) as cursor:
            cursor.execute(
                """
                UPDATE user_sessions
                SET is_revoked = 1
                WHERE user_id = ? AND session_id = ?;
                """,
                (user_id, session_id),
            )
        AuthService.log_audit(
            conn,
            action="SESSION_REVOKED",
            resource="user",
            resource_id=str(user_id),
            details=f"Remote session {session_id[:8]}... revoked",
        )
        return True
