"""Database helper utilities for mapping sqlite3 rows to dictionaries."""

import sqlite3
from typing import Any, Dict, Iterable, List, Optional


def row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    """Safely convert a single sqlite3.Row instance to a Python dictionary.

    Returns None if the provided row is None.
    """
    if row is None:
        return None
    return dict(row)


def rows_to_list(rows: Optional[Iterable[sqlite3.Row]]) -> List[Dict[str, Any]]:
    """Safely convert an iterable of sqlite3.Row instances into a list of dictionaries.

    Returns an empty list if rows is None.
    """
    if rows is None:
        return []
    return [dict(r) for r in rows]
