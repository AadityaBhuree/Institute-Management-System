"""Campus Health, Student Clinic & Infirmary Hub API Router."""

import sqlite3
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.database.connection import get_db
from src.models.health import (
    DispensaryMedicineCreate,
    DispensaryMedicineOut,
    DispensaryStockUpdate,
    HealthProfileCreate,
    HealthProfileOut,
    HealthStatsOut,
    MedicalCertificateCreate,
    MedicalCertificateOut,
    MedicalEncounterCreate,
    MedicalEncounterOut,
)
from src.services.health_service import HealthService

router = APIRouter(prefix="/api/health-center", tags=["Campus Health & Infirmary"])


# =============================================================================
# HEALTH TELEMETRY
# =============================================================================


@router.get("/stats", response_model=HealthStatsOut)
def get_health_stats(conn: sqlite3.Connection = Depends(get_db)):
    """Retrieve campus clinic and infirmary health telemetry KPI metrics."""
    return HealthService.get_health_stats(conn)


# =============================================================================
# HEALTH PROFILES
# =============================================================================


@router.get("/profiles", response_model=List[HealthProfileOut])
def list_health_profiles(
    person_type: Optional[str] = Query(None, description="STUDENT or FACULTY"),
    blood_group: Optional[str] = Query(None, description="A+, A-, B+, B-, AB+, AB-, O+, O-"),
    has_allergies: Optional[bool] = Query(
        None, description="Filter profiles with recorded allergies"
    ),
    search: Optional[str] = Query(
        None, description="Search by name, ID, emergency contact, or condition"
    ),
    conn: sqlite3.Connection = Depends(get_db),
):
    """List student and faculty health profiles with demographic and condition filters."""
    return HealthService.list_profiles(
        conn,
        person_type=person_type,
        blood_group=blood_group,
        has_allergies=has_allergies,
        search=search,
    )


