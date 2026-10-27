"""Database connection manager, connection pool, and session context for SQLite.
Enforces WAL mode, foreign keys, dictionary row mapping, and high-performance connection pooling.
"""

import queue
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, Optional

import src.core.config as config


class SQLiteConnectionPool:
    """Thread-safe connection pool for SQLite connections.

    Reuses open connections across requests to eliminate file handle thrashing,
    journal initialization latency, and recurring PRAGMA executions.
    """

    def __init__(self, max_connections_per_db: int = 15, timeout: float = 30.0):
        self.max_connections = max_connections_per_db
        self.timeout = timeout
        self._pools: Dict[str, queue.Queue[sqlite3.Connection]] = {}
        self._allocated: Dict[str, int] = {}
        self._lock = threading.Lock()

    def _resolve_target_path(self, db_path: Path | str | None = None) -> str:
        target = Path(db_path) if db_path else config.DB_PATH
        return str(target.resolve())

    def _create_raw_connection(self, path_str: str) -> sqlite3.Connection:
        target_path = Path(path_str)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(
            path_str,
            check_same_thread=False,
            timeout=10.0,
            isolation_level=None,  # autocommit mode / explicit transaction management
        )
        conn.row_factory = sqlite3.Row

        # Enforce SQLite enterprise pragmas
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute("PRAGMA journal_mode = WAL;")
        cursor.execute("PRAGMA synchronous = NORMAL;")
        cursor.execute("PRAGMA busy_timeout = 5000;")
        cursor.close()
        return conn

    def acquire(self, db_path: Path | str | None = None) -> sqlite3.Connection:
        """Acquire a healthy SQLite connection from the pool or create a new one."""
        path_str = self._resolve_target_path(db_path)

        with self._lock:
            if path_str not in self._pools:
                self._pools[path_str] = queue.Queue(maxsize=self.max_connections)
                self._allocated[path_str] = 0
            pool_q = self._pools[path_str]

            # Try to retrieve an idle connection from the pool
            while not pool_q.empty():
                try:
                    conn = pool_q.get_nowait()
                    # Check if connection is still alive
                    try:
                        conn.execute("SELECT 1;")
                        return conn
                    except Exception:
                        self._allocated[path_str] = max(0, self._allocated[path_str] - 1)
                        continue
                except queue.Empty:
                    break

            # If capacity allows, allocate a new pooled connection
            if self._allocated[path_str] < self.max_connections:
                conn = self._create_raw_connection(path_str)
                self._allocated[path_str] += 1
                return conn

        # Capacity reached: wait for connection release
        try:
            return pool_q.get(timeout=self.timeout)
        except queue.Empty:
            # Fallback on pool congestion: create transient connection
            return self._create_raw_connection(path_str)

    def release(
        self, conn: Optional[sqlite3.Connection], db_path: Path | str | None = None
    ) -> None:
        """Return a connection to the pool after rolling back any unfinished transactions."""
        if conn is None:
            return

        try:
            if conn.in_transaction:
                conn.rollback()
        except Exception:
            pass

        path_str = self._resolve_target_path(db_path)
        with self._lock:
            if path_str not in self._pools:
                try:
                    conn.close()
                except Exception:
                    pass
                return

            pool_q = self._pools[path_str]
            try:
                pool_q.put_nowait(conn)
            except queue.Full:
                try:
                    conn.close()
                except Exception:
                    pass
                self._allocated[path_str] = max(0, self._allocated[path_str] - 1)

    def close_all(self) -> None:
        """Close and discard all pooled database connections."""
        with self._lock:
            for path_str, pool_q in self._pools.items():
                while not pool_q.empty():
                    try:
                        conn = pool_q.get_nowait()
                        conn.close()
                    except Exception:
                        pass
                self._allocated[path_str] = 0
            self._pools.clear()

    def stats(self, db_path: Path | str | None = None) -> Dict[str, Any]:
        """Return current pooling statistics."""
        path_str = self._resolve_target_path(db_path)
        with self._lock:
            allocated = self._allocated.get(path_str, 0)
            idle = self._pools[path_str].qsize() if path_str in self._pools else 0
            return {
                "db_path": path_str,
                "max_connections": self.max_connections,
                "allocated_connections": allocated,
                "idle_connections": idle,
                "busy_connections": max(0, allocated - idle),
            }


# Global singleton connection pool
pool = SQLiteConnectionPool(max_connections_per_db=15, timeout=30.0)


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Create or acquire a configured SQLite connection."""
    return pool.acquire(db_path)


def release_connection(conn: sqlite3.Connection, db_path: Path | str | None = None) -> None:
    """Release a connection back to the global pool."""
    pool.release(conn, db_path)


def close_pool() -> None:
    """Shutdown routine to close all pooled database connections."""
    pool.close_all()


def get_pool_stats(db_path: Path | str | None = None) -> Dict[str, Any]:
    """Retrieve telemetry metrics for the connection pool."""
    return pool.stats(db_path)


@contextmanager
def transaction(conn: sqlite3.Connection) -> Generator[sqlite3.Cursor, None, None]:
    """Context manager for atomic transaction block with automatic rollback on error."""
    cursor = conn.cursor()
    cursor.execute("BEGIN IMMEDIATE;")
    try:
        yield cursor
        cursor.execute("COMMIT;")
    except Exception:
        cursor.execute("ROLLBACK;")
        raise
    finally:
        cursor.close()


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI dependency for obtaining a pooled database connection."""
    conn = pool.acquire()
    try:
        yield conn
    finally:
        pool.release(conn)
