"""Native Binary PDF Generation Service.
Programmatic vector PDF compilation using ReportLab for official sealed transcripts,
bursar fee payment receipts, and clinical infirmary medical certificates.
"""

import io
import logging
import sqlite3
from datetime import datetime
from typing import Any, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.services.finance_service import FinanceService
from src.services.health_service import HealthService
from src.services.student_service import StudentService

logger = logging.getLogger("ims")


class PDFService:
    """Enterprise vector PDF document compiler."""

    @staticmethod
    def _create_watermark_callback(watermark_text: str, subtitle: str = "OFFICIAL DOCUMENT"):
        """Generate a ReportLab canvas callback for subtle rotated background watermark and pagination."""

        def on_page(canvas, doc):
            canvas.saveState()
            # Background Watermark
            canvas.setFont("Helvetica-Bold", 38)
            canvas.setFillColor(colors.Color(0.85, 0.88, 0.94, alpha=0.18))
            canvas.translate(A4[0] / 2, A4[1] / 2)
            canvas.rotate(42)
            canvas.drawCentredString(0, 0, watermark_text)
            canvas.restoreState()

            # Top Decorative Header Bar
            canvas.saveState()
            canvas.setFillColor(colors.HexColor("#1E3A8A"))
            canvas.rect(0, A4[1] - 8, A4[0], 8, stroke=0, fill=1)
            canvas.restoreState()

            # Bottom Running Footer
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.HexColor("#64748B"))
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            canvas.drawString(
                36, 22, f"Institute Management System • {subtitle} • Generated: {now_str}"
            )
            canvas.drawRightString(A4[0] - 36, 22, f"Page {doc.page}")
            canvas.setStrokeColor(colors.HexColor("#E2E8F0"))
            canvas.setLineWidth(0.5)
            canvas.line(36, 32, A4[0] - 36, 32)
            canvas.restoreState()

        return on_page

    @staticmethod
    def generate_transcript_pdf(conn: sqlite3.Connection, student_id: int) -> bytes:
        """Compile official sealed academic transcript vector PDF."""
        dossier = StudentService.get_student_portal_dossier(conn, student_id)
        if not dossier or not dossier.get("student"):
            raise KeyError(f"Student #{student_id} not found")

        student = dossier["student"]
        exam_results = dossier.get("exam_results", [])
        attendance = dossier.get("attendance", {})
        enrollments = dossier.get("enrollments", [])

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=42,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0F172A"),
            alignment=1,  # Center
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#475569"),
            alignment=1,
        )
        section_style = ParagraphStyle(
            "SectionHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#1E3A8A"),
            spaceAfter=4,
        )
        cell_bold = ParagraphStyle(
            "CellBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=10,
            textColor=colors.HexColor("#0F172A"),
        )
        cell_normal = ParagraphStyle(
            "CellNormal",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#334155"),
        )
        cell_header = ParagraphStyle(
            "CellHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
            alignment=1,
        )

        elements: List[Any] = []

        # 1. Header Banner
        elements.append(Paragraph("INSTITUTE OF TECHNOLOGY & MANAGEMENT", title_style))
        elements.append(
            Paragraph(
                "Office of the University Registrar • Division of Academic Records & Examination",
                subtitle_style,
            )
        )
        elements.append(
            Paragraph(
                "OFFICIAL ACADEMIC TRANSCRIPT OF RECORD",
                ParagraphStyle(
                    "DocType",
                    parent=title_style,
                    fontName="Helvetica-Bold",
                    fontSize=13,
                    leading=16,
                    textColor=colors.HexColor("#4338CA"),
                    spaceBefore=6,
                ),
            )
        )
        elements.append(Spacer(1, 14))

        # 2. Student Demographic Metadata
        meta_data = [
            [
                Paragraph("Student Full Name:", cell_bold),
                Paragraph(
                    f"{student.get('first_name', '')} {student.get('last_name', '')}", cell_normal
                ),
                Paragraph("Enrollment ID:", cell_bold),
                Paragraph(str(student.get("enrollment_no", "N/A")), cell_normal),
            ],
            [
                Paragraph("Academic Department:", cell_bold),
                Paragraph(str(student.get("department_name", "N/A")), cell_normal),
                Paragraph("Current Semester:", cell_bold),
                Paragraph(f"Semester {student.get('current_semester', 'N/A')}", cell_normal),
            ],
            [
                Paragraph("Admission Date:", cell_bold),
                Paragraph(str(student.get("admission_date", "N/A")), cell_normal),
                Paragraph("Academic Status:", cell_bold),
                Paragraph(str(student.get("status", "ENROLLED")), cell_bold),
            ],
        ]
        meta_table = Table(meta_data, colWidths=[110, 155, 100, 155])
        meta_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        elements.append(meta_table)
        elements.append(Spacer(1, 14))

        # 3. Academic Summary KPI Box
        total_creds = sum(e.get("credits", 0) for e in enrollments)
        eval_count = len(exam_results)
        tot_marks = sum(float(r.get("marks_obtained", 0)) for r in exam_results)
        tot_max = sum(float(r.get("max_marks", 0)) for r in exam_results)
        avg_pct = round((tot_marks / tot_max) * 100, 1) if tot_max > 0 else 0.0
        cgpa = round(avg_pct / 10.0, 2)
        att_pct = attendance.get("attendance_pct", 100.0)

        summary_data = [
            [
                Paragraph("Credits Earned", cell_bold),
                Paragraph("Evaluations Completed", cell_bold),
                Paragraph("Cumulative Marks %", cell_bold),
                Paragraph("Estimated CGPA (10.0)", cell_bold),
                Paragraph("Attendance Rate", cell_bold),
            ],
            [
                Paragraph(f"<b>{total_creds}</b>", cell_bold),
                Paragraph(f"<b>{eval_count}</b>", cell_bold),
                Paragraph(f"<b>{avg_pct}%</b>", cell_bold),
                Paragraph(f"<b>{cgpa} / 10.0</b>", cell_bold),
                Paragraph(f"<b>{att_pct}%</b>", cell_bold),
            ],
        ]
        sum_table = Table(summary_data, colWidths=[104, 104, 104, 104, 104])
        sum_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFF6FF")),
                    ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#FFFFFF")),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#93C5FD")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BFDBFE")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elements.append(sum_table)
        elements.append(Spacer(1, 14))

        # 4. Examination Results & Course Grades Table
        elements.append(
            Paragraph("Official Examination Records & Course Assessments", section_style)
        )
        exam_table_rows = [
            [
                Paragraph("Course Code", cell_header),
                Paragraph("Course Title", cell_header),
                Paragraph("Exam Title / Type", cell_header),
                Paragraph("Marks", cell_header),
                Paragraph("Max", cell_header),
                Paragraph("Percentage", cell_header),
                Paragraph("Grade", cell_header),
            ]
        ]

        if exam_results:
            for r in exam_results:
                m_ob = float(r.get("marks_obtained", 0))
                m_max = float(r.get("max_marks", 100))
                pct = round((m_ob / m_max) * 100, 1) if m_max > 0 else 0.0
                grade = str(r.get("letter_grade") or r.get("grade_letter") or "P")
                exam_table_rows.append(
                    [
                        Paragraph(str(r.get("course_code", "-")), cell_normal),
                        Paragraph(str(r.get("course_title", "-")), cell_normal),
                        Paragraph(
                            f"{r.get('exam_title', '')} ({r.get('exam_type', '')})", cell_normal
                        ),
                        Paragraph(f"{m_ob:.1f}", cell_normal),
                        Paragraph(f"{m_max:.1f}", cell_normal),
                        Paragraph(f"{pct}%", cell_normal),
                        Paragraph(f"<b>{grade}</b>", cell_bold),
                    ]
                )
        else:
            # If no exams yet, display enrolled courses
            for e in enrollments:
                exam_table_rows.append(
                    [
                        Paragraph(str(e.get("course_code", "-")), cell_normal),
                        Paragraph(str(e.get("course_title", "-")), cell_normal),
                        Paragraph("Regular Term Enrollment", cell_normal),
                        Paragraph("-", cell_normal),
                        Paragraph(f"{e.get('credits', 0)} cr", cell_normal),
                        Paragraph("In Progress", cell_normal),
                        Paragraph("ENROLLED", cell_bold),
                    ]
                )

        exam_table = Table(exam_table_rows, colWidths=[65, 145, 120, 45, 45, 55, 45])
        exam_style = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
            ("ALIGN", (3, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        # Alternating row colors
        for i in range(1, len(exam_table_rows)):
            bg = colors.HexColor("#F8FAFC") if i % 2 == 1 else colors.white
            exam_style.append(("BACKGROUND", (0, i), (-1, i), bg))

        exam_table.setStyle(TableStyle(exam_style))
        elements.append(exam_table)
        elements.append(Spacer(1, 18))

        # 5. Registrar Signature & Certification Seal
        sig_data = [
            [
                Paragraph(
                    "<b>Certified True & Correct Record</b><br/><font size=7 color='#64748B'>Issued under the official authority of the Academic Registrar.</font>",
                    cell_normal,
                ),
                Paragraph(
                    "<font size=7 color='#64748B'>OFFICIAL INSTITUTIONAL SEAL</font><br/><b>[ SEAL AFFIXED ]</b>",
                    ParagraphStyle("Seal", parent=cell_normal, alignment=1),
                ),
                Paragraph(
                    "<b>Office of Academic Registrar</b><br/><br/>___________________________<br/><font size=7 color='#64748B'>Authorized Signature & Stamp</font>",
                    ParagraphStyle("Sig", parent=cell_normal, alignment=2),
                ),
            ]
        ]
        sig_table = Table(sig_data, colWidths=[200, 120, 200])
        sig_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                    ("LINEBEFORE", (1, 0), (1, 0), 0.5, colors.HexColor("#CBD5E1")),
                    ("LINEAFTER", (1, 0), (1, 0), 0.5, colors.HexColor("#CBD5E1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        elements.append(sig_table)

        # Build PDF
        on_page = PDFService._create_watermark_callback(
            "OFFICIAL TRANSCRIPT", "Official Academic Transcript"
        )
        doc.build(elements, onFirstPage=on_page, onLaterPages=on_page)
        return buf.getvalue()

    @staticmethod
    def generate_fee_receipt_pdf(conn: sqlite3.Connection, invoice_id: int) -> bytes:
        """Compile official bursar payment receipt vector PDF."""
        invoice = FinanceService.get_invoice_by_id(conn, invoice_id)
        if not invoice:
            raise KeyError(f"Fee invoice #{invoice_id} not found")

        payments = invoice.get("payments", [])
        total_amt = float(invoice.get("total_amount", 0.0))
        paid_amt = float(invoice.get("paid_amount", 0.0))
        balance = float(invoice.get("balance_amount", 0.0))
        inv_status = str(invoice.get("status", "PENDING")).upper()

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=42,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "RecTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0F172A"),
            alignment=1,
        )
        subtitle_style = ParagraphStyle(
            "RecSubTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#475569"),
            alignment=1,
        )
        cell_bold = ParagraphStyle(
            "CellBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=10,
            textColor=colors.HexColor("#0F172A"),
        )
        cell_normal = ParagraphStyle(
            "CellNormal",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#334155"),
        )
        cell_header = ParagraphStyle(
            "CellHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=10,
            textColor=colors.white,
            alignment=1,
        )

        elements: List[Any] = []

        # 1. Header
        elements.append(Paragraph("INSTITUTE OF TECHNOLOGY & MANAGEMENT", title_style))
        elements.append(
            Paragraph(
                "Office of the Bursar • Division of Student Financial Affairs", subtitle_style
            )
        )
        elements.append(
            Paragraph(
                "OFFICIAL BURSAR FEE RECEIPT & STATEMENT",
                ParagraphStyle(
                    "DocType",
                    parent=title_style,
                    fontName="Helvetica-Bold",
                    fontSize=13,
                    leading=16,
                    textColor=colors.HexColor("#0D9488"),
                    spaceBefore=6,
                ),
            )
        )
        elements.append(Spacer(1, 14))

        # 2. Receipt Demographic Meta
        meta_data = [
            [
                Paragraph("Invoice Number:", cell_bold),
                Paragraph(str(invoice.get("invoice_no", "N/A")), cell_bold),
                Paragraph("Issue Date:", cell_bold),
                Paragraph(str(invoice.get("created_at", "N/A"))[:10], cell_normal),
            ],
            [
                Paragraph("Student Name:", cell_bold),
                Paragraph(str(invoice.get("student_name", "N/A")), cell_normal),
                Paragraph("Enrollment No:", cell_bold),
                Paragraph(str(invoice.get("enrollment_no", "N/A")), cell_normal),
            ],
            [
                Paragraph("Department:", cell_bold),
                Paragraph(str(invoice.get("department_name", "N/A")), cell_normal),
                Paragraph("Due Date:", cell_bold),
                Paragraph(str(invoice.get("due_date", "N/A")), cell_normal),
            ],
            [
                Paragraph("Academic Term:", cell_bold),
                Paragraph(str(invoice.get("term_name", "General")), cell_normal),
                Paragraph("Settlement Status:", cell_bold),
                Paragraph(f"<b>{inv_status}</b>", cell_bold),
            ],
        ]
        meta_table = Table(meta_data, colWidths=[110, 155, 100, 155])
        meta_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0FDFA")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#99F6E4")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCFBF1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        elements.append(meta_table)
        elements.append(Spacer(1, 14))

        # 3. Itemized Invoice Charges Table
        charge_rows = [
            [
                Paragraph("Description / Item", cell_header),
                Paragraph("Term / Scope", cell_header),
                Paragraph("Due Date", cell_header),
                Paragraph("Total Billed", cell_header),
                Paragraph("Paid to Date", cell_header),
                Paragraph("Balance Outstanding", cell_header),
            ],
            [
                Paragraph(str(invoice.get("title", "Tuition Fee")), cell_normal),
                Paragraph(str(invoice.get("term_name", "-")), cell_normal),
                Paragraph(str(invoice.get("due_date", "-")), cell_normal),
                Paragraph(f"${total_amt:,.2f}", cell_normal),
                Paragraph(f"${paid_amt:,.2f}", cell_normal),
                Paragraph(f"<b>${balance:,.2f}</b>", cell_bold),
            ],
        ]
        charge_table = Table(charge_rows, colWidths=[140, 80, 75, 75, 75, 75])
        charge_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F766E")),
                    ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        elements.append(charge_table)
        elements.append(Spacer(1, 14))

        # 4. Recorded Payment Transactions
        elements.append(
            Paragraph(
                "Recorded Transaction History & Payment Receipts",
                ParagraphStyle(
                    "SecH",
                    parent=styles["Normal"],
                    fontName="Helvetica-Bold",
                    fontSize=11,
                    leading=14,
                    textColor=colors.HexColor("#0F766E"),
                    spaceAfter=4,
                ),
            )
        )
        pay_rows = [
            [
                Paragraph("Receipt #", cell_header),
                Paragraph("Payment Date", cell_header),
                Paragraph("Payment Mode", cell_header),
                Paragraph("Transaction Ref", cell_header),
                Paragraph("Amount Received", cell_header),
            ]
        ]
        if payments:
            for p in payments:
                amt = float(p.get("amount", 0.0))
                pay_rows.append(
                    [
                        Paragraph(str(p.get("receipt_no", "-")), cell_normal),
                        Paragraph(str(p.get("payment_date", "-")), cell_normal),
                        Paragraph(str(p.get("payment_method", "-")), cell_normal),
                        Paragraph(str(p.get("transaction_ref") or "DIRECT"), cell_normal),
                        Paragraph(f"<b>${amt:,.2f}</b>", cell_bold),
                    ]
                )
        else:
            pay_rows.append(
                [
                    Paragraph("No payment transactions recorded yet.", cell_normal),
                    Paragraph("-", cell_normal),
                    Paragraph("-", cell_normal),
                    Paragraph("-", cell_normal),
                    Paragraph("$0.00", cell_normal),
                ]
            )

        pay_table = Table(pay_rows, colWidths=[110, 90, 100, 120, 100])
        pay_style = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
            ("ALIGN", (4, 0), (4, -1), "RIGHT"),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        for i in range(1, len(pay_rows)):
            bg = colors.HexColor("#F8FAFC") if i % 2 == 1 else colors.white
            pay_style.append(("BACKGROUND", (0, i), (-1, i), bg))
        pay_table.setStyle(TableStyle(pay_style))
        elements.append(pay_table)
        elements.append(Spacer(1, 20))

        # 5. Settlement Stamp & Signatures
        stamp_text = (
            "PAID IN FULL"
            if balance <= 0
            else ("PARTIAL PAYMENT" if paid_amt > 0 else "PAYMENT PENDING")
        )
        sig_data = [
            [
                Paragraph(
                    f"<b>Bursar Certification:</b><br/><font size=7 color='#64748B'>This receipt acknowledges receipt of institutional fees.<br/>Status: <b>{stamp_text}</b></font>",
                    cell_normal,
                ),
                Paragraph(
                    f"<font size=8 color='#0F766E'><b>[ {stamp_text} ]</b></font><br/><font size=7 color='#64748B'>TRANSACTION VERIFIED</font>",
                    ParagraphStyle("Stamp", parent=cell_normal, alignment=1),
                ),
                Paragraph(
                    "<b>Accounts & Bursar Officer</b><br/><br/>___________________________<br/><font size=7 color='#64748B'>Financial Audit Clearance</font>",
                    ParagraphStyle("Sig", parent=cell_normal, alignment=2),
                ),
            ]
        ]
        sig_table = Table(sig_data, colWidths=[200, 120, 200])
        sig_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                    ("LINEBEFORE", (1, 0), (1, 0), 0.5, colors.HexColor("#CBD5E1")),
                    ("LINEAFTER", (1, 0), (1, 0), 0.5, colors.HexColor("#CBD5E1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        elements.append(sig_table)

        on_page = PDFService._create_watermark_callback(stamp_text, "Official Bursar Fee Receipt")
        doc.build(elements, onFirstPage=on_page, onLaterPages=on_page)
        return buf.getvalue()

    @staticmethod
    def generate_medical_certificate_pdf(conn: sqlite3.Connection, certificate_id: int) -> bytes:
        """Compile official clinical medical clearance certificate vector PDF."""
        cert = HealthService.get_medical_certificate(conn, certificate_id)

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=40,
            rightMargin=40,
            topMargin=40,
            bottomMargin=42,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "MedTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0F172A"),
            alignment=1,
        )
        subtitle_style = ParagraphStyle(
            "MedSubTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#475569"),
            alignment=1,
        )
        cell_bold = ParagraphStyle(
            "CellBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#0F172A"),
        )
        cell_normal = ParagraphStyle(
            "CellNormal",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#334155"),
        )

        elements: List[Any] = []

        # 1. Header
        elements.append(Paragraph("INSTITUTE OF TECHNOLOGY & MANAGEMENT", title_style))
        elements.append(
            Paragraph(
                "Health Center & Student Infirmary • Clinical Services Division", subtitle_style
            )
        )
        elements.append(
            Paragraph(
                "OFFICIAL MEDICAL CLEARANCE CERTIFICATE",
                ParagraphStyle(
                    "DocType",
                    parent=title_style,
                    fontName="Helvetica-Bold",
                    fontSize=13,
                    leading=16,
                    textColor=colors.HexColor("#DC2626"),
                    spaceBefore=6,
                ),
            )
        )
        elements.append(Spacer(1, 16))

        # 2. Certificate Meta
        cert_data = [
            [
                Paragraph("Certificate Number:", cell_bold),
                Paragraph(str(cert.get("certificate_number", "N/A")), cell_bold),
                Paragraph("Date of Issue:", cell_bold),
                Paragraph(str(cert.get("created_at", "N/A"))[:10], cell_normal),
            ],
            [
                Paragraph("Patient Name:", cell_bold),
                Paragraph(str(cert.get("patient_name", "N/A")), cell_normal),
                Paragraph("Patient ID / Roll:", cell_bold),
                Paragraph(str(cert.get("patient_identifier", "N/A")), cell_normal),
            ],
            [
                Paragraph("Department:", cell_bold),
                Paragraph(str(cert.get("department_name", "General")), cell_normal),
                Paragraph("Attending Physician:", cell_bold),
                Paragraph(str(cert.get("doctor_name", "Staff Medical Officer")), cell_normal),
            ],
        ]
        cert_table = Table(cert_data, colWidths=[110, 150, 105, 150])
        cert_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF2F2")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#FECACA")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#FEE2E2")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        elements.append(cert_table)
        elements.append(Spacer(1, 16))

        # 3. Clinical Recommendation & Certification
        start_d = cert.get("rest_from_date") or cert.get("rest_start_date", "-")
        end_d = cert.get("rest_to_date") or cert.get("rest_end_date", "-")
        fit_d = cert.get("fit_to_resume_date", "-")
        diag = cert.get("diagnosis_summary") or cert.get("diagnosis", "Clinical Consultation")
        notes = (
            cert.get("doctor_remarks")
            or cert.get("clinical_remarks")
            or cert.get("remarks")
            or "Advised appropriate rest and recovery."
        )

        body_text = (
            "<b>To Whom It May Concern:</b><br/><br/>"
            f"This is to certify that <b>{cert.get('patient_name')}</b> ({cert.get('patient_type', 'STUDENT')} - "
            f"ID: <code>{cert.get('patient_identifier')}</code>) was examined at the Institute Health Center on "
            f"<b>{cert.get('created_at', '')[:10]}</b>.<br/><br/>"
            f"<b>Diagnosis / Clinical Assessment:</b> {diag}<br/><br/>"
            f"In the opinion of the attending medical officer, the patient requires <b>medical rest</b> "
            f"from <b>{start_d}</b> to <b>{end_d}</b>, and is assessed fit to resume institutional duties on <b>{fit_d}</b>.<br/><br/>"
            "<b>Clinical Remarks & Restrictions:</b><br/>"
            f"{notes}"
        )
        elements.append(
            Paragraph(
                body_text,
                ParagraphStyle(
                    "Body",
                    parent=styles["Normal"],
                    fontSize=9.5,
                    leading=14,
                    textColor=colors.HexColor("#1E293B"),
                ),
            )
        )
        elements.append(Spacer(1, 24))

        # 4. Signatures
        sig_data = [
            [
                Paragraph(
                    "<b>Infirmary Verification</b><br/><font size=7 color='#64748B'>Registered Health Record</font>",
                    cell_normal,
                ),
                Paragraph(
                    "<font size=7 color='#DC2626'><b>[ MEDICAL SEAL ]</b></font>",
                    ParagraphStyle("Seal", parent=cell_normal, alignment=1),
                ),
                Paragraph(
                    f"<b>Dr. {cert.get('doctor_name', 'Medical Officer')}</b><br/><br/>___________________________<br/><font size=7 color='#64748B'>Attending Physician License</font>",
                    ParagraphStyle("Sig", parent=cell_normal, alignment=2),
                ),
            ]
        ]
        sig_table = Table(sig_data, colWidths=[180, 130, 205])
        sig_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        elements.append(sig_table)

        on_page = PDFService._create_watermark_callback(
            "MEDICAL CLEARANCE", "Clinical Medical Certificate"
        )
        doc.build(elements, onFirstPage=on_page, onLaterPages=on_page)
        return buf.getvalue()
