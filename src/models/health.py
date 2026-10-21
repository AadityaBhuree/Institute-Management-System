"""Campus Health, Student Clinic & Infirmary Hub Pydantic Models."""

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class HealthProfileBase(BaseModel):
    person_type: Literal["STUDENT", "FACULTY"]
    student_id: Optional[int] = Field(None, gt=0)
    faculty_id: Optional[int] = Field(None, gt=0)
    blood_group: Literal["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
    allergies: str = Field("None", max_length=500)
    chronic_conditions: str = Field("None", max_length=500)
    emergency_contact_name: str = Field(..., min_length=2, max_length=150)
    emergency_contact_phone: str = Field(..., min_length=5, max_length=30)
    emergency_contact_relation: str = Field("Parent", max_length=100)
    insurance_provider: Optional[str] = Field(None, max_length=150)
    insurance_policy_number: Optional[str] = Field(None, max_length=100)


class HealthProfileCreate(HealthProfileBase):
    @model_validator(mode="after")
    def validate_person_link(self) -> "HealthProfileCreate":
        if self.person_type == "STUDENT" and not self.student_id:
            raise ValueError("student_id is required when person_type is STUDENT")
        if self.person_type == "FACULTY" and not self.faculty_id:
            raise ValueError("faculty_id is required when person_type is FACULTY")
        if self.person_type == "STUDENT" and self.faculty_id:
            raise ValueError("faculty_id must be null for student profiles")
        if self.person_type == "FACULTY" and self.student_id:
            raise ValueError("student_id must be null for faculty profiles")
        return self


class HealthProfileUpdate(BaseModel):
    blood_group: Optional[Literal["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]] = None
    allergies: Optional[str] = Field(None, max_length=500)
    chronic_conditions: Optional[str] = Field(None, max_length=500)
    emergency_contact_name: Optional[str] = Field(None, min_length=2, max_length=150)
    emergency_contact_phone: Optional[str] = Field(None, min_length=5, max_length=30)
    emergency_contact_relation: Optional[str] = Field(None, max_length=100)
    insurance_provider: Optional[str] = Field(None, max_length=150)
    insurance_policy_number: Optional[str] = Field(None, max_length=100)


class HealthProfileOut(HealthProfileBase):
    id: int
    person_name: Optional[str] = None
    enrollment_or_faculty_id: Optional[str] = None
    department_name: Optional[str] = None
    department_code: Optional[str] = None
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


class DispensaryMedicineBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    category: Literal[
        "ANALGESIC",
        "ANTIBIOTIC",
        "ANTIHISTAMINE",
        "ANTISEPTIC",
        "ANTACID",
        "FIRST_AID",
        "SUPPLEMENT",
        "OTHER",
    ] = "ANALGESIC"
    form: Literal[
        "TABLET",
        "CAPSULE",
        "SYRUP",
        "OINTMENT",
        "INJECTION",
        "BANDAGE",
        "DROPS",
        "SACHET",
        "OTHER",
    ] = "TABLET"
    stock_quantity: int = Field(0, ge=0)
    unit: str = Field("Units", max_length=50)
    reorder_level: int = Field(10, ge=0)
    expiry_date: str = Field(..., description="ISO Date YYYY-MM-DD")
    batch_number: str = Field(..., min_length=2, max_length=100)


class DispensaryMedicineCreate(DispensaryMedicineBase):
    item_code: Optional[str] = Field(None, max_length=50)


class DispensaryStockUpdate(BaseModel):
    quantity_change: int = Field(..., description="Positive to add stock, negative to consume")
    reason: Optional[str] = Field("Restock", max_length=200)


class DispensaryMedicineOut(DispensaryMedicineBase):
    id: int
    item_code: str
    is_low_stock: bool = False
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class PrescriptionItemCreate(BaseModel):
    medicine_id: Optional[int] = Field(None, gt=0)
    medicine_name: str = Field(..., min_length=2, max_length=150)
    dosage: str = Field(..., min_length=1, max_length=50)
    frequency: str = Field(..., min_length=1, max_length=100)
    duration_days: int = Field(3, gt=0)
    quantity_dispensed: int = Field(1, ge=0)


class PrescriptionItemOut(PrescriptionItemCreate):
    id: int
    encounter_id: int
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class MedicalEncounterBase(BaseModel):
    patient_type: Literal["STUDENT", "FACULTY"]
    student_id: Optional[int] = Field(None, gt=0)
    faculty_id: Optional[int] = Field(None, gt=0)
    visit_date: str = Field(..., description="ISO Date YYYY-MM-DD")
    doctor_name: str = Field(..., min_length=2, max_length=150)
    chief_complaint: str = Field(..., min_length=2, max_length=500)
    symptoms: Optional[str] = Field(None, max_length=1000)
    diagnosis: str = Field(..., min_length=2, max_length=500)
    blood_pressure: Optional[str] = Field(None, max_length=20)
    pulse_bpm: Optional[int] = Field(None, gt=0, lt=300)
    temperature_f: Optional[float] = Field(None, gt=80.0, lt=115.0)
    triage_severity: Literal["NORMAL", "URGENT", "EMERGENCY"] = "NORMAL"
    treatment_given: Optional[str] = Field(None, max_length=1000)
    follow_up_date: Optional[str] = Field(None, description="ISO Date YYYY-MM-DD")


class MedicalEncounterCreate(MedicalEncounterBase):
    prescriptions: List[PrescriptionItemCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_patient_link(self) -> "MedicalEncounterCreate":
        if self.patient_type == "STUDENT" and not self.student_id:
            raise ValueError("student_id is required for student encounter")
        if self.patient_type == "FACULTY" and not self.faculty_id:
            raise ValueError("faculty_id is required for faculty encounter")
        if self.patient_type == "STUDENT" and self.faculty_id:
            raise ValueError("faculty_id must be null for student encounter")
        if self.patient_type == "FACULTY" and self.student_id:
            raise ValueError("student_id must be null for faculty encounter")
        return self


class MedicalEncounterOut(MedicalEncounterBase):
    id: int
    encounter_code: str
    patient_name: Optional[str] = None
    patient_identifier: Optional[str] = None
    department_name: Optional[str] = None
    blood_group: Optional[str] = None
    allergies: Optional[str] = None
    prescriptions: List[PrescriptionItemOut] = Field(default_factory=list)
    has_medical_certificate: bool = False
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class MedicalCertificateBase(BaseModel):
    encounter_id: int = Field(..., gt=0)
    rest_from_date: str = Field(..., description="ISO Date YYYY-MM-DD")
    rest_to_date: str = Field(..., description="ISO Date YYYY-MM-DD")
    fit_to_resume_date: str = Field(..., description="ISO Date YYYY-MM-DD")
    diagnosis_summary: str = Field(..., min_length=2, max_length=500)
    doctor_remarks: Optional[str] = Field(None, max_length=500)


class MedicalCertificateCreate(MedicalCertificateBase):
    @model_validator(mode="after")
    def validate_dates(self) -> "MedicalCertificateCreate":
        if self.rest_to_date < self.rest_from_date:
            raise ValueError("rest_to_date cannot precede rest_from_date")
        if self.fit_to_resume_date < self.rest_to_date:
            raise ValueError("fit_to_resume_date cannot precede rest_to_date")
        return self


class MedicalCertificateOut(MedicalCertificateBase):
    id: int
    certificate_number: str
    patient_type: str
    student_id: Optional[int] = None
    faculty_id: Optional[int] = None
    patient_name: Optional[str] = None
    patient_identifier: Optional[str] = None
    doctor_name: Optional[str] = None
    status: Literal["ISSUED", "REVOKED"]
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class HealthStatsOut(BaseModel):
    total_encounters: int
    student_visits: int
    faculty_visits: int
    active_sick_leaves: int
    low_stock_medicines: int
    total_profiles_registered: int
    emergency_triage_count: int
    allergies_recorded_count: int
