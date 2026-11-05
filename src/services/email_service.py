"""Institutional Email Dispatch Service & Template Renderer.
Supports pluggable transports (Mock, Console, SMTP), rich HTML email rendering,
background asynchronous queuing, and compliance journal logging.
"""

import logging
import smtplib
import sqlite3
import threading
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

import jinja2

from src.core.config import (
    EMAIL_BACKEND,
    EMAIL_FROM,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_TLS,
    SMTP_USER,
    TEMPLATES_DIR,
)
from src.core.tasks import enqueue_background_task
from src.database.connection import get_connection, release_connection, transaction
from src.database.utils import rows_to_list

logger = logging.getLogger("ims")

# Jinja2 environment dedicated to rendering HTML emails
_email_template_dir = TEMPLATES_DIR / "emails"
_email_jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(_email_template_dir)),
    autoescape=jinja2.select_autoescape(["html", "xml"]),
)


class MockEmailBackend:
    """In-memory mock email backend for unit testing and local offline development."""

    _sent: List[Dict[str, Any]] = []
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def send(cls, message: Dict[str, Any]) -> Dict[str, Any]:
        with cls._lock:
            cls._sent.append(message)
        logger.info("[MOCK EMAIL] Sent to %s: '%s'", message["recipient"], message["subject"])
        return {
            "status": "SENT",
            "message_id": message.get("message_id"),
            "recipient": message["recipient"],
            "subject": message["subject"],
        }

    @classmethod
    def get_sent(cls) -> List[Dict[str, Any]]:
        with cls._lock:
            return list(cls._sent)

    @classmethod
    def get_outbox(cls) -> List[Dict[str, Any]]:
        return cls.get_sent()

    @classmethod
    def clear(cls) -> None:
        with cls._lock:
            cls._sent.clear()

    @classmethod
    def clear_outbox(cls) -> None:
        cls.clear()


