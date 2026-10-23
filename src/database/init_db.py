"""Database initialization script.
Executes the schema and inserts baseline institutional departments if not present.
"""

from pathlib import Path

from src.core.config import DB_PATH
from src.database.connection import (
    get_connection,
    transaction,
)

SCHEMA_FILE = Path(__file__).parent / "schema.sql"

DEFAULT_DEPARTMENTS = [
    (
        "CSE",
        "Computer Science & Engineering",
        "Department of Computer Science, Software Engineering, and AI",
    ),
    (
        "ECE",
        "Electronics & Communication Engineering",
        "Department of Embedded Systems, Telecommunications, and VLSI",
    ),
    (
        "MECH",
        "Mechanical Engineering",
        "Department of Robotics, Thermodynamics, and Manufacturing",
    ),
    (
        "BIOTECH",
        "Biotechnology & Bioinformatics",
        "Department of Computational Biology and Genetic Engineering",
    ),
    (
        "MGMT",
        "School of Management & Business",
        "Department of Business Analytics, Finance, and Enterprise Administration",
    ),
]

DEFAULT_USERS = [
    ("admin", "admin@institute.edu", "admin123", "admin"),
    ("faculty", "faculty@institute.edu", "faculty123", "faculty"),
    ("student", "student@institute.edu", "student123", "student"),
]


def init_database(db_path: Path | str | None = None) -> None:
    """Initialize database tables and initial baseline reference records."""
    conn = get_connection(db_path)
    try:
        with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
            ddl_script = f.read()

        # Migration check: Ensure students table has is_deleted column before creating index
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(students);")
        cols = [col["name"] for col in cursor.fetchall()]
        if cols and "is_deleted" not in cols:
            cursor.execute("ALTER TABLE students ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT 0;")
        cursor.close()

        # Execute DDL
        conn.executescript(ddl_script)

        # Ensure default departments exist
        with transaction(conn) as cursor:
            for code, name, desc in DEFAULT_DEPARTMENTS:
                cursor.execute(
                    """
                    INSERT INTO departments (code, name, description)
                    VALUES (?, ?, ?)
                    ON CONFLICT(code) DO UPDATE
                    SET name = excluded.name, description = excluded.description;
                    """,
                    (code, name, desc),
                )

            # Ensure default users exist
            from src.core.security import hash_password

            for username, email, raw_password, role in DEFAULT_USERS:
                cursor.execute(
                    "SELECT id FROM users WHERE username = ? OR email = ?;",
                    (username, email),
                )
                if not cursor.fetchone():
                    pw_hash = hash_password(raw_password)
                    cursor.execute(
                        """
                        INSERT INTO users (username, email, password_hash, role, status)
                        VALUES (?, ?, ?, ?, 'active');
                        """,
                        (username, email, pw_hash, role),
                    )

            # Log system initialization if audit_logs is empty
            cursor.execute("SELECT COUNT(*) AS total FROM audit_logs;")
            row = cursor.fetchone()
            if row and row["total"] == 0:
                cursor.execute(
                    """
                    INSERT INTO audit_logs (username, action, resource, details)
                    VALUES ('system', 'SYSTEM_INIT', 'database', 'Database initialized with baseline schemas and credentials');
                    """
                )
    finally:
        conn.close()


if __name__ == "__main__":
    init_database()
    print(f"Database initialized successfully at: {DB_PATH}")
