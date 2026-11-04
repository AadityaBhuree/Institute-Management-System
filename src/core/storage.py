"""Secure Document & Media Storage Core Module.
Provides file signature magic-byte verification, safe UUID naming, path traversal prevention,
and strict extension / payload size validation.
"""

import os
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from src.core.config import MAX_UPLOAD_SIZE_BYTES, UPLOAD_DIR

# Dangerous file extensions strictly forbidden from institutional upload
FORBIDDEN_EXTENSIONS = {
    ".exe",
    ".bat",
    ".cmd",
    ".sh",
    ".bash",
    ".php",
    ".phtml",
    ".py",
    ".pyw",
    ".js",
    ".vbs",
    ".ps1",
    ".jar",
    ".msi",
    ".dll",
    ".com",
    ".scr",
    ".cgi",
    ".pl",
}

# Supported institutional MIME types mapped to canonical file extensions
ALLOWED_MIME_TYPES: Dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}


def _verify_magic_bytes(header: bytes) -> Optional[str]:
    """Verify true content type using binary magic byte signatures."""
    if len(header) < 4:
        return None

    # JPEG signature: FF D8 FF
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"

    # PNG signature: 89 50 4E 47 0D 0A 1A 0A
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"

    # GIF signature: GIF87a or GIF89a
    if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
        return "image/gif"

    # WebP signature: RIFF....WEBP
    if header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WEBP":
        return "image/webp"

    # PDF signature: %PDF-
    if header.startswith(b"%PDF-"):
        return "application/pdf"

    # DOCX / ZIP archive signature: PK\x03\x04
    if header.startswith(b"PK\x03\x04"):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    # Check for valid plain text (ASCII/UTF-8 with printable/whitespace chars)
    try:
        sample = header[:256].decode("utf-8")
        if all(c.isprintable() or c in "\r\n\t " for c in sample):
            return "text/plain"
    except UnicodeDecodeError:
        pass

    return None


class StorageManager:
    """Enterprise file upload and document storage provider."""

    @staticmethod
    def validate_file(
        file_bytes: bytes,
        original_filename: str,
        max_size: int = MAX_UPLOAD_SIZE_BYTES,
    ) -> Tuple[str, str]:
        """Validate payload size, filename extension, and binary magic bytes.

        Returns (canonical_extension, verified_mime_type).
        Raises ValueError on security policy violation.
        """
        if not file_bytes:
            raise ValueError("Uploaded file is empty (0 bytes).")

        if len(file_bytes) > max_size:
            max_mb = max_size / (1024 * 1024)
            raise ValueError(f"File size exceeds maximum permitted limit of {max_mb:.1f} MB.")

        if not original_filename or not original_filename.strip():
            raise ValueError("Original filename must not be blank.")

        clean_name = os.path.basename(original_filename.strip())
        ext = Path(clean_name).suffix.lower()

        if not ext:
            raise ValueError("File extension is required.")

        if ext in FORBIDDEN_EXTENSIONS:
            raise ValueError(
                f"Security policy violation: Files with extension '{ext}' are strictly prohibited."
            )

        # Inspect binary magic numbers
        detected_mime = _verify_magic_bytes(file_bytes[:32])
        if not detected_mime:
            raise ValueError(
                "Unsupported or disguised file format. File content signature does not match allowed types."
            )

        # Ensure declared extension is compatible with detected MIME type
        expected_ext = ALLOWED_MIME_TYPES.get(detected_mime)
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf", ".txt", ".doc", ".docx"):
            raise ValueError(f"File extension '{ext}' is not permitted.")

        # Disallow mismatch where an executable/binary disguises as another type
        if detected_mime == "application/pdf" and ext != ".pdf":
            raise ValueError("File header indicates PDF, but extension does not match.")
        if detected_mime in ("image/jpeg", "image/png", "image/webp", "image/gif") and ext not in (
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".gif",
        ):
            raise ValueError("File header indicates Image, but extension does not match.")

        canonical_ext = expected_ext if expected_ext else ext
        return canonical_ext, detected_mime

    @staticmethod
    def save_file(
        file_bytes: bytes,
        original_filename: str,
        category: str = "GENERAL",
        max_size: int = MAX_UPLOAD_SIZE_BYTES,
    ) -> Dict[str, Any]:
        """Validate and atomically store file into isolated UPLOAD_DIR with UUID naming."""
        ext, mime_type = StorageManager.validate_file(file_bytes, original_filename, max_size)

        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        file_id = f"doc_{uuid.uuid4().hex}"
        filename = f"{file_id}{ext}"
        destination = (UPLOAD_DIR / filename).resolve()

        # Path traversal guard
        if not str(destination).startswith(str(UPLOAD_DIR.resolve())):
            raise ValueError("Path traversal attempt detected in storage destination.")

        with open(destination, "wb") as f:
            f.write(file_bytes)

        return {
            "file_id": file_id,
            "filename": filename,
            "original_name": os.path.basename(original_filename),
            "mime_type": mime_type,
            "size_bytes": len(file_bytes),
            "category": category.upper(),
            "file_path": str(destination),
        }

    @staticmethod
    def resolve_file(file_id: str) -> Optional[Tuple[Path, str]]:
        """Safely locate stored file on disk and return (file_path, mime_type) or None."""
        if not file_id or "/" in file_id or "\\" in file_id or ".." in file_id:
            return None

        clean_id = os.path.basename(file_id)
        candidates = list(UPLOAD_DIR.glob(f"{clean_id}.*"))
        if not candidates:
            return None

        target = candidates[0].resolve()
        if not str(target).startswith(str(UPLOAD_DIR.resolve())) or not target.is_file():
            return None

        ext = target.suffix.lower()
        mime_type = "application/octet-stream"
        for mime, allowed_ext in ALLOWED_MIME_TYPES.items():
            if allowed_ext == ext:
                mime_type = mime
                break

        return target, mime_type

    @staticmethod
    def delete_file(file_path_or_id: str | Path) -> bool:
        """Safely delete file from disk storage."""
        if isinstance(file_path_or_id, Path):
            path = file_path_or_id.resolve()
        elif "/" in str(file_path_or_id) or "\\" in str(file_path_or_id):
            path = Path(file_path_or_id).resolve()
        else:
            resolved = StorageManager.resolve_file(str(file_path_or_id))
            if not resolved:
                return False
            path = resolved[0]

        if not str(path).startswith(str(UPLOAD_DIR.resolve())):
            return False

        if path.is_file():
            path.unlink(missing_ok=True)
            return True
        return False
