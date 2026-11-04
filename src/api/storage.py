"""Document and Media Storage REST API Router.
Handles multipart file uploads, content-type verification, and streaming downloads.
"""

import sqlite3
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse

from src.core.security import get_current_user, get_current_user_optional
from src.core.storage import StorageManager
from src.database.connection import get_db
from src.models.storage import DocumentListResponse, DocumentUploadResponse
from src.services.auth_service import AuthService
from src.services.storage_service import StorageService

router = APIRouter(tags=["Document Storage"])


@router.post(
    "/api/storage/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form("GENERAL"),
    conn: sqlite3.Connection = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """Upload a document or media asset with magic-byte signature validation."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename must not be empty.",
        )

    try:
        content = await file.read()
        user_id = current_user.get("id") if current_user else None
        username = current_user.get("username") if current_user else "anonymous"

        result = StorageService.save_document(
            conn=conn,
            file_bytes=content,
            original_filename=file.filename,
            category=category,
            uploaded_by_user_id=user_id,
        )

        AuthService.log_audit(
            conn,
            action="FILE_UPLOAD",
            resource="document",
            resource_id=result["file_id"],
            user_id=user_id,
            username=username,
            details=f"Uploaded '{result['original_name']}' ({result['size_bytes']} bytes, cat={result['category']})",
        )

        return {
            "status": "SUCCESS",
            "message": f"File '{result['original_name']}' uploaded and verified successfully.",
            "document": result,
        }
    except ValueError as e:
        error_msg = str(e)
        if "exceeds maximum permitted limit" in error_msg:
            status_413 = getattr(status, "HTTP_413_CONTENT_TOO_LARGE", 413)
            raise HTTPException(status_code=status_413, detail=error_msg) from e
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg) from e


@router.get("/api/storage/files/{file_id}")
def stream_file(
    file_id: str,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Safely stream stored document with verified MIME headers and path traversal guards."""
    doc_record = StorageService.get_document(conn, file_id)
    resolved = StorageManager.resolve_file(file_id)
    if not doc_record or not resolved:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with identifier '{file_id}' not found.",
        )

    file_path, mime_type = resolved
    filename = doc_record["original_name"]

    return FileResponse(
        path=file_path,
        media_type=mime_type,
        filename=filename,
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "public, max-age=86400",
        },
    )


@router.get("/api/storage/documents", response_model=DocumentListResponse)
def list_documents(
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List uploaded documents with role-aware privacy boundaries."""
    role = current_user.get("role")
    user_id = current_user.get("id")

    # Admins can query all documents; students and faculty query their own
    query_user_id = None if role == "admin" else user_id

    result = StorageService.list_documents(
        conn=conn,
        category=category,
        uploaded_by=query_user_id,
        limit=min(limit, 100),
        offset=max(offset, 0),
    )
    return result


@router.delete("/api/storage/files/{file_id}")
def delete_document(
    file_id: str,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete an uploaded document (Admin or owner only)."""
    role = current_user.get("role")
    user_id = current_user.get("id")
    is_admin = role == "admin"

    try:
        StorageService.delete_document(
            conn=conn,
            file_id=file_id,
            user_id=user_id,
            is_admin=is_admin,
        )
        AuthService.log_audit(
            conn,
            action="FILE_DELETE",
            resource="document",
            resource_id=file_id,
            user_id=user_id,
            username=current_user.get("username"),
            details=f"Deleted document {file_id}",
        )
        return {"status": "DELETED", "file_id": file_id}
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
