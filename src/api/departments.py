"""Academic departments API router."""

import sqlite3
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from src.database.connection import get_db
from src.models.department import DepartmentCreate, DepartmentOut
from src.services.department_service import DepartmentService

router = APIRouter(prefix="/api/departments", tags=["Departments"])


@router.get("", response_model=List[DepartmentOut])
def list_departments(conn: sqlite3.Connection = Depends(get_db)):
    """Retrieve all academic departments."""
    return DepartmentService.list_all(conn)


@router.post("", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
def create_department(dept_in: DepartmentCreate, conn: sqlite3.Connection = Depends(get_db)):
    """Create a new academic department."""
    try:
        return DepartmentService.create(conn, dept_in)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