class ConsoleEmailBackend:
    """Terminal/stdout logger email backend."""

    @staticmethod
    def send(message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(
            "==================== EMAIL DISPATCH ====================\n"
            "To: %s\nFrom: %s\nSubject: %s\n\n%s\n"
            "========================================================",
            message["recipient"],
            message["sender"],
            message["subject"],
            message["body_text"],
        )
        return {
            "status": "SENT",
            "message_id": message.get("message_id"),
            "recipient": message["recipient"],
            "subject": message["subject"],
        }


class SMTPEmailBackend:
    """Production SMTP transport backend with STARTTLS and authentication."""

    @staticmethod
    def send(message: Dict[str, Any]) -> Dict[str, Any]:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = message["subject"]
        msg["From"] = message["sender"]
        msg["To"] = message["recipient"]

        part1 = MIMEText(message["body_text"], "plain")
        msg.attach(part1)

        if message.get("body_html"):
            part2 = MIMEText(message["body_html"], "html")
            msg.attach(part2)

        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
        try:
            if SMTP_TLS:
                server.starttls()
            if SMTP_USER and SMTP_PASSWORD:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(message["sender"], [message["recipient"]], msg.as_string())
        finally:
            server.quit()

        logger.info("[SMTP EMAIL] Delivered to %s: '%s'", message["recipient"], message["subject"])
        return {
            "status": "SENT",
            "message_id": message.get("message_id"),
            "recipient": message["recipient"],
            "subject": message["subject"],
        }


class EmailService:
    """Institutional email communication and background dispatch service."""

    @staticmethod
    def _record_email_log(
        recipient: str,
        subject: str,
        template: Optional[str],
        status: str,
        error_message: Optional[str] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> None:
        """Record email delivery result into immutable email_logs table."""
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            with transaction(conn) as cur:
                cur.execute(
                    """
                    INSERT INTO email_logs (recipient, subject, template, status, error_message)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (recipient, subject, template, status, error_message),
                )
        except Exception as e:
            logger.warning("Failed to record email log: %s", e)
        finally:
            if should_release:
                release_connection(conn)

    @staticmethod
    def send_email(
        recipient: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        template_name: Optional[str] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> Dict[str, Any]:
        """Dispatch email immediately using the active transport backend."""
        message_id = f"msg_{uuid.uuid4().hex[:12]}"
        msg_payload = {
            "message_id": message_id,
            "sender": EMAIL_FROM,
            "recipient": recipient,
            "subject": subject,
            "body_text": body_text,
            "body_html": body_html,
            "template": template_name,
        }

        backend = EMAIL_BACKEND.lower()
        try:
            if backend == "smtp":
                result = SMTPEmailBackend.send(msg_payload)
            elif backend == "console":
                result = ConsoleEmailBackend.send(msg_payload)
            else:
                result = MockEmailBackend.send(msg_payload)

            EmailService._record_email_log(
                recipient=recipient,
                subject=subject,
                template=template_name,
                status=result.get("status", "SENT"),
                error_message=None,
                conn=conn,
            )
            return result
        except Exception as err:
            err_msg = str(err)
            logger.error("Email dispatch to %s failed: %s", recipient, err_msg)
            EmailService._record_email_log(
                recipient=recipient,
                subject=subject,
                template=template_name,
                status="FAILED",
                error_message=err_msg,
                conn=conn,
            )
            return {
                "status": "FAILED",
                "message_id": message_id,
                "recipient": recipient,
                "subject": subject,
                "error": err_msg,
            }

    @staticmethod
    def send_email_async(
        recipient: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        template_name: Optional[str] = None,
    ) -> None:
        """Schedule email to be dispatched in the background worker thread pool."""
        enqueue_background_task(
            EmailService.send_email,
            recipient=recipient,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            template_name=template_name,
        )

    @staticmethod
    def send_fee_receipt_email(
        recipient: str,
        student_name: str,
        payment_dict: Dict[str, Any],
        async_send: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Render and dispatch official electronic bursar payment receipt."""
        subject = f"Official Fee Payment Receipt #{payment_dict.get('receipt_number', 'IMS')}"
        body_text = (
            f"Dear {student_name},\n\n"
            f"Your fee payment of Rs. {payment_dict.get('amount_paid', 0.0):.2f} has been verified.\n"
            f"Receipt Number: {payment_dict.get('receipt_number')}\n"
            f"Transaction Date: {payment_dict.get('payment_date')}\n"
            f"Remaining Balance: Rs. {payment_dict.get('balance_after', 0.0):.2f}\n\n"
            f"Thank you,\nOffice of the Bursar"
        )

        try:
            tmpl = _email_jinja_env.get_template("fee_receipt.html")
            body_html = tmpl.render(student_name=student_name, payment=payment_dict)
        except Exception as e:
            logger.warning("Failed to render fee_receipt.html email template: %s", e)
            body_html = None

        if async_send:
            EmailService.send_email_async(
                recipient=recipient,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                template_name="fee_receipt",
            )
            return {"status": "QUEUED", "recipient": recipient, "subject": subject}
        return EmailService.send_email(
            recipient=recipient,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            template_name="fee_receipt",
        )

    @staticmethod
    def send_leave_decision_email(
        recipient: str,
        applicant_name: str,
        leave_dict: Dict[str, Any],
        async_send: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Render and dispatch leave petition decision notification."""
        status_val = leave_dict.get("status", "REVIEWED")
        subject = f"Absence Petition #{leave_dict.get('id')}: {status_val}"
        body_text = (
            f"Dear {applicant_name},\n\n"
            f"Your institutional absence petition (#{leave_dict.get('id')}) has been reviewed.\n"
            f"Decision: {status_val}\n"
            f"Dates: {leave_dict.get('start_date')} to {leave_dict.get('end_date')}\n"
            f"Remarks: {leave_dict.get('review_remarks', 'None')}\n\n"
            f"Office of Academic Affairs"
        )

        try:
            tmpl = _email_jinja_env.get_template("leave_decision.html")
            body_html = tmpl.render(applicant_name=applicant_name, leave=leave_dict)
        except Exception as e:
            logger.warning("Failed to render leave_decision.html email template: %s", e)
            body_html = None

        if async_send:
            EmailService.send_email_async(
                recipient=recipient,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                template_name="leave_decision",
            )
            return {"status": "QUEUED", "recipient": recipient, "subject": subject}
        return EmailService.send_email(
            recipient=recipient,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            template_name="leave_decision",
        )

    @staticmethod
    def send_attendance_alert_email(
        recipient: str,
        student_name: str,
        course_code: str,
        course_title: str,
        attended_sessions: int,
        total_sessions: int,
        attendance_percentage: float,
        async_send: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Render and dispatch academic low-attendance warning (< 75%)."""
        subject = f"URGENT: Low Attendance Warning in {course_code} ({attendance_percentage:.1f}%)"
        body_text = (
            f"Dear {student_name},\n\n"
            f"Your attendance in {course_title} ({course_code}) is currently {attendance_percentage:.1f}% "
            f"({attended_sessions}/{total_sessions} sessions attended).\n"
            f"This falls below the mandatory 75% requirement. Please contact your instructor immediately.\n\n"
            f"Academic Registry"
        )

        try:
            tmpl = _email_jinja_env.get_template("attendance_alert.html")
            body_html = tmpl.render(
                student_name=student_name,
                course_code=course_code,
                course_title=course_title,
                attended_sessions=attended_sessions,
                total_sessions=total_sessions,
                attendance_percentage=attendance_percentage,
            )
        except Exception as e:
            logger.warning("Failed to render attendance_alert.html email template: %s", e)
            body_html = None

        if async_send:
            EmailService.send_email_async(
                recipient=recipient,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                template_name="attendance_alert",
            )
            return {"status": "QUEUED", "recipient": recipient, "subject": subject}
        return EmailService.send_email(
            recipient=recipient,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            template_name="attendance_alert",
        )

    @staticmethod
    def list_email_logs(
        conn: sqlite3.Connection,
        recipient: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Query historical email dispatch journal with filters and pagination."""
        query = "SELECT * FROM email_logs WHERE 1=1"
        count_query = "SELECT COUNT(*) AS total FROM email_logs WHERE 1=1"
        params: List[Any] = []

        if recipient:
            query += " AND recipient LIKE ?"
            count_query += " AND recipient LIKE ?"
            params.append(f"%{recipient.strip()}%")
        if status:
            query += " AND status = ?"
            count_query += " AND status = ?"
            params.append(status.strip().upper())

        cur = conn.cursor()
        cur.execute(count_query, tuple(params))
        total = cur.fetchone()["total"]

        query += " ORDER BY id DESC LIMIT ? OFFSET ?;"
        cur.execute(query, tuple(params + [limit, offset]))
        rows = cur.fetchall()
        cur.close()

        return {"total": total, "logs": rows_to_list(rows)}
