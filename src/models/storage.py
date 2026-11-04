"""Pydantic Models for Document and Media Storage Subsystem."""

from typing import List, Optional

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """Metadata schema representing an uploaded institutional document."""

    id: Optional[int] = Field(default=None, description="Database unique record ID")
    file_id: str = Field(..., description="Unique opaque alphanumeric file identifier")
    original_name: str = Field(..., description="Original client-supplied file name")
    mime_type: str = Field(..., description="Verified MIME content type")
    size_bytes: int = Field(..., ge=0, description="Exact file size in bytes")
    category: str = Field(
        default="GENERAL",
        description="Functional document category: AVATAR, RESUME, MEDICAL, PROOF, GENERAL",
    )
    uploaded_by: Optional[int] = Field(default=None, description="User ID of uploader")
    file_url: str = Field(..., description="Public/authenticated streaming URL")
    created_at: Optional[str] = Field(default=None, description="ISO timestamp of upload")


class DocumentUploadResponse(BaseModel):
    """API response envelope returned upon successful document upload."""

    status: str = Field(default="SUCCESS", description="Operation status indicator")
    message: str = Field(..., description="Human-readable confirmation message")
    document: DocumentMetadata


class DocumentListResponse(BaseModel):
    """Paginated collection of uploaded documents."""

    total: int = Field(..., ge=0, description="Total matching document count")
    documents: List[DocumentMetadata]
