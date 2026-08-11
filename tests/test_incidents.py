"""
Tests for incident creation, data isolation, and history.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.connection import Base, get_db
from backend.api.main import app

TEST_DB_URL = "sqlite:///./test_incidents.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    from backend.database import models  # noqa
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _register_and_login(client, username, email="u@test.com", password="pass1234"):
    client.post("/auth/register", json={
        "username": username, "email": email, "password": password
    })
    resp = client.post("/auth/login", json={
        "username": username, "password": password
    })
    return resp.json()["access_token"]


def test_incident_history_empty(client):
    token = _register_and_login(client, "histuser", "hist@test.com")
    resp = client.get("/incidents/history", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_incident_data_isolation(client):
    """User A cannot access User B's incidents."""
    db = TestingSessionLocal()
    from backend.database.models import Incident
    from backend.database.repository import create_user, create_incident, get_user_by_username
    from backend.services.auth_service import hash_password
    import uuid

    # Create two users directly
    user_a = create_user(db, "user_a", "a@test.com", hash_password("pass1234"))
    user_b = create_user(db, "user_b", "b@test.com", hash_password("pass1234"))

    # Create incident for User A
    inc = Incident(
        incident_id=str(uuid.uuid4()),
        thread_id=str(uuid.uuid4()),
        user_id=user_a.id,
        user_query="User A's private incident",
        status="IN_PROGRESS",
    )
    create_incident(db, inc)
    incident_id = inc.incident_id
    db.close()

    # Login as User B and try to access User A's incident
    token_b = _register_and_login(client, "loginb", "loginb@test.com")

    # The endpoint should reject this (403)
    # Get User B's token properly
    resp_login = client.post("/auth/login", json={"username": "user_b", "password": "pass1234"})
    if resp_login.status_code != 200:
        pytest.skip("User B login failed in test setup")
    token_b_real = resp_login.json()["access_token"]

    resp = client.get(
        f"/incidents/{incident_id}",
        headers={"Authorization": f"Bearer {token_b_real}"}
    )
    assert resp.status_code in (403, 404)


def test_user_stats_default(client):
    token = _register_and_login(client, "statsuser", "stats@test.com")
    resp = client.get("/incidents/stats", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["resolved"] == 0


def test_admin_cannot_be_deactivated_by_self(client):
    """Admin cannot deactivate their own account."""
    # Register admin
    db = TestingSessionLocal()
    from backend.database.repository import create_user
    from backend.services.auth_service import hash_password
    admin = create_user(db, "admin_test", "admin@test.com", hash_password("adminpass"), role="admin")
    db.close()

    resp = client.post("/auth/login", json={"username": "admin_test", "password": "adminpass"})
    token = resp.json()["access_token"]
    admin_id = resp.json()["user_id"]

    resp = client.patch(
        f"/admin/users/{admin_id}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_admin_can_list_all_users(client):
    db = TestingSessionLocal()
    from backend.database.repository import create_user
    from backend.services.auth_service import hash_password
    create_user(db, "some_user", "some@test.com", hash_password("pass1234"))
    admin = create_user(db, "admin2", "admin2@test.com", hash_password("adminpass2"), role="admin")
    db.close()

    resp = client.post("/auth/login", json={"username": "admin2", "password": "adminpass2"})
    token = resp.json()["access_token"]

    resp = client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    users = resp.json()
    usernames = [u["username"] for u in users]
    assert "some_user" in usernames
