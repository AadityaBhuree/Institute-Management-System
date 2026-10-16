"""Campus Health, Student Clinic & Infirmary Hub Service."""

import sqlite3
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from src.database.connection import transaction
from src.models.health import (
    DispensaryMedicineCreate,
    HealthProfileCreate,
    MedicalCertificateCreate,
    MedicalEncounterCreate,
)


class HealthService:
    @staticmethod
    def _generate_encounter_code(conn: sqlite3.Connection, visit_date: str) -> str:
        """Generate unique medical encounter code: ENC-YYYY-XXXX."""
        try:
            year = datetime.strptime(visit_date, "%Y-%m-%d").year
        except ValueError:
            year = datetime.now().year

        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM medical_encounters WHERE encounter_code LIKE ?;",
            (f"ENC-{year}-%",),
        )
        count = cursor.fetchone()["cnt"] + 1
        cursor.close()

        code = f"ENC-{year}-{count:04d}"
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM medical_encounters WHERE encounter_code = ?;", (code,))
        while cursor.fetchone():
            count += 1
            code = f"ENC-{year}-{count:04d}"
            cursor.execute("SELECT id FROM medical_encounters WHERE encounter_code = ?;", (code,))
        cursor.close()
        return code

    @staticmethod
    def _generate_certificate_number(conn: sqlite3.Connection, rest_date: str) -> str:
        """Generate unique medical certificate number: MED-YYYY-XXXX."""
        try:
            year = datetime.strptime(rest_date, "%Y-%m-%d").year
        except ValueError:
            year = datetime.now().year

        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM medical_certificates WHERE certificate_number LIKE ?;",
            (f"MED-{year}-%",),
        )
        count = cursor.fetchone()["cnt"] + 1
        cursor.close()

        num = f"MED-{year}-{count:04d}"
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM medical_certificates WHERE certificate_number = ?;", (num,))
        while cursor.fetchone():
            count += 1
            num = f"MED-{year}-{count:04d}"
            cursor.execute("SELECT id FROM medical_certificates WHERE certificate_number = ?;", (num,))
        cursor.close()
        return num

    @staticmethod
    def _generate_medicine_code(conn: sqlite3.Connection) -> str:
        """Generate unique dispensary medicine code: MED-STK-XXXX."""
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS cnt FROM dispensary_medicines;")
        count = cursor.fetchone()["cnt"] + 1
        cursor.close()

        code = f"MED-STK-{count:04d}"
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM dispensary_medicines WHERE item_code = ?;", (code,))
        while cursor.fetchone():
            count += 1
            code = f"MED-STK-{count:04d}"
            cursor.execute("SELECT id FROM dispensary_medicines WHERE item_code = ?;", (code,))
        cursor.close()
        return code

    # =========================================================================
    # HEALTH PROFILES
    # =========================================================================

    @staticmethod
    def create_or_update_profile(
        conn: sqlite3.Connection, data: HealthProfileCreate
    ) -> Dict[str, Any]:
        """Create or update a student/faculty health profile."""
        cursor = conn.cursor()
        if data.person_type == "STUDENT":
            cursor.execute("SELECT id, first_name, last_name FROM students WHERE id = ?;", (data.student_id,))
            student = cursor.fetchone()
            if not student:
                cursor.close()
                raise ValueError(f"Student with id {data.student_id} does not exist")
        else:
            cursor.execute("SELECT id, first_name, last_name FROM faculty WHERE id = ?;", (data.faculty_id,))
            faculty = cursor.fetchone()
            if not faculty:
                cursor.close()
                raise ValueError(f"Faculty with id {data.faculty_id} does not exist")

        # Check existing
        if data.person_type == "STUDENT":
            cursor.execute("SELECT id FROM health_profiles WHERE student_id = ?;", (data.student_id,))
        else:
            cursor.execute("SELECT id FROM health_profiles WHERE faculty_id = ?;", (data.faculty_id,))
        existing = cursor.fetchone()
        cursor.close()

        with transaction(conn) as tx:
            if existing:
                tx.execute(
                    """
                    UPDATE health_profiles
                    SET blood_group = ?, allergies = ?, chronic_conditions = ?,
                        emergency_contact_name = ?, emergency_contact_phone = ?,
                        emergency_contact_relation = ?, insurance_provider = ?,
                        insurance_policy_number = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?;
                    """,
                    (
                        data.blood_group,
                        data.allergies,
                        data.chronic_conditions,
                        data.emergency_contact_name,
                        data.emergency_contact_phone,
                        data.emergency_contact_relation,
                        data.insurance_provider,
                        data.insurance_policy_number,
                        existing["id"],
                    ),
                )
                profile_id = existing["id"]
            else:
                tx.execute(
                    """
                    INSERT INTO health_profiles (
                        person_type, student_id, faculty_id, blood_group,
                        allergies, chronic_conditions, emergency_contact_name,
                        emergency_contact_phone, emergency_contact_relation,
                        insurance_provider, insurance_policy_number
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        data.person_type,
                        data.student_id,
                        data.faculty_id,
                        data.blood_group,
                        data.allergies,
                        data.chronic_conditions,
                        data.emergency_contact_name,
                        data.emergency_contact_phone,
                        data.emergency_contact_relation,
                        data.insurance_provider,
                        data.insurance_policy_number,
                    ),
                )
                profile_id = tx.lastrowid

        return HealthService.get_profile_by_id(conn, profile_id)

    @staticmethod
    def get_profile_by_id(conn: sqlite3.Connection, profile_id: int) -> Dict[str, Any]:
        """Retrieve single health profile by ID with demographic join."""
        query = """
            SELECT hp.*,
                   CASE
                       WHEN hp.person_type = 'STUDENT' THEN s.first_name || ' ' || s.last_name
                       ELSE f.first_name || ' ' || f.last_name
                   END AS person_name,
                   CASE
                       WHEN hp.person_type = 'STUDENT' THEN s.enrollment_no
                       ELSE f.faculty_id
                   END AS enrollment_or_faculty_id,
                   d.name AS department_name,
                   d.code AS department_code
            FROM health_profiles hp
            LEFT JOIN students s ON hp.student_id = s.id
            LEFT JOIN faculty f ON hp.faculty_id = f.id
            LEFT JOIN departments d ON (s.department_id = d.id OR f.department_id = d.id)
            WHERE hp.id = ?;
        """
        cursor = conn.cursor()
        cursor.execute(query, (profile_id,))
        row = cursor.fetchone()
        cursor.close()
        if not row:
            raise KeyError(f"Health profile with id {profile_id} not found")
        return dict(row)

    @staticmethod
    def get_profile_by_person(
        conn: sqlite3.Connection, person_type: str, person_id: int
    ) -> Optional[Dict[str, Any]]:
        """Retrieve health profile by student_id or faculty_id."""
        query = """
            SELECT hp.*,
                   CASE
                       WHEN hp.person_type = 'STUDENT' THEN s.first_name || ' ' || s.last_name
                       ELSE f.first_name || ' ' || f.last_name
                   END AS person_name,
                   CASE
                       WHEN hp.person_type = 'STUDENT' THEN s.enrollment_no
                       ELSE f.faculty_id
                   END AS enrollment_or_faculty_id,
                   d.name AS department_name,
                   d.code AS department_code
            FROM health_profiles hp
            LEFT JOIN students s ON hp.student_id = s.id
            LEFT JOIN faculty f ON hp.faculty_id = f.id
            LEFT JOIN departments d ON (s.department_id = d.id OR f.department_id = d.id)
            WHERE hp.person_type = ? AND (
                (hp.person_type = 'STUDENT' AND hp.student_id = ?) OR
                (hp.person_type = 'FACULTY' AND hp.faculty_id = ?)
            );
        """
        cursor = conn.cursor()
        cursor.execute(query, (person_type, person_id, person_id))
        row = cursor.fetchone()
        cursor.close()
        return dict(row) if row else None

    @staticmethod
    def list_profiles(
        conn: sqlite3.Connection,
        person_type: Optional[str] = None,
        blood_group: Optional[str] = None,
        has_allergies: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List health profiles with demographic and filter parameters."""
        query = """
            SELECT hp.*,
                   CASE
                       WHEN hp.person_type = 'STUDENT' THEN s.first_name || ' ' || s.last_name
                       ELSE f.first_name || ' ' || f.last_name
                   END AS person_name,
                   CASE
                       WHEN hp.person_type = 'STUDENT' THEN s.enrollment_no
                       ELSE f.faculty_id
                   END AS enrollment_or_faculty_id,
                   d.name AS department_name,
                   d.code AS department_code
            FROM health_profiles hp
            LEFT JOIN students s ON hp.student_id = s.id
            LEFT JOIN faculty f ON hp.faculty_id = f.id
            LEFT JOIN departments d ON (s.department_id = d.id OR f.department_id = d.id)
            WHERE 1=1
        """
        params: List[Any] = []
        if person_type:
            query += " AND hp.person_type = ?"
            params.append(person_type)
        if blood_group:
            query += " AND hp.blood_group = ?"
            params.append(blood_group)
        if has_allergies is True:
            query += " AND hp.allergies != 'None' AND hp.allergies != ''"
        elif has_allergies is False:
            query += " AND (hp.allergies = 'None' OR hp.allergies = '')"

        if search:
            query += """
                AND (
                    s.first_name LIKE ? OR s.last_name LIKE ? OR s.enrollment_no LIKE ?
                    OR f.first_name LIKE ? OR f.last_name LIKE ? OR f.faculty_id LIKE ?
                    OR hp.emergency_contact_name LIKE ? OR hp.allergies LIKE ?
                    OR hp.chronic_conditions LIKE ?
                )
            """
            wildcard = f"%{search}%"
            params.extend([wildcard] * 9)

        query += " ORDER BY hp.updated_at DESC;"
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(r) for r in rows]

    # =========================================================================
    # DISPENSARY MEDICINE INVENTORY
    # =========================================================================

    @staticmethod
    def create_dispensary_medicine(
        conn: sqlite3.Connection, data: DispensaryMedicineCreate
    ) -> Dict[str, Any]:
        """Register a new medicine batch in the dispensary stock."""
        item_code = data.item_code or HealthService._generate_medicine_code(conn)

        cursor = conn.cursor()
        cursor.execute("SELECT id FROM dispensary_medicines WHERE item_code = ?;", (item_code,))
        if cursor.fetchone():
            cursor.close()
            raise ValueError(f"Medicine with item code '{item_code}' already exists")
        cursor.close()

        with transaction(conn) as tx:
            tx.execute(
                """
                INSERT INTO dispensary_medicines (
                    item_code, name, category, form, stock_quantity,
                    unit, reorder_level, expiry_date, batch_number
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    item_code,
                    data.name,
                    data.category,
                    data.form,
                    data.stock_quantity,
                    data.unit,
                    data.reorder_level,
                    data.expiry_date,
                    data.batch_number,
                ),
            )
            med_id = tx.lastrowid

        return HealthService.get_dispensary_medicine(conn, med_id)

    @staticmethod
    def get_dispensary_medicine(conn: sqlite3.Connection, medicine_id: int) -> Dict[str, Any]:
        """Fetch single medicine details with low stock indicator."""
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT dm.*,
                   CASE WHEN dm.stock_quantity <= dm.reorder_level THEN 1 ELSE 0 END AS is_low_stock
            FROM dispensary_medicines dm
            WHERE dm.id = ?;
            """,
            (medicine_id,),
        )
        row = cursor.fetchone()
        cursor.close()
        if not row:
            raise KeyError(f"Dispensary medicine with id {medicine_id} not found")
        item = dict(row)
        item["is_low_stock"] = bool(item["is_low_stock"])
        return item

    @staticmethod
    def update_dispensary_stock(
        conn: sqlite3.Connection, medicine_id: int, quantity_change: int, reason: str = "Restock"
    ) -> Dict[str, Any]:
        """Update medicine inventory stock quantity."""
        med = HealthService.get_dispensary_medicine(conn, medicine_id)
        new_quantity = med["stock_quantity"] + quantity_change
        if new_quantity < 0:
            raise ValueError(
                f"Cannot reduce stock by {abs(quantity_change)}. Current stock is only {med['stock_quantity']}."
            )

        with transaction(conn) as tx:
            tx.execute(
                "UPDATE dispensary_medicines SET stock_quantity = ? WHERE id = ?;",
                (new_quantity, medicine_id),
            )

        return HealthService.get_dispensary_medicine(conn, medicine_id)

    @staticmethod
    def list_dispensary_medicines(
        conn: sqlite3.Connection,
        category: Optional[str] = None,
        low_stock_only: bool = False,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List dispensary medicines with stock alerts and filtering."""
        query = """
            SELECT dm.*,
                   CASE WHEN dm.stock_quantity <= dm.reorder_level THEN 1 ELSE 0 END AS is_low_stock
            FROM dispensary_medicines dm
            WHERE 1=1
        """
        params: List[Any] = []
        if category:
            query += " AND dm.category = ?"
            params.append(category)
        if low_stock_only:
            query += " AND dm.stock_quantity <= dm.reorder_level"

        if search:
            query += " AND (dm.name LIKE ? OR dm.item_code LIKE ? OR dm.batch_number LIKE ?)"
            wildcard = f"%{search}%"
            params.extend([wildcard, wildcard, wildcard])

        query += " ORDER BY is_low_stock DESC, dm.name ASC;"
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()

        result = []
        for r in rows:
            d = dict(r)
            d["is_low_stock"] = bool(d["is_low_stock"])
            result.append(d)
        return result

    # =========================================================================
    # MEDICAL ENCOUNTERS & CONSULTATIONS
    # =========================================================================

    @staticmethod
    def create_encounter(
        conn: sqlite3.Connection, data: MedicalEncounterCreate
    ) -> Dict[str, Any]:
        """Log a new clinical consultation with vital signs and prescription dispensation."""
        cursor = conn.cursor()
        if data.patient_type == "STUDENT":
            cursor.execute("SELECT id FROM students WHERE id = ?;", (data.student_id,))
            if not cursor.fetchone():
                cursor.close()
                raise ValueError(f"Student with id {data.student_id} does not exist")
        else:
            cursor.execute("SELECT id FROM faculty WHERE id = ?;", (data.faculty_id,))
            if not cursor.fetchone():
                cursor.close()
                raise ValueError(f"Faculty with id {data.faculty_id} does not exist")

        # Validate medicine stocks before applying transaction
        for p in data.prescriptions:
            if p.medicine_id:
                cursor.execute(
                    "SELECT stock_quantity, name FROM dispensary_medicines WHERE id = ?;",
                    (p.medicine_id,),
                )
                med_row = cursor.fetchone()
                if not med_row:
                    cursor.close()
                    raise ValueError(f"Medicine id {p.medicine_id} not found in dispensary")
                if med_row["stock_quantity"] < p.quantity_dispensed:
                    cursor.close()
                    raise ValueError(
                        f"Insufficient stock for {med_row['name']}. Available: {med_row['stock_quantity']}, Requested: {p.quantity_dispensed}"
                    )
        cursor.close()

        encounter_code = HealthService._generate_encounter_code(conn, data.visit_date)

        with transaction(conn) as tx:
            tx.execute(
                """
                INSERT INTO medical_encounters (
                    encounter_code, patient_type, student_id, faculty_id,
                    visit_date, doctor_name, chief_complaint, symptoms,
                    diagnosis, blood_pressure, pulse_bpm, temperature_f,
                    triage_severity, treatment_given, follow_up_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    encounter_code,
                    data.patient_type,
                    data.student_id,
                    data.faculty_id,
                    data.visit_date,
                    data.doctor_name,
                    data.chief_complaint,
                    data.symptoms,
                    data.diagnosis,
                    data.blood_pressure,
                    data.pulse_bpm,
                    data.temperature_f,
                    data.triage_severity,
                    data.treatment_given,
                    data.follow_up_date,
                ),
            )
            encounter_id = tx.lastrowid

            # Save prescriptions and decrement dispensary inventory
            for p in data.prescriptions:
                tx.execute(
                    """
                    INSERT INTO encounter_prescriptions (
                        encounter_id, medicine_id, medicine_name, dosage,
                        frequency, duration_days, quantity_dispensed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        encounter_id,
                        p.medicine_id,
                        p.medicine_name,
                        p.dosage,
                        p.frequency,
                        p.duration_days,
                        p.quantity_dispensed,
                    ),
                )
                if p.medicine_id and p.quantity_dispensed > 0:
                    tx.execute(
                        """
                        UPDATE dispensary_medicines
                        SET stock_quantity = stock_quantity - ?
                        WHERE id = ?;
                        """,
                        (p.quantity_dispensed, p.medicine_id),
                    )

        return HealthService.get_encounter(conn, encounter_id)

    @staticmethod
    def get_encounter(conn: sqlite3.Connection, encounter_id: int) -> Dict[str, Any]:
        """Fetch medical encounter details with joined patient metadata and prescriptions."""
        query = """
            SELECT me.*,
                   CASE
                       WHEN me.patient_type = 'STUDENT' THEN s.first_name || ' ' || s.last_name
                       ELSE f.first_name || ' ' || f.last_name
                   END AS patient_name,
                   CASE
                       WHEN me.patient_type = 'STUDENT' THEN s.enrollment_no
                       ELSE f.faculty_id
                   END AS patient_identifier,
                   d.name AS department_name,
                   hp.blood_group,
                   hp.allergies,
                   CASE WHEN mc.id IS NOT NULL THEN 1 ELSE 0 END AS has_medical_certificate
            FROM medical_encounters me
            LEFT JOIN students s ON me.student_id = s.id
            LEFT JOIN faculty f ON me.faculty_id = f.id
            LEFT JOIN departments d ON (s.department_id = d.id OR f.department_id = d.id)
            LEFT JOIN health_profiles hp ON (
                (me.patient_type = 'STUDENT' AND me.student_id = hp.student_id) OR
                (me.patient_type = 'FACULTY' AND me.faculty_id = hp.faculty_id)
            )
            LEFT JOIN medical_certificates mc ON (me.id = mc.encounter_id AND mc.status = 'ISSUED')
            WHERE me.id = ?;
        """
        cursor = conn.cursor()
        cursor.execute(query, (encounter_id,))
        row = cursor.fetchone()
        if not row:
            cursor.close()
            raise KeyError(f"Medical encounter with id {encounter_id} not found")

        encounter = dict(row)
        encounter["has_medical_certificate"] = bool(encounter["has_medical_certificate"])

        # Fetch prescriptions
        cursor.execute(
            """
            SELECT ep.*, dm.item_code AS medicine_item_code
            FROM encounter_prescriptions ep
            LEFT JOIN dispensary_medicines dm ON ep.medicine_id = dm.id
            WHERE ep.encounter_id = ?
            ORDER BY ep.id ASC;
            """,
            (encounter_id,),
        )
        p_rows = cursor.fetchall()
        cursor.close()
        encounter["prescriptions"] = [dict(pr) for pr in p_rows]
        return encounter

    @staticmethod
    def list_encounters(
        conn: sqlite3.Connection,
        patient_type: Optional[str] = None,
        triage_severity: Optional[str] = None,
        visit_date: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List medical encounters with filtering and search."""
        query = """
            SELECT me.*,
                   CASE
                       WHEN me.patient_type = 'STUDENT' THEN s.first_name || ' ' || s.last_name
                       ELSE f.first_name || ' ' || f.last_name
                   END AS patient_name,
                   CASE
                       WHEN me.patient_type = 'STUDENT' THEN s.enrollment_no
                       ELSE f.faculty_id
                   END AS patient_identifier,
                   d.name AS department_name,
                   (SELECT COUNT(*) FROM encounter_prescriptions ep WHERE ep.encounter_id = me.id) AS prescription_count,
                   (SELECT COUNT(*) FROM medical_certificates mc WHERE mc.encounter_id = me.id AND mc.status = 'ISSUED') AS has_certificate
            FROM medical_encounters me
            LEFT JOIN students s ON me.student_id = s.id
            LEFT JOIN faculty f ON me.faculty_id = f.id
            LEFT JOIN departments d ON (s.department_id = d.id OR f.department_id = d.id)
            WHERE 1=1
        """
        params: List[Any] = []
        if patient_type:
            query += " AND me.patient_type = ?"
            params.append(patient_type)
        if triage_severity:
            query += " AND me.triage_severity = ?"
            params.append(triage_severity)
        if visit_date:
            query += " AND me.visit_date = ?"
            params.append(visit_date)

        if search:
            query += """
                AND (
                    me.encounter_code LIKE ? OR me.doctor_name LIKE ? OR me.chief_complaint LIKE ?
                    OR me.diagnosis LIKE ? OR s.first_name LIKE ? OR s.last_name LIKE ?
                    OR s.enrollment_no LIKE ? OR f.first_name LIKE ? OR f.last_name LIKE ?
                    OR f.faculty_id LIKE ?
                )
            """
            wildcard = f"%{search}%"
            params.extend([wildcard] * 10)

        query += " ORDER BY me.visit_date DESC, me.id DESC LIMIT ?;"
        params.append(limit)

        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()

        result = []
        for r in rows:
            d = dict(r)
            d["has_medical_certificate"] = bool(d["has_certificate"])
            result.append(d)
        return result

    # =========================================================================
    # MEDICAL CERTIFICATES & SICK LEAVE ENDORSEMENTS
    # =========================================================================

    @staticmethod
    def issue_medical_certificate(
        conn: sqlite3.Connection, data: MedicalCertificateCreate
    ) -> Dict[str, Any]:
        """Issue an official verifiable medical sick leave certificate for an encounter."""
        encounter = HealthService.get_encounter(conn, data.encounter_id)

        # Check existing active certificate for encounter
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM medical_certificates WHERE encounter_id = ? AND status = 'ISSUED';",
            (data.encounter_id,),
        )
        if cursor.fetchone():
            cursor.close()
            raise ValueError(f"An active medical certificate already exists for encounter {encounter['encounter_code']}")
        cursor.close()

        cert_number = HealthService._generate_certificate_number(conn, data.rest_from_date)

        with transaction(conn) as tx:
            tx.execute(
                """
                INSERT INTO medical_certificates (
                    certificate_number, encounter_id, patient_type,
                    student_id, faculty_id, rest_from_date, rest_to_date,
                    fit_to_resume_date, diagnosis_summary, doctor_remarks, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ISSUED');
                """,
                (
                    cert_number,
                    data.encounter_id,
                    encounter["patient_type"],
                    encounter["student_id"],
                    encounter["faculty_id"],
                    data.rest_from_date,
                    data.rest_to_date,
                    data.fit_to_resume_date,
                    data.diagnosis_summary,
                    data.doctor_remarks,
                ),
            )
            cert_id = tx.lastrowid

        return HealthService.get_medical_certificate(conn, cert_id)

    @staticmethod
    def get_medical_certificate(conn: sqlite3.Connection, certificate_id: int) -> Dict[str, Any]:
        """Fetch medical certificate details with patient demographic and encounter data."""
        query = """
            SELECT mc.*,
                   me.encounter_code,
                   me.doctor_name,
                   CASE
                       WHEN mc.patient_type = 'STUDENT' THEN s.first_name || ' ' || s.last_name
                       ELSE f.first_name || ' ' || f.last_name
                   END AS patient_name,
                   CASE
                       WHEN mc.patient_type = 'STUDENT' THEN s.enrollment_no
                       ELSE f.faculty_id
                   END AS patient_identifier,
                   d.name AS department_name
            FROM medical_certificates mc
            JOIN medical_encounters me ON mc.encounter_id = me.id
            LEFT JOIN students s ON mc.student_id = s.id
            LEFT JOIN faculty f ON mc.faculty_id = f.id
            LEFT JOIN departments d ON (s.department_id = d.id OR f.department_id = d.id)
            WHERE mc.id = ?;
        """
        cursor = conn.cursor()
        cursor.execute(query, (certificate_id,))
        row = cursor.fetchone()
        cursor.close()
        if not row:
            raise KeyError(f"Medical certificate with id {certificate_id} not found")
        return dict(row)

    @staticmethod
    def revoke_medical_certificate(conn: sqlite3.Connection, certificate_id: int) -> Dict[str, Any]:
        """Revoke a medical certificate."""
        HealthService.get_medical_certificate(conn, certificate_id)
        with transaction(conn) as tx:
            tx.execute("UPDATE medical_certificates SET status = 'REVOKED' WHERE id = ?;", (certificate_id,))
        return HealthService.get_medical_certificate(conn, certificate_id)

    @staticmethod
    def list_medical_certificates(
        conn: sqlite3.Connection,
        status: Optional[str] = None,
        patient_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List medical certificates with search and status filters."""
        query = """
            SELECT mc.*,
                   me.encounter_code,
                   me.doctor_name,
                   CASE
                       WHEN mc.patient_type = 'STUDENT' THEN s.first_name || ' ' || s.last_name
                       ELSE f.first_name || ' ' || f.last_name
                   END AS patient_name,
                   CASE
                       WHEN mc.patient_type = 'STUDENT' THEN s.enrollment_no
                       ELSE f.faculty_id
                   END AS patient_identifier,
                   d.name AS department_name
            FROM medical_certificates mc
            JOIN medical_encounters me ON mc.encounter_id = me.id
            LEFT JOIN students s ON mc.student_id = s.id
            LEFT JOIN faculty f ON mc.faculty_id = f.id
            LEFT JOIN departments d ON (s.department_id = d.id OR f.department_id = d.id)
            WHERE 1=1
        """
        params: List[Any] = []
        if status:
            query += " AND mc.status = ?"
            params.append(status)
        if patient_type:
            query += " AND mc.patient_type = ?"
            params.append(patient_type)

        if search:
            query += """
                AND (
                    mc.certificate_number LIKE ? OR me.encounter_code LIKE ?
                    OR me.doctor_name LIKE ? OR s.first_name LIKE ? OR s.last_name LIKE ?
                    OR s.enrollment_no LIKE ? OR f.first_name LIKE ? OR f.last_name LIKE ?
                    OR f.faculty_id LIKE ? OR mc.diagnosis_summary LIKE ?
                )
            """
            wildcard = f"%{search}%"
            params.extend([wildcard] * 10)

        query += " ORDER BY mc.created_at DESC;"
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(r) for r in rows]

    # =========================================================================
    # TELEMETRY & STATS SUMMARY
    # =========================================================================

    @staticmethod
    def get_health_stats(conn: sqlite3.Connection) -> Dict[str, Any]:
        """Compute institutional clinic and infirmary health telemetry KPI metrics."""
        cursor = conn.cursor()

        # Total encounters
        cursor.execute("SELECT COUNT(*) AS cnt FROM medical_encounters;")
        total_encounters = cursor.fetchone()["cnt"]

        # Student visits
        cursor.execute("SELECT COUNT(*) AS cnt FROM medical_encounters WHERE patient_type = 'STUDENT';")
        student_visits = cursor.fetchone()["cnt"]

        # Faculty visits
        cursor.execute("SELECT COUNT(*) AS cnt FROM medical_encounters WHERE patient_type = 'FACULTY';")
        faculty_visits = cursor.fetchone()["cnt"]

        # Active sick leaves
        today_str = date.today().isoformat()
        cursor.execute(
            """
            SELECT COUNT(*) AS cnt FROM medical_certificates
            WHERE status = 'ISSUED' AND fit_to_resume_date >= ?;
            """,
            (today_str,),
        )
        active_sick_leaves = cursor.fetchone()["cnt"]

        # Low stock medicines
        cursor.execute("SELECT COUNT(*) AS cnt FROM dispensary_medicines WHERE stock_quantity <= reorder_level;")
        low_stock_medicines = cursor.fetchone()["cnt"]

        # Total registered health profiles
        cursor.execute("SELECT COUNT(*) AS cnt FROM health_profiles;")
        total_profiles_registered = cursor.fetchone()["cnt"]

        # Urgent / Emergency encounters
        cursor.execute("SELECT COUNT(*) AS cnt FROM medical_encounters WHERE triage_severity IN ('URGENT', 'EMERGENCY');")
        emergency_triage_count = cursor.fetchone()["cnt"]

        # Allergies recorded
        cursor.execute(
            """
            SELECT COUNT(*) AS cnt FROM health_profiles
            WHERE allergies != 'None' AND allergies != '' AND LOWER(allergies) != 'no allergies';
            """
        )
        allergies_recorded_count = cursor.fetchone()["cnt"]

        cursor.close()

        return {
            "total_encounters": total_encounters,
            "student_visits": student_visits,
            "faculty_visits": faculty_visits,
            "active_sick_leaves": active_sick_leaves,
            "low_stock_medicines": low_stock_medicines,
            "total_profiles_registered": total_profiles_registered,
            "emergency_triage_count": emergency_triage_count,
            "allergies_recorded_count": allergies_recorded_count,
        }
