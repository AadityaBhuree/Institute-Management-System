"""Database initialization script.
Executes the schema and inserts baseline institutional departments if not present.
"""

from pathlib import Path

from src.core.config import DB_PATH  # pyright: ignore[reportMissingImports] # type: ignore
from src.database.connection import (  # pyright: ignore[reportMissingImports] # type: ignore
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


def init_database(db_path: Path | str | None = None) -> None:
    """Initialize database tables and initial baseline reference records."""
    conn = get_connection(db_path)
    try:
        with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
            ddl_script = f.read()

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
    finally:
        conn.close()


if __name__ == "__main__":
    init_database()
    print(f"Database initialized successfully at: {DB_PATH}")