@router.post("/profiles", response_model=HealthProfileOut, status_code=status.HTTP_201_CREATED)
def create_or_update_health_profile(
    data: HealthProfileCreate, conn: sqlite3.Connection = Depends(get_db)
):
    """Create or update a student or faculty medical health profile."""
    try:
        return HealthService.create_or_update_profile(conn, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/profiles/{person_type}/{person_id}", response_model=HealthProfileOut)
def get_health_profile_by_person(
    person_type: str, person_id: int, conn: sqlite3.Connection = Depends(get_db)
):
    """Retrieve health profile by student_id or faculty_id."""
    person_type_norm = person_type.upper()
    if person_type_norm not in ("STUDENT", "FACULTY"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="person_type must be either STUDENT or FACULTY",
        )
    profile = HealthService.get_profile_by_person(conn, person_type_norm, person_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Health profile for {person_type_norm} id {person_id} not found",
        )
    return profile


# =============================================================================
# DISPENSARY MEDICINES
# =============================================================================


@router.get("/medicines", response_model=List[DispensaryMedicineOut])
def list_dispensary_medicines(
    category: Optional[str] = Query(
        None,
        description="ANALGESIC, ANTIBIOTIC, ANTIHISTAMINE, ANTISEPTIC, ANTACID, FIRST_AID, SUPPLEMENT, OTHER",
    ),
    low_stock_only: bool = Query(
        False, description="Filter only medicines at or below reorder level"
    ),
    search: Optional[str] = Query(None, description="Search by medicine name, code, or batch"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """List dispensary pharmacy medicine stock with low inventory indicators."""
    return HealthService.list_dispensary_medicines(
        conn,
        category=category,
        low_stock_only=low_stock_only,
        search=search,
    )


@router.post(
    "/medicines", response_model=DispensaryMedicineOut, status_code=status.HTTP_201_CREATED
)
def create_dispensary_medicine(
    data: DispensaryMedicineCreate, conn: sqlite3.Connection = Depends(get_db)
):
    """Add a new medicine batch to the infirmary dispensary inventory."""
    try:
        return HealthService.create_dispensary_medicine(conn, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/medicines/{id}", response_model=DispensaryMedicineOut)
def get_dispensary_medicine(id: int, conn: sqlite3.Connection = Depends(get_db)):
    """Retrieve details for a specific dispensary medicine item."""
    try:
        return HealthService.get_dispensary_medicine(conn, id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.put("/medicines/{id}/stock", response_model=DispensaryMedicineOut)
def update_dispensary_stock(
    id: int, data: DispensaryStockUpdate, conn: sqlite3.Connection = Depends(get_db)
):
    """Update stock quantity for a dispensary medicine item (restock or dispense)."""
    try:
        return HealthService.update_dispensary_stock(
            conn, id, quantity_change=data.quantity_change, reason=data.reason or "Restock"
        )
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# =============================================================================
# MEDICAL ENCOUNTERS & CONSULTATIONS
# =============================================================================


@router.get("/encounters", response_model=List[MedicalEncounterOut])
def list_medical_encounters(
    patient_type: Optional[str] = Query(None, description="STUDENT or FACULTY"),
    triage_severity: Optional[str] = Query(None, description="NORMAL, URGENT, EMERGENCY"),
    visit_date: Optional[str] = Query(None, description="ISO Date YYYY-MM-DD"),
    search: Optional[str] = Query(
        None, description="Search by code, doctor, patient name, or complaint"
    ),
    limit: int = Query(100, ge=1, le=500),
    conn: sqlite3.Connection = Depends(get_db),
):
    """List clinical consultation encounter records with multi-criteria filtering."""
    return HealthService.list_encounters(
        conn,
        patient_type=patient_type,
        triage_severity=triage_severity,
        visit_date=visit_date,
        search=search,
        limit=limit,
    )


@router.post("/encounters", response_model=MedicalEncounterOut, status_code=status.HTTP_201_CREATED)
def create_medical_encounter(
    data: MedicalEncounterCreate, conn: sqlite3.Connection = Depends(get_db)
):
    """Log a clinical consultation encounter with vital signs and prescription dispensation."""
    try:
        return HealthService.create_encounter(conn, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/encounters/{id}", response_model=MedicalEncounterOut)
def get_medical_encounter(id: int, conn: sqlite3.Connection = Depends(get_db)):
    """Retrieve detailed consultation record including vital signs, diagnosis, and prescriptions."""
    try:
        return HealthService.get_encounter(conn, id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


# =============================================================================
# MEDICAL CERTIFICATES & SICK LEAVE ENDORSEMENTS
# =============================================================================


@router.get("/certificates", response_model=List[MedicalCertificateOut])
def list_medical_certificates(
    status_filter: Optional[str] = Query(None, alias="status", description="ISSUED or REVOKED"),
    patient_type: Optional[str] = Query(None, description="STUDENT or FACULTY"),
    search: Optional[str] = Query(
        None, description="Search by certificate number, doctor, or patient"
    ),
    conn: sqlite3.Connection = Depends(get_db),
):
    """List issued medical sick leave certificates."""
    return HealthService.list_medical_certificates(
        conn,
        status=status_filter,
        patient_type=patient_type,
        search=search,
    )


@router.post(
    "/certificates", response_model=MedicalCertificateOut, status_code=status.HTTP_201_CREATED
)
def issue_medical_certificate(
    data: MedicalCertificateCreate, conn: sqlite3.Connection = Depends(get_db)
):
    """Issue a verifiable official medical certificate for an encounter."""
    try:
        return HealthService.issue_medical_certificate(conn, data)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/certificates/{id}", response_model=MedicalCertificateOut)
def get_medical_certificate(id: int, conn: sqlite3.Connection = Depends(get_db)):
    """Retrieve medical certificate details by ID."""
    try:
        return HealthService.get_medical_certificate(conn, id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.put("/certificates/{id}/revoke", response_model=MedicalCertificateOut)
def revoke_medical_certificate(id: int, conn: sqlite3.Connection = Depends(get_db)):
    """Revoke an active medical certificate."""
    try:
        return HealthService.revoke_medical_certificate(conn, id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
