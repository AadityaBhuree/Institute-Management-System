"""Global Pytest Configuration and Test Fixtures.
Ensures an isolated, clean SQLite database for each test session and RBAC test client fixtures.
"""

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def setup_test_db(tmp_path_factory):
    """Isolate tests into a temporary database file."""
    temp_dir = tmp_path_factory.mktemp("test_db")
    test_db = temp_dir / "test_institute.db"
    os.environ["IMS_DB_PATH"] = str(test_db)
    os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-session-only")
    os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

    # Re-initialize config and schema
    import src.core.config as config

    config.DB_PATH = test_db
    config.DATABASE_URL = f"sqlite:///{test_db}"

    from src.database.init_db import init_database

    init_database(test_db)
    yield test_db


@pytest.fixture(scope="session")
def client(setup_test_db):
    """Session-scoped FastAPI test client authenticated as admin by default."""
    from src.app import app
    from src.core.security import SESSION_COOKIE_NAME, create_session_token

    admin_token = create_session_token(user_id=1, username="admin", role="admin")
    with TestClient(app) as test_client:
        test_client.cookies.set(SESSION_COOKIE_NAME, admin_token)
        yield test_client


@pytest.fixture
def anon_client(setup_test_db):
    """Unauthenticated test client for permission and authentication boundary testing."""
    from src.app import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def student_client(setup_test_db):
    """Test client authenticated with student role."""
    from src.app import app
    from src.core.security import SESSION_COOKIE_NAME, create_session_token

    student_token = create_session_token(user_id=3, username="student", role="student")
    with TestClient(app) as test_client:
        test_client.cookies.set(SESSION_COOKIE_NAME, student_token)
        yield test_client


@pytest.fixture
def faculty_client(setup_test_db):
    """Test client authenticated with faculty role."""
    from src.app import app
    from src.core.security import SESSION_COOKIE_NAME, create_session_token

    faculty_token = create_session_token(user_id=2, username="faculty", role="faculty")
    with TestClient(app) as test_client:
        test_client.cookies.set(SESSION_COOKIE_NAME, faculty_token)
        yield test_client
