"""Global Pytest Configuration and Test Fixtures.
Ensures an isolated, clean SQLite database for each test session.
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

    # Re-initialize config and schema
    import src.core.config as config

    config.DB_PATH = test_db
    config.DATABASE_URL = f"sqlite:///{test_db}"

    from src.database.init_db import init_database

    init_database(test_db)
    yield test_db


@pytest.fixture(scope="session")
def client(setup_test_db):
    """Session-scoped FastAPI test client."""
    from src.app import app

    with TestClient(app) as test_client:
        yield test_client
