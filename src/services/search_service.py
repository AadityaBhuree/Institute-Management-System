"""High-Performance SQLite FTS5 Full-Text Omnisearch Service.
Executes sub-millisecond BM25 ranked global queries across students,
faculty, courses, library catalog, and campus announcements.
"""

import re
import sqlite3
from typing import Any, Dict, List, Optional


class SearchService:
    """Institutional global omnisearch engine powered by SQLite FTS5."""

    @staticmethod
    def sanitize_query(raw_query: str) -> str:
        """Sanitize raw user query into safe FTS5 prefix-matching tokens.
        Strips control characters, unescaped quotes, and punctuation that
        could trigger SQLite FTS5 query syntax errors.
        """
        if not raw_query:
            return ""
        # Extract alphanumeric words (including accented characters/underscores)
        tokens = re.findall(r"\w+", raw_query, flags=re.UNICODE)
        if not tokens:
            return ""
        # Format tokens as FTS5 prefix matches: "token"*
        return " ".join(f'"{t}"*' for t in tokens)

    @classmethod
    def global_search(
        cls,
        conn: sqlite3.Connection,
        query: str,
        category: Optional[str] = None,
        limit: int = 20,
        user_role: str = "admin",
    ) -> Dict[str, Any]:
        """Execute unified ranked search across institutional domains."""
        sanitized = cls.sanitize_query(query)
        if not sanitized:
            return {
                "query": query,
                "total": 0,
                "categories": {
                    "STUDENT": 0,
                    "FACULTY": 0,
                    "COURSE": 0,
                    "BOOK": 0,
                    "ANNOUNCEMENT": 0,
                },
                "results": [],
            }

        cat_upper = category.upper() if category else "ALL"
        all_results: List[Dict[str, Any]] = []
        counts: Dict[str, int] = {
            "STUDENT": 0,
            "FACULTY": 0,
            "COURSE": 0,
            "BOOK": 0,
            "ANNOUNCEMENT": 0,
        }

        # Query helper safely handling empty FTS virtual tables
        cur = conn.cursor()

        # 1. Students Search (Admins & Faculty)
        if (cat_upper in ("ALL", "STUDENT")) and (user_role in ("admin", "faculty")):
            try:
                cur.execute(
                    """
                    SELECT student_id, enrollment_no, name, email, status,
                           snippet(fts_students, 2, '<mark>', '</mark>', '...', 8) AS match_snippet,
                           rank
                    FROM fts_students
                    WHERE fts_students MATCH ?
                    ORDER BY rank
                    LIMIT ?;
                    """,
                    (sanitized, limit),
                )
                for r in cur.fetchall():
                    item = {
                        "id": r["student_id"],
                        "category": "STUDENT",
                        "title": r["name"],
                        "subtitle": f"{r['enrollment_no']} • {r['status']}",
                        "snippet": r["match_snippet"] or r["email"],
                        "url": f"/students?search={r['enrollment_no']}",
                        "rank": r["rank"],
                    }
                    all_results.append(item)
                    counts["STUDENT"] += 1
            except Exception:
                pass

        # 2. Faculty Directory Search
        if cat_upper in ("ALL", "FACULTY"):
            try:
                cur.execute(
                    """
                    SELECT faculty_id_col, faculty_code, name, email, designation,
                           snippet(fts_faculty, 2, '<mark>', '</mark>', '...', 8) AS match_snippet,
                           rank
                    FROM fts_faculty
                    WHERE fts_faculty MATCH ?
                    ORDER BY rank
                    LIMIT ?;
                    """,
                    (sanitized, limit),
                )
                for r in cur.fetchall():
                    item = {
                        "id": r["faculty_id_col"],
                        "category": "FACULTY",
                        "title": r["name"],
                        "subtitle": f"{r['designation']} • {r['faculty_code']}",
                        "snippet": r["match_snippet"] or r["email"],
                        "url": "/faculty",
                        "rank": r["rank"],
                    }
                    all_results.append(item)
                    counts["FACULTY"] += 1
            except Exception:
                pass

        # 3. Courses Catalog Search
        if cat_upper in ("ALL", "COURSE"):
            try:
                cur.execute(
                    """
                    SELECT course_id, code, title, syllabus_summary,
                           snippet(fts_courses, 2, '<mark>', '</mark>', '...', 8) AS match_snippet,
                           rank
                    FROM fts_courses
                    WHERE fts_courses MATCH ?
                    ORDER BY rank
                    LIMIT ?;
                    """,
                    (sanitized, limit),
                )
                for r in cur.fetchall():
                    item = {
                        "id": r["course_id"],
                        "category": "COURSE",
                        "title": r["title"],
                        "subtitle": f"Code: {r['code']}",
                        "snippet": r["match_snippet"] or r["syllabus_summary"],
                        "url": "/courses",
                        "rank": r["rank"],
                    }
                    all_results.append(item)
                    counts["COURSE"] += 1
            except Exception:
                pass

        # 4. Library Monograph Catalog Search
        if cat_upper in ("ALL", "BOOK"):
            try:
                cur.execute(
                    """
                    SELECT book_id, isbn, title, author, category, publisher,
                           snippet(fts_library_books, 2, '<mark>', '</mark>', '...', 8) AS match_snippet,
                           rank
                    FROM fts_library_books
                    WHERE fts_library_books MATCH ?
                    ORDER BY rank
                    LIMIT ?;
                    """,
                    (sanitized, limit),
                )
                for r in cur.fetchall():
                    item = {
                        "id": r["book_id"],
                        "category": "BOOK",
                        "title": r["title"],
                        "subtitle": f"By {r['author']} • ISBN {r['isbn']}",
                        "snippet": r["match_snippet"] or r["category"],
                        "url": "/library",
                        "rank": r["rank"],
                    }
                    all_results.append(item)
                    counts["BOOK"] += 1
            except Exception:
                pass

        # 5. Campus Announcements Search
        if cat_upper in ("ALL", "ANNOUNCEMENT"):
            try:
                cur.execute(
                    """
                    SELECT announcement_id, title, content, category, target_audience,
                           snippet(fts_announcements, 2, '<mark>', '</mark>', '...', 8) AS match_snippet,
                           rank
                    FROM fts_announcements
                    WHERE fts_announcements MATCH ?
                    ORDER BY rank
                    LIMIT ?;
                    """,
                    (sanitized, limit),
                )
                for r in cur.fetchall():
                    # Filter audience permissions
                    aud = r["target_audience"]
                    if user_role == "student" and aud not in ("ALL", "STUDENTS"):
                        continue
                    if user_role == "faculty" and aud not in ("ALL", "FACULTY"):
                        continue

                    item = {
                        "id": r["announcement_id"],
                        "category": "ANNOUNCEMENT",
                        "title": r["title"],
                        "subtitle": f"Category: {r['category']}",
                        "snippet": r["match_snippet"] or r["content"][:120],
                        "url": "/announcements",
                        "rank": r["rank"],
                    }
                    all_results.append(item)
                    counts["ANNOUNCEMENT"] += 1
            except Exception:
                pass

        cur.close()

        # Sort combined results by BM25 rank score (ascending, since lower rank score = closer match in SQLite FTS5)
        all_results.sort(key=lambda x: x.get("rank", 0.0))
        trimmed_results = all_results[:limit]

        # Strip internal rank score before returning
        for res in trimmed_results:
            res.pop("rank", None)

        return {
            "query": query,
            "total": len(trimmed_results),
            "categories": counts,
            "results": trimmed_results,
        }
