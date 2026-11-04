"""Document & Media Storage Domain Service.
Manages database persistence, upload record tracking, querying, and deletion lifecycle.
"""

import logging
import sqlite3
from typing import Any, Dict, List, Optional

from src.core.storage import StorageManager
from src.database.connection import transaction
from src.database.utils import row_to_dict, rows_to_list


class StorageService:
    """Institutional document persistence and metadata service."""

    @staticmethod
    def save_document(
        conn: sqlite3.Connection,
        file_bytes: bytes,
        original_filename: str,
        category: str = "GENERAL",
        uploaded_by_user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Validate, store file on disk, and record metadata into database."""
        normalized_cat = category.strip().upper()
        if normalized_cat not in ("AVATAR", "RESUME", "MEDICAL", "PROOF", "GENERAL"):
            normalized_cat = "GENERAL"

        # 1. Disk persistence & security verification
        saved = StorageManager.save_file(
            file_bytes=file_bytes,
            original_filename=original_filename,
            category=normalized_cat,
        )

        file_id = saved["file_id"]
        original_name = saved["original_name"]
        mime_type = saved["mime_type"]
        size_bytes = saved["size_bytes"]
        file_path = saved["file_path"]

        # 2. Database record insertion
        with transaction(conn) as cur:
            cur.execute(
                """
                INSERT INTO uploaded_documents (
                    file_id, original_name, mime_type, size_bytes, category, file_path, uploaded_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    file_id,
                    original_name,
                    mime_type,
                    size_bytes,
                    normalized_cat,
                    file_path,
                    uploaded_by_user_id,
                ),
            )
            doc_id = cur.lastrowid

        logging.getLogger("ims").info(
            "Stored document %s ('%s', %d bytes, cat=%s) by user %s",
            file_id,
            original_name,
            size_bytes,
            normalized_cat,
            uploaded_by_user_id,
        )

        return {
            "id": doc_id,
            "file_id": file_id,
            "original_name": original_name,
            "mime_type": mime_type,
            "size_bytes": size_bytes,
            "category": normalized_cat,
            "uploaded_by": uploaded_by_user_id,
            "file_url": f"/api/storage/files/{file_id}",
        }

    @staticmethod
    def get_document(conn: sqlite3.Connection, file_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored document metadata by file_id."""
        cur = conn.cursor()
        cur.execute("SELECT * FROM uploaded_documents WHERE file_id = ?;", (file_id,))
        row = cur.fetchone()
        cur.close()

        if not row:
            return None

        data = row_to_dict(row)
        data["file_url"] = f"/api/storage/files/{file_id}"
        return data

    @staticmethod
    def list_documents(
        conn: sqlite3.Connection,
        category: Optional[str] = None,
        uploaded_by: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Query and paginate uploaded documents with optional filtering."""
        query = "SELECT * FROM uploaded_documents WHERE 1=1"
        count_query = "SELECT COUNT(*) AS total FROM uploaded_documents WHERE 1=1"
        params: List[Any] = []

        if category:
            query += " AND category = ?"
            count_query += " AND category = ?"
            params.append(category.strip().upper())
        if uploaded_by is not None:
            query += " AND uploaded_by = ?"
            count_query += " AND uploaded_by = ?"
            params.append(uploaded_by)

        cur = conn.cursor()
        cur.execute(count_query, tuple(params))
        total = cur.fetchone()["total"]

        query += " ORDER BY id DESC LIMIT ? OFFSET ?;"
        cur.execute(query, tuple(params + [limit, offset]))
        rows = cur.fetchall()
        cur.close()

        docs = []
        for r in rows_to_list(rows):
            r["file_url"] = f"/api/storage/files/{r['file_id']}"
            docs.append(r)

        return {"total": total, "documents": docs}

    @staticmethod
    def delete_document(
        conn: sqlite3.Connection,
        file_id: str,
        user_id: Optional[int] = None,
        is_admin: bool = False,
    ) -> bool:
        """Delete document file from disk and database record."""
        doc = StorageService.get_document(conn, file_id)
        if not doc:
            raise KeyError(f"Document with file_id '{file_id}' not found.")

        # Authorization check: only admin or the user who uploaded can delete
        if not is_admin and doc.get("uploaded_by") != user_id:
            raise PermissionError("Access denied: You cannot delete another user's document.")

        # 1. Delete physical file from disk
        StorageManager.delete_file(doc["file_path"])

        # 2. Delete database record
        with transaction(conn) as cur:
            cur.execute("DELETE FROM uploaded_documents WHERE file_id = ?;", (file_id,))

        logging.getLogger("ims").info(
            "Deleted document %s ('%s') by user %s (admin=%s)",
            file_id,
            doc["original_name"],
            user_id,
            is_admin,
        )
        return True
