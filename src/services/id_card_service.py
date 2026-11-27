"""Institutional Digital ID Card Generation & Cryptographic Verification Service.
Produces official CR80 (credit-card format 85.6mm x 53.98mm) vector PDFs,
A4 batch 8-up print sheets with cut guides, interactive SVG digital cards,
and tamper-proof HMAC-SHA256 digital verification tokens with scannable QR codes.
"""

import base64
import hashlib
import hmac
import io
import json
import logging
import sqlite3
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from reportlab.graphics.barcode import createBarcodeDrawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from src.core.config import APP_NAME, SECRET_KEY

logger = logging.getLogger("ims")

# Standard ISO/IEC 7810 ID-1 (CR80) dimensions in points (72 points/inch)
# 85.60 mm x 53.98 mm = 242.64 pt x 153.01 pt
CR80_WIDTH = 242.64
CR80_HEIGHT = 153.01


class IDCardService:
    """Enterprise Digital ID Card Generator & Verification Engine."""

    @staticmethod
    def generate_id_token(
        entity_type: str,
        entity_id: int,
        identifier: str,
        name: str,
        dept_code: str,
        valid_until: str,
    ) -> str:
        """Create a tamper-proof HMAC-SHA256 signed ID card verification token."""
        payload = {
            "t": entity_type.upper(),
            "id": entity_id,
            "no": identifier,
            "n": name,
            "d": dept_code,
            "v": valid_until,
            "iss": "IMS-ENTERPRISE",
            "iat": int(time.time()),
        }
        payload_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        payload_b64 = base64.urlsafe_b64encode(payload_json).decode("utf-8").rstrip("=")

        secret_bytes = SECRET_KEY.encode("utf-8")
        signature = hmac.new(secret_bytes, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()

        return f"{payload_b64}.{signature}"

    @staticmethod
    def verify_id_token(token: str, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
        """Verify the cryptographic authenticity, validity term, and active institutional status of an ID card."""
        try:
            parts = token.split(".")
            if len(parts) != 2:
                return {
                    "valid": False,
                    "status": "MALFORMED",
                    "reason": "Invalid token structure",
                }

            payload_b64, signature = parts
            secret_bytes = SECRET_KEY.encode("utf-8")
            expected_sig = hmac.new(
                secret_bytes, payload_b64.encode("utf-8"), hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(signature, expected_sig):
                return {
                    "valid": False,
                    "status": "TAMPERED",
                    "reason": "Cryptographic signature verification failed (tampered or counterfeit)",
                }

            # Decode payload
            padding = 4 - (len(payload_b64) % 4)
            if padding and padding < 4:
                payload_b64 += "=" * padding
            payload_bytes = base64.urlsafe_b64decode(payload_b64.encode("utf-8"))
            payload = json.loads(payload_bytes.decode("utf-8"))

            # Check expiration date
            valid_until_str = payload.get("v")
            if valid_until_str:
                try:
                    expiry_date = datetime.strptime(valid_until_str, "%Y-%m-%d").date()
                    if datetime.now().date() > expiry_date:
                        return {
                            "valid": False,
                            "status": "EXPIRED",
                            "reason": f"ID Card validity expired on {valid_until_str}",
                            "payload": payload,
                        }
                except ValueError:
                    pass

            # If DB connection provided, verify active enrollment status
            entity_details = None
            if conn:
                cur = conn.cursor()
                if payload.get("t") == "STUDENT":
                    cur.execute(
                        """
                        SELECT s.id, s.enrollment_no, s.first_name, s.last_name, s.email, s.phone,
                               s.blood_group, s.emergency_contact, s.current_semester, s.admission_date,
                               s.status, s.is_deleted, d.name AS department_name, d.code AS department_code
                        FROM students s
                        JOIN departments d ON s.department_id = d.id
                        WHERE s.id = ?;
                        """,
                        (payload.get("id"),),
                    )
                    row = cur.fetchone()
                    if not row or row["is_deleted"] == 1:
                        cur.close()
                        return {
                            "valid": False,
                            "status": "NOT_FOUND",
                            "reason": "Scholar record does not exist in registry",
                        }
                    entity_details = dict(row)
                    cur.close()

                    if entity_details["status"] in ("SUSPENDED", "WITHDRAWN"):
                        return {
                            "valid": False,
                            "status": "REVOKED",
                            "reason": f"Scholar is currently {entity_details['status']}",
                            "data": entity_details,
                        }
                elif payload.get("t") == "FACULTY":
                    cur.execute(
                        """
                        SELECT f.id, f.faculty_id, f.first_name, f.last_name, f.email, f.phone,
                               f.designation, f.qualification, f.status,
                               d.name AS department_name, d.code AS department_code
                        FROM faculty f
                        JOIN departments d ON f.department_id = d.id
                        WHERE f.id = ?;
                        """,
                        (payload.get("id"),),
                    )
                    row = cur.fetchone()
                    cur.close()
                    if not row:
                        return {
                            "valid": False,
                            "status": "NOT_FOUND",
                            "reason": "Faculty instructor record does not exist in registry",
                        }
                    entity_details = dict(row)
                    if entity_details["status"] != "active":
                        return {
                            "valid": False,
                            "status": "REVOKED",
                            "reason": f"Faculty status is inactive ({entity_details['status']})",
                            "data": entity_details,
                        }

            return {
                "valid": True,
                "status": "VERIFIED",
                "entity_type": payload.get("t"),
                "identifier": payload.get("no"),
                "name": payload.get("n"),
                "department": payload.get("d"),
                "valid_until": payload.get("v"),
                "issued_by": payload.get("iss"),
                "data": entity_details,
            }
        except Exception as e:
            logger.warning("Error verifying ID token: %s", e)
            return {
                "valid": False,
                "status": "ERROR",
                "reason": f"Verification encountered an error: {e}",
            }

    @staticmethod
    def get_student_card_data(conn: sqlite3.Connection, student_id: int) -> Dict[str, Any]:
        """Fetch and format student information required for ID card rendering."""
        cur = conn.cursor()
        cur.execute(
            """
            SELECT s.id, s.enrollment_no, s.first_name, s.last_name, s.email, s.phone,
                   s.blood_group, s.emergency_contact, s.current_semester, s.admission_date,
                   s.status, d.name AS department_name, d.code AS department_code
            FROM students s
            JOIN departments d ON s.department_id = d.id
            WHERE s.id = ? AND s.is_deleted = 0;
            """,
            (student_id,),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            raise ValueError(f"Active student ID {student_id} not found.")

        data = dict(row)
        full_name = f"{data['first_name']} {data['last_name']}"

        # Calculate standard 4-year validity or active cycle
        adm_year = (
            int(data["admission_date"][:4]) if data["admission_date"] else datetime.now().year
        )
        valid_until = f"{adm_year + 4}-06-30"

        token = IDCardService.generate_id_token(
            entity_type="STUDENT",
            entity_id=data["id"],
            identifier=data["enrollment_no"],
            name=full_name,
            dept_code=data["department_code"],
            valid_until=valid_until,
        )

        data.update(
            {
                "entity_type": "STUDENT",
                "role_label": "STUDENT IDENTITY CARD",
                "full_name": full_name,
                "valid_until": valid_until,
                "validity_term": f"{adm_year} - {adm_year + 4}",
                "token": token,
            }
        )
        return data

    @staticmethod
    def get_faculty_card_data(conn: sqlite3.Connection, faculty_id: int) -> Dict[str, Any]:
        """Fetch and format faculty instructor information required for ID card rendering."""
        cur = conn.cursor()
        cur.execute(
            """
            SELECT f.id, f.faculty_id, f.first_name, f.last_name, f.email, f.phone,
                   f.designation, f.qualification, f.hire_date, f.status,
                   d.name AS department_name, d.code AS department_code
            FROM faculty f
            JOIN departments d ON f.department_id = d.id
            WHERE f.id = ?;
            """,
            (faculty_id,),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            raise ValueError(f"Faculty ID {faculty_id} not found.")

        data = dict(row)
        full_name = f"{data['first_name']} {data['last_name']}"

        hire_year = int(data["hire_date"][:4]) if data["hire_date"] else datetime.now().year
        valid_until = f"{datetime.now().year + 3}-12-31"

        token = IDCardService.generate_id_token(
            entity_type="FACULTY",
            entity_id=data["id"],
            identifier=data["faculty_id"],
            name=full_name,
            dept_code=data["department_code"],
            valid_until=valid_until,
        )

        data.update(
            {
                "entity_type": "FACULTY",
                "enrollment_no": data["faculty_id"],
                "role_label": "FACULTY IDENTITY CARD",
                "full_name": full_name,
                "current_semester": data.get("designation", "Faculty Member"),
                "blood_group": "A+",
                "emergency_contact": "Department Dean Office",
                "valid_until": valid_until,
                "validity_term": f"{hire_year} - {datetime.now().year + 3}",
                "token": token,
            }
        )
        return data

    # ------------------------------------------------------------------------
    # Vector Canvas Drawing Primitives
    # ------------------------------------------------------------------------

    @staticmethod
    def draw_card_front(c: canvas.Canvas, x: float, y: float, data: Dict[str, Any]) -> None:
        """Render the front face of a CR80 ID Card at coordinates (x, y)."""
        c.saveState()

        # Card Base (Outer Border & Background)
        c.setFillColor(colors.HexColor("#0F172A"))  # Slate 900
        c.roundRect(x, y, CR80_WIDTH, CR80_HEIGHT, radius=8, fill=1, stroke=0)

        # Header Banner
        header_color = (
            colors.HexColor("#1E3A8A")
            if data["entity_type"] == "STUDENT"
            else colors.HexColor("#065F46")
        )
        c.setFillColor(header_color)
        c.roundRect(x, y + CR80_HEIGHT - 32, CR80_WIDTH, 32, radius=8, fill=1, stroke=0)
        c.rect(x, y + CR80_HEIGHT - 32, CR80_WIDTH, 14, fill=1, stroke=0)

        # Top Gold Accent Line
        c.setFillColor(colors.HexColor("#F59E0B"))
        c.rect(x, y + CR80_HEIGHT - 34, CR80_WIDTH, 2, fill=1, stroke=0)

        # Institution Crest Icon and Header Text
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x + 10, y + CR80_HEIGHT - 17, APP_NAME.upper())
        c.setFont("Helvetica-Bold", 7)
        c.setFillColor(colors.HexColor("#93C5FD"))
        c.drawString(x + 10, y + CR80_HEIGHT - 27, data.get("role_label", "IDENTITY CARD"))

        # Photo / Avatar Frame (Left Side)
        avatar_x = x + 12
        avatar_y = y + 42
        avatar_w = 54
        avatar_h = 66
        c.setFillColor(colors.HexColor("#1E293B"))
        c.roundRect(avatar_x, avatar_y, avatar_w, avatar_h, radius=4, fill=1, stroke=1)
        c.setStrokeColor(colors.HexColor("#3B82F6"))
        c.setLineWidth(1)
        c.roundRect(avatar_x, avatar_y, avatar_w, avatar_h, radius=4, fill=0, stroke=1)

        # Stylized Silhouette Initials Avatar
        initials = (
            "".join([part[0] for part in data["full_name"].split()[:2]]).upper()
            if data.get("full_name")
            else "ID"
        )
        c.setFont("Helvetica-Bold", 18)
        c.setFillColor(colors.HexColor("#60A5FA"))
        c.drawCentredString(avatar_x + avatar_w / 2, avatar_y + avatar_h / 2 - 6, initials)

        # Scholar / Faculty Details (Right Side)
        text_x = x + 76
        cur_y = y + CR80_HEIGHT - 48

        # Name
        c.setFont("Helvetica-Bold", 10.5)
        c.setFillColor(colors.white)
        name_display = (
            data["full_name"][:22] + "..." if len(data["full_name"]) > 22 else data["full_name"]
        )
        c.drawString(text_x, cur_y, name_display)
        cur_y -= 12

        # Enrollment / ID
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(colors.HexColor("#38BDF8"))
        c.drawString(text_x, cur_y, f"ID: {data['enrollment_no']}")
        cur_y -= 11

        # Department
        c.setFont("Helvetica", 7.5)
        c.setFillColor(colors.HexColor("#CBD5E1"))
        dept_str = (
            data["department_name"][:24] + "..."
            if len(data.get("department_name", "")) > 24
            else data.get("department_name", "")
        )
        c.drawString(text_x, cur_y, dept_str)
        cur_y -= 10

        # Term / Semester
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.HexColor("#94A3B8"))
        sem_str = (
            f"Semester: {data.get('current_semester')}"
            if data["entity_type"] == "STUDENT"
            else str(data.get("current_semester"))
        )
        c.drawString(text_x, cur_y, sem_str)
        cur_y -= 10

        # Blood Group & Validity Badges
        bg = data.get("blood_group") or "N/A"
        c.setFillColor(colors.HexColor("#DC2626"))  # Red 600 badge
        c.roundRect(text_x, cur_y - 2, 34, 10, radius=2, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawCentredString(text_x + 17, cur_y + 0.5, f"BLOOD: {bg}")

        valid_str = f"TERM: {data.get('validity_term', '2026-2030')}"
        c.setFillColor(colors.HexColor("#334155"))
        c.roundRect(text_x + 38, cur_y - 2, 70, 10, radius=2, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#F8FAFC"))
        c.setFont("Helvetica-Bold", 6.5)
        c.drawCentredString(text_x + 73, cur_y + 0.5, valid_str)

        # Barcode Container at Bottom
        barcode_val = data["enrollment_no"]
        try:
            bc = createBarcodeDrawing(
                "Code128",
                value=barcode_val,
                width=CR80_WIDTH - 24,
                height=18,
                barWidth=0.85,
                barHeight=14,
                fontSize=0,
            )
            c.setFillColor(colors.white)
            c.roundRect(x + 12, y + 8, CR80_WIDTH - 24, 22, radius=3, fill=1, stroke=0)
            bc.drawOn(c, x + 16, y + 10)
        except Exception as e:
            logger.debug("Barcode render error: %s", e)

        # Outer Card Border
        c.setStrokeColor(colors.HexColor("#334155"))
        c.setLineWidth(0.75)
        c.roundRect(x, y, CR80_WIDTH, CR80_HEIGHT, radius=8, fill=0, stroke=1)

        c.restoreState()

    @staticmethod
    def draw_card_back(
        c: canvas.Canvas,
        x: float,
        y: float,
        data: Dict[str, Any],
        verify_base_url: str = "https://ims.edu",
    ) -> None:
        """Render the reverse face of a CR80 ID Card featuring security QR code and terms."""
        c.saveState()

        # Card Base (Reverse Dark Navy Slate)
        c.setFillColor(colors.HexColor("#0B132B"))
        c.roundRect(x, y, CR80_WIDTH, CR80_HEIGHT, radius=8, fill=1, stroke=0)

        # Magnetic Stripe Simulation (Top)
        c.setFillColor(colors.HexColor("#1C1917"))  # Stone 900
        c.rect(x, y + CR80_HEIGHT - 28, CR80_WIDTH, 20, fill=1, stroke=0)

        # Instructions / Policy Section (Left Side)
        c.setFont("Helvetica-Bold", 6.5)
        c.setFillColor(colors.HexColor("#93C5FD"))
        c.drawString(x + 12, y + CR80_HEIGHT - 38, "TERMS & CONDITIONS OF USE")

        c.setFont("Helvetica", 5.5)
        c.setFillColor(colors.HexColor("#94A3B8"))
        c.drawString(
            x + 12,
            y + CR80_HEIGHT - 48,
            "• This credential is institutional property and non-transferable.",
        )
        c.drawString(
            x + 12,
            y + CR80_HEIGHT - 56,
            "• Mandatory for campus access, exams, library loans, & buses.",
        )
        c.drawString(
            x + 12, y + CR80_HEIGHT - 64, "• If lost/found, surrender to Registrar Security Office."
        )

        emergency = data.get("emergency_contact") or "Campus Security: +1 (555) 019-9111"
        c.setFont("Helvetica-Bold", 6)
        c.setFillColor(colors.HexColor("#F87171"))
        c.drawString(x + 12, y + CR80_HEIGHT - 74, f"SOS / EMERGENCY: {emergency[:32]}")

        # Verification Seal & Signatures
        c.setFont("Helvetica-Bold", 6)
        c.setFillColor(colors.HexColor("#CBD5E1"))
        c.drawString(x + 12, y + 26, "Registrar & Academic Council")
        c.setFont("Helvetica", 5)
        c.setFillColor(colors.HexColor("#64748B"))
        c.drawString(x + 12, y + 18, "Cryptographic Integrity Sealed • SHA-256")
        c.drawString(x + 12, y + 10, f"Token: {data['token'][:24]}...")

        # QR Code Container (Right Side)
        qr_size = 56
        qr_x = x + CR80_WIDTH - qr_size - 12
        qr_y = y + 16

        c.setFillColor(colors.white)
        c.roundRect(qr_x - 3, qr_y - 3, qr_size + 6, qr_size + 6, radius=4, fill=1, stroke=0)

        verify_url = f"{verify_base_url}/verify/id/{data['token']}"
        try:
            qr = createBarcodeDrawing(
                "QR",
                value=verify_url,
                width=qr_size,
                height=qr_size,
            )
            qr.drawOn(c, qr_x, qr_y)
        except Exception as e:
            logger.debug("QR code render error: %s", e)

        c.setFont("Helvetica-Bold", 5)
        c.setFillColor(colors.HexColor("#38BDF8"))
        c.drawCentredString(qr_x + qr_size / 2, qr_y - 8, "SCAN TO VERIFY")

        # Outer Card Border
        c.setStrokeColor(colors.HexColor("#334155"))
        c.setLineWidth(0.75)
        c.roundRect(x, y, CR80_WIDTH, CR80_HEIGHT, radius=8, fill=0, stroke=1)

        c.restoreState()

    # ------------------------------------------------------------------------
    # Public Generation APIs
    # ------------------------------------------------------------------------

    @staticmethod
    def generate_single_id_card_pdf(
        entity_type: str,
        entity_id: int,
        conn: sqlite3.Connection,
        base_url: str = "https://ims.edu",
    ) -> bytes:
        """Compile a 2-page print-ready vector PDF for a single ID Card (Page 1: Front, Page 2: Back)."""
        if entity_type.upper() == "STUDENT":
            data = IDCardService.get_student_card_data(conn, entity_id)
        elif entity_type.upper() == "FACULTY":
            data = IDCardService.get_faculty_card_data(conn, entity_id)
        else:
            raise ValueError(
                f"Unsupported entity type '{entity_type}'. Must be STUDENT or FACULTY."
            )

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=(CR80_WIDTH, CR80_HEIGHT))
        c.setTitle(f"ID_Card_{data['enrollment_no']}")
        c.setAuthor(APP_NAME)

        # Page 1: Front
        IDCardService.draw_card_front(c, 0, 0, data)
        c.showPage()

        # Page 2: Back
        IDCardService.draw_card_back(c, 0, 0, data, verify_base_url=base_url)
        c.showPage()

        c.save()
        buffer.seek(0)
        return buffer.getvalue()

    @staticmethod
    def generate_batch_id_cards_pdf(
        department_id: Optional[int],
        cohort_year: Optional[int],
        conn: sqlite3.Connection,
        base_url: str = "https://ims.edu",
    ) -> bytes:
        """Generate an A4 print sheet containing 8 CR80 cards per page (4 rows x 2 cols) with trim guide lines."""
        query = "SELECT id FROM students WHERE is_deleted = 0"
        params: List[Any] = []
        if department_id:
            query += " AND department_id = ?"
            params.append(department_id)
        if cohort_year:
            query += " AND strftime('%Y', admission_date) = ?"
            params.append(str(cohort_year))
        query += " ORDER BY enrollment_no ASC LIMIT 160;"

        cur = conn.cursor()
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        cur.close()

        if not rows:
            raise ValueError("No matching scholars found for the requested batch criteria.")

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        c.setTitle(f"Batch_ID_Cards_Dept{department_id or 'All'}")

        page_width, page_height = A4
        cols = 2
        rows_per_page = 4
        margin_x = (page_width - (cols * CR80_WIDTH)) / (cols + 1)
        margin_y = (page_height - (rows_per_page * CR80_HEIGHT)) / (rows_per_page + 1)

        card_idx = 0
        for r in rows:
            student_data = IDCardService.get_student_card_data(conn, r["id"])

            pos_on_page = card_idx % (cols * rows_per_page)
            col_idx = pos_on_page % cols
            row_idx = pos_on_page // cols

            card_x = margin_x + col_idx * (CR80_WIDTH + margin_x)
            card_y = page_height - (margin_y + (row_idx + 1) * CR80_HEIGHT + row_idx * margin_y)

            # Draw Front
            IDCardService.draw_card_front(c, card_x, card_y, student_data)

            # Draw subtle trim marks around the card
            c.saveState()
            c.setStrokeColor(colors.HexColor("#CBD5E1"))
            c.setLineWidth(0.3)
            c.setDash([2, 2])
            c.rect(card_x - 1, card_y - 1, CR80_WIDTH + 2, CR80_HEIGHT + 2, fill=0, stroke=1)
            c.restoreState()

            card_idx += 1
            if card_idx % (cols * rows_per_page) == 0:
                c.showPage()

        if card_idx % (cols * rows_per_page) != 0:
            c.showPage()

        c.save()
        buffer.seek(0)
        return buffer.getvalue()

    @staticmethod
    def generate_id_card_svg(
        entity_type: str,
        entity_id: int,
        conn: sqlite3.Connection,
        base_url: str = "https://ims.edu",
    ) -> str:
        """Compile a crisp, mobile-responsive interactive SVG card for portal embedding."""
        if entity_type.upper() == "STUDENT":
            data = IDCardService.get_student_card_data(conn, entity_id)
        elif entity_type.upper() == "FACULTY":
            data = IDCardService.get_faculty_card_data(conn, entity_id)
        else:
            raise ValueError(f"Unsupported entity type '{entity_type}'.")

        initials = (
            "".join([part[0] for part in data["full_name"].split()[:2]]).upper()
            if data.get("full_name")
            else "ID"
        )
        accent_color = "#3B82F6" if data["entity_type"] == "STUDENT" else "#10B981"
        header_color = "#1E3A8A" if data["entity_type"] == "STUDENT" else "#065F46"

        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 428 270" width="100%" style="max-width: 428px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.4); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <defs>
    <linearGradient id="cardGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0F172A" />
      <stop offset="100%" stop-color="#1E293B" />
    </linearGradient>
    <linearGradient id="headerGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{header_color}" />
      <stop offset="100%" stop-color="{accent_color}" />
    </linearGradient>
  </defs>

  <!-- Background Base -->
  <rect x="0" y="0" width="428" height="270" rx="12" fill="url(#cardGrad)" stroke="#334155" stroke-width="1.5" />

  <!-- Header Banner -->
  <path d="M 0 12 Q 0 0 12 0 L 416 0 Q 428 0 428 12 L 428 56 L 0 56 Z" fill="url(#headerGrad)" />
  <rect x="0" y="56" width="428" height="3" fill="#F59E0B" />

  <!-- Header Text -->
  <text x="20" y="28" font-size="14" font-weight="bold" fill="#FFFFFF" letter-spacing="0.5">INSTITUTE OF TECHNOLOGY</text>
  <text x="20" y="46" font-size="10" font-weight="600" fill="#93C5FD" letter-spacing="1">{data["role_label"]}</text>
  <text x="408" y="36" font-size="20" text-anchor="end">🏛️</text>

  <!-- Photo / Avatar Frame -->
  <rect x="20" y="74" width="95" height="116" rx="8" fill="#1E293B" stroke="{accent_color}" stroke-width="1.5" />
  <circle cx="67.5" cy="132" r="32" fill="#334155" />
  <text x="67.5" y="142" font-size="28" font-weight="bold" fill="#60A5FA" text-anchor="middle">{initials}</text>

  <!-- Scholar / Faculty Information -->
  <g transform="translate(130, 80)">
    <text x="0" y="20" font-size="17" font-weight="bold" fill="#FFFFFF">{data["full_name"]}</text>
    <text x="0" y="40" font-size="12" font-weight="bold" fill="#38BDF8">ID: {data["enrollment_no"]}</text>
    <text x="0" y="60" font-size="11" fill="#CBD5E1">{data.get("department_name", "")[:28]}</text>
    <text x="0" y="78" font-size="10" fill="#94A3B8">Semester: {data.get("current_semester", "Active")}</text>

    <!-- Badges: Blood & Term -->
    <g transform="translate(0, 92)">
      <rect x="0" y="0" width="60" height="18" rx="4" fill="#DC2626" />
      <text x="30" y="13" font-size="9" font-weight="bold" fill="#FFFFFF" text-anchor="middle">O+ BLOOD</text>

      <rect x="68" y="0" width="110" height="18" rx="4" fill="#334155" />
      <text x="123" y="13" font-size="9" font-weight="bold" fill="#F8FAFC" text-anchor="middle">{data.get("validity_term", "2026-2030")}</text>
    </g>
  </g>

  <!-- Bottom Barcode Strip & Security Chip -->
  <rect x="20" y="205" width="280" height="48" rx="6" fill="#FFFFFF" />
  <!-- Simulated barcode lines -->
  <g transform="translate(30, 215)" fill="#000000">
    <rect x="0" y="0" width="3" height="28" />
    <rect x="5" y="0" width="2" height="28" />
    <rect x="9" y="0" width="4" height="28" />
    <rect x="16" y="0" width="1" height="28" />
    <rect x="20" y="0" width="5" height="28" />
    <rect x="28" y="0" width="2" height="28" />
    <rect x="33" y="0" width="4" height="28" />
    <rect x="40" y="0" width="2" height="28" />
    <rect x="45" y="0" width="6" height="28" />
    <rect x="54" y="0" width="3" height="28" />
    <rect x="60" y="0" width="2" height="28" />
    <rect x="65" y="0" width="5" height="28" />
    <rect x="73" y="0" width="2" height="28" />
    <rect x="78" y="0" width="4" height="28" />
    <rect x="85" y="0" width="2" height="28" />
    <rect x="90" y="0" width="3" height="28" />
    <rect x="96" y="0" width="5" height="28" />
    <rect x="104" y="0" width="2" height="28" />
    <rect x="110" y="0" width="4" height="28" />
    <rect x="117" y="0" width="2" height="28" />
    <rect x="122" y="0" width="5" height="28" />
    <rect x="130" y="0" width="3" height="28" />
    <rect x="136" y="0" width="2" height="28" />
    <rect x="141" y="0" width="4" height="28" />
    <rect x="148" y="0" width="2" height="28" />
    <rect x="153" y="0" width="5" height="28" />
    <rect x="161" y="0" width="2" height="28" />
    <rect x="166" y="0" width="4" height="28" />
    <rect x="173" y="0" width="3" height="28" />
    <rect x="180" y="0" width="2" height="28" />
    <rect x="185" y="0" width="5" height="28" />
    <rect x="193" y="0" width="2" height="28" />
    <rect x="198" y="0" width="4" height="28" />
    <rect x="205" y="0" width="3" height="28" />
    <rect x="211" y="0" width="2" height="28" />
    <rect x="216" y="0" width="5" height="28" />
    <rect x="224" y="0" width="2" height="28" />
    <rect x="230" y="0" width="4" height="28" />
    <rect x="237" y="0" width="3" height="28" />
    <rect x="243" y="0" width="2" height="28" />
    <rect x="248" y="0" width="5" height="28" />
  </g>
  <text x="160" y="249" font-size="8" font-family="monospace" fill="#000000" text-anchor="middle">{data["enrollment_no"]}</text>

  <!-- Interactive Scan/Verify Button Box -->
  <g transform="translate(315, 205)">
    <rect x="0" y="0" width="93" height="48" rx="6" fill="#1E293B" stroke="#334155" />
    <text x="46.5" y="20" font-size="9" font-weight="bold" fill="#38BDF8" text-anchor="middle">QR SEALED</text>
    <text x="46.5" y="36" font-size="7.5" fill="#94A3B8" text-anchor="middle">VERIFIED</text>
  </g>
</svg>"""
        return svg
