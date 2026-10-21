"""Attendance and Examination schemas."""

from typing import List, Optional

from pydantic import BaseModel, Field


class SingleAttendance(BaseModel):
    student_id: int = Field(..., gt=0)
    status: str = Field(..., description="PRESENT, ABSENT, LATE, EXCUSED")
    remarks: Optional[str] = None


class AttendanceBatchMark(BaseModel):
    course_id: int = Field(..., gt=0)
    attendance_date: str = Field(..., description="YYYY-MM-DD")
    records: List[SingleAttendance]
    recorded_by: Optional[int] = None


class AttendanceRecordOut(BaseModel):
    id: int
    student_id: int
    student_name: str
    enrollment_no: str
    course_id: int
    course_code: str
    attendance_date: str
    status: str
    remarks: Optional[str] = None


class ExamCreate(BaseModel):
    course_id: int = Field(..., gt=0)
    title: str = Field(..., min_length=3, max_length=150)
    exam_type: str = Field(
        "MIDTERM", description="MIDTERM, FINAL, QUIZ, LAB_ASSESSMENT, ASSIGNMENT"
    )
    exam_date: str = Field(..., description="YYYY-MM-DD")
    max_marks: float = Field(100.0, gt=0)
    passing_marks: float = Field(40.0, ge=0)
    weightage_percent: float = Field(100.0, gt=0, le=100)


class ExamOut(ExamCreate):
    id: int
    course_code: Optional[str] = None
    course_title: Optional[str] = None
    graded_count: int = 0
    created_at: Optional[str] = None


class SingleGrade(BaseModel):
    student_id: int = Field(..., gt=0)
    marks_obtained: float = Field(..., ge=0)
    remarks: Optional[str] = None


class ExamGradeBatchSubmit(BaseModel):
    grades: List[SingleGrade]


class ExamResultOut(BaseModel):
    id: int
    exam_id: int
    student_id: int
    student_name: str
    enrollment_no: str
    marks_obtained: float
    max_marks: float
    grade_letter: str
    remarks: Optional[str] = None
    evaluated_at: Optional[str] = None
