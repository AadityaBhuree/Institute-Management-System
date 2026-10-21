"""Campus Library & Resource Circulation Service."""

import sqlite3
from datetime import date
from typing import Dict, List, Optional

from src.database.connection import transaction
from src.models.library import BookIssueRequest, BookReturnRequest, LibraryBookCreate


class LibraryService:
    @staticmethod
    def list_books(
        conn: sqlite3.Connection,
        category: Optional[str] = None,
        search: Optional[str] = None,
        available_only: bool = False,
    ) -> List[dict]:
        """List library books with optional category and search filters."""
        query = """
            SELECT id, isbn, title, author, category, total_copies, available_copies,
                   shelf_location, publisher, edition, publication_year, created_at
            FROM library_books
            WHERE 1=1
        """
        params = []

        if category:
            query += " AND category = ?"
            params.append(category)

        if search:
            term = f"%{search.strip()}%"
            query += " AND (title LIKE ? OR author LIKE ? OR isbn LIKE ?)"
            params.extend([term, term, term])

        if available_only:
            query += " AND available_copies > 0"

        query += " ORDER BY title ASC;"

        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_book_by_id(conn: sqlite3.Connection, book_id: int) -> Optional[dict]:
        """Retrieve a book by primary key."""
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM library_books WHERE id = ?;", (book_id,))
        row = cursor.fetchone()
        cursor.close()
        return dict(row) if row else None

    @staticmethod
    def get_book_by_isbn(conn: sqlite3.Connection, isbn: str) -> Optional[dict]:
        """Retrieve a book by ISBN."""
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM library_books WHERE isbn = ?;", (isbn.strip(),))
        row = cursor.fetchone()
        cursor.close()
        return dict(row) if row else None

    @staticmethod
    def create_book(conn: sqlite3.Connection, data: LibraryBookCreate) -> dict:
        """Add a new book to the catalog."""
        if LibraryService.get_book_by_isbn(conn, data.isbn):
            raise ValueError(f"Book with ISBN '{data.isbn}' already exists in catalog.")

        with transaction(conn) as cursor:
            cursor.execute(
                """
                INSERT INTO library_books (
                    isbn, title, author, category, total_copies, available_copies,
                    shelf_location, publisher, edition, publication_year
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    data.isbn.strip(),
                    data.title.strip(),
                    data.author.strip(),
                    data.category,
                    data.total_copies,
                    data.total_copies,  # Initially all copies available
                    data.shelf_location.strip(),
                    data.publisher.strip() if data.publisher else None,
                    data.edition.strip() if data.edition else "1st Ed",
                    data.publication_year,
                ),
            )
            book_id = cursor.lastrowid

        return LibraryService.get_book_by_id(conn, book_id)  # type: ignore

    @staticmethod
    def issue_book(conn: sqlite3.Connection, data: BookIssueRequest) -> dict:
        """Issue a book copy to a student."""
        book = LibraryService.get_book_by_id(conn, data.book_id)
        if not book:
            raise ValueError(f"Book ID {data.book_id} not found.")

        if book["available_copies"] <= 0:
            raise ValueError(f"No copies of '{book['title']}' are currently available for issue.")

        # Validate student
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, first_name, last_name FROM students WHERE id = ?;",
            (data.student_id,),
        )
        student = cursor.fetchone()
        cursor.close()
        if not student:
            raise ValueError(f"Student ID {data.student_id} not found.")

        with transaction(conn) as cursor:
            # Insert loan record
            cursor.execute(
                """
                INSERT INTO book_loans (book_id, student_id, issue_date, due_date, status, remarks)
                VALUES (?, ?, ?, ?, 'ISSUED', ?);
                """,
                (data.book_id, data.student_id, data.issue_date, data.due_date, data.remarks),
            )
            loan_id = cursor.lastrowid

            # Decrement available copies
            cursor.execute(
                "UPDATE library_books SET available_copies = available_copies - 1 WHERE id = ?;",
                (data.book_id,),
            )

        loans = LibraryService.list_loans(conn)
        for loan in loans:
            if loan["id"] == loan_id:
                return loan
        return {
            "id": loan_id,
            "book_id": data.book_id,
            "student_id": data.student_id,
            "status": "ISSUED",
        }

    @staticmethod
    def return_book(conn: sqlite3.Connection, loan_id: int, return_data: BookReturnRequest) -> dict:
        """Process book return, update fine if applicable, and increment available copies."""
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM book_loans WHERE id = ?;", (loan_id,))
        loan = cursor.fetchone()
        cursor.close()

        if not loan:
            raise ValueError(f"Loan record ID {loan_id} not found.")

        if loan["status"] == "RETURNED":
            raise ValueError("This loan has already been marked as returned.")

        book_id = loan["book_id"]

        with transaction(conn) as cursor:
            cursor.execute(
                """
                UPDATE book_loans
                SET return_date = ?, fine_amount = ?, status = 'RETURNED', remarks = ?
                WHERE id = ?;
                """,
                (
                    return_data.return_date,
                    return_data.fine_amount,
                    return_data.remarks or loan["remarks"],
                    loan_id,
                ),
            )
            cursor.execute(
                "UPDATE library_books SET available_copies = available_copies + 1 WHERE id = ?;",
                (book_id,),
            )

        loans = LibraryService.list_loans(conn)
        for item in loans:
            if item["id"] == loan_id:
                return item
        return {"id": loan_id, "status": "RETURNED"}

    @staticmethod
    def list_loans(
        conn: sqlite3.Connection,
        status: Optional[str] = None,
        student_id: Optional[int] = None,
        book_id: Optional[int] = None,
    ) -> List[dict]:
        """List loans enriched with book and student metadata."""
        query = """
            SELECT l.id, l.book_id, l.student_id, l.issue_date, l.due_date, l.return_date,
                   l.fine_amount, l.status, l.remarks, l.created_at,
                   b.title AS book_title, b.isbn,
                   (s.first_name || ' ' || s.last_name) AS student_name, s.enrollment_no
            FROM book_loans l
            JOIN library_books b ON l.book_id = b.id
            JOIN students s ON l.student_id = s.id
            WHERE 1=1
        """
        params = []

        if status:
            query += " AND l.status = ?"
            params.append(status)

        if student_id:
            query += " AND l.student_id = ?"
            params.append(student_id)

        if book_id:
            query += " AND l.book_id = ?"
            params.append(book_id)

        query += " ORDER BY l.id DESC;"

        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()

        # Dynamically flag overdue loans if today > due_date and status is ISSUED
        today_str = date.today().isoformat()
        results = []
        for r in rows:
            d = dict(r)
            if d["status"] == "ISSUED" and d["due_date"] < today_str:
                d["is_overdue"] = True
            else:
                d["is_overdue"] = False
            results.append(d)
        return results

    @staticmethod
    def get_stats(conn: sqlite3.Connection) -> Dict[str, float]:
        """Get aggregate metrics for the library module."""
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*),
                   COALESCE(SUM(total_copies), 0),
                   COALESCE(SUM(available_copies), 0)
            FROM library_books;
            """
        )
        total_titles, total_copies, available_copies = cursor.fetchone()

        cursor.execute("SELECT COUNT(*) FROM book_loans WHERE status = 'ISSUED';")
        active_loans = cursor.fetchone()[0]

        today_str = date.today().isoformat()
        cursor.execute(
            "SELECT COUNT(*) FROM book_loans WHERE status = 'ISSUED' AND due_date < ?;",
            (today_str,),
        )
        overdue_loans = cursor.fetchone()[0]

        cursor.execute("SELECT COALESCE(SUM(fine_amount), 0.0) FROM book_loans;")
        total_fines = cursor.fetchone()[0]

        cursor.close()
        return {
            "total_titles": total_titles,
            "total_copies": total_copies,
            "available_copies": available_copies,
            "active_loans": active_loans,
            "overdue_loans": overdue_loans,
            "total_fines_collected": round(float(total_fines), 2),
        }
