"""Shared pytest fixtures for FakeLM tests."""

import pytest
from fastapi.testclient import TestClient

from fakellm.server.app import app


@pytest.fixture
def client() -> TestClient:
    """Provide a FastAPI TestClient instance."""
    with TestClient(app) as c:
        yield c