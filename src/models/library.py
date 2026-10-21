"""Library & Digital Resource Circulation Schemas."""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class LibraryBookBase(BaseModel):
    isbn: str = Field(..., min_length=5, max_length=25, description="ISBN-10 or ISBN-13 identifier")
    title: str = Field(..., min_length=2, max_length=200)
    author: str = Field(..., min_length=2, max_length=150)
    category: Literal[
        "COMPUTER_SCIENCE",
        "ENGINEERING",
        "MANAGEMENT",
        "BIOTECH",
        "MATHEMATICS",
        "LITERATURE",
        "GENERAL",
    ] = "COMPUTER_SCIENCE"
    total_copies: int = Field(1, ge=1)
    shelf_location: str = Field("Main Stack A-1", max_length=100)
    publisher: Optional[str] = None
    edition: Optional[str] = "1st Ed"
    publication_year: Optional[int] = Field(None, ge=1900, le=2100)


class LibraryBookCreate(LibraryBookBase):
    pass


class LibraryBookOut(LibraryBookBase):
    id: int
    available_copies: int
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class BookIssueRequest(BaseModel):
    book_id: int = Field(..., gt=0)
    student_id: int = Field(..., gt=0)
    issue_date: str = Field(..., description="ISO Date YYYY-MM-DD")
    due_date: str = Field(..., description="ISO Date YYYY-MM-DD")
    remarks: Optional[str] = None


class BookReturnRequest(BaseModel):
    return_date: str = Field(..., description="ISO Date YYYY-MM-DD")
    fine_amount: float = Field(0.0, ge=0.0)
    remarks: Optional[str] = None


class BookLoanOut(BaseModel):
    id: int
    book_id: int
    student_id: int
    book_title: Optional[str] = None
    isbn: Optional[str] = None
    student_name: Optional[str] = None
    enrollment_no: Optional[str] = None
    issue_date: str
    due_date: str
    return_date: Optional[str] = None
    fine_amount: float = 0.0
    status: Literal["ISSUED", "RETURNED", "OVERDUE"]
    remarks: Optional[str] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class LibraryStatsOut(BaseModel):
    total_titles: int
    total_copies: int
    available_copies: int
    active_loans: int
    overdue_loans: int
    total_fines_collected: float
