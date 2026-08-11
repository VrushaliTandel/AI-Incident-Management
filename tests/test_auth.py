"""
Tests for authentication flows.
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

# ── In-memory SQLite for tests ───────────────────────────────
TEST_DB_URL = "sqlite:///./test_auth.db"
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


def test_register_success(client):
    resp = client.post("/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "securepass",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "testuser"
    assert data["role"] == "user"


def test_register_duplicate_username(client):
    client.post("/auth/register", json={
        "username": "dup", "email": "dup@test.com", "password": "pass1234"
    })
    resp = client.post("/auth/register", json={
        "username": "dup", "email": "dup2@test.com", "password": "pass1234"
    })
    assert resp.status_code == 400


def test_login_success(client):
    client.post("/auth/register", json={
        "username": "loginuser", "email": "login@test.com", "password": "mypassword"
    })
    resp = client.post("/auth/login", json={
        "username": "loginuser", "password": "mypassword"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["username"] == "loginuser"


def test_login_wrong_password(client):
    client.post("/auth/register", json={
        "username": "user2", "email": "u2@test.com", "password": "correct"
    })
    resp = client.post("/auth/login", json={
        "username": "user2", "password": "wrong"
    })
    assert resp.status_code == 401


def test_login_by_email(client):
    client.post("/auth/register", json={
        "username": "emailuser", "email": "emaillogin@test.com", "password": "pass1234"
    })
    resp = client.post("/auth/login", json={
        "username": "emaillogin@test.com", "password": "pass1234"
    })
    assert resp.status_code == 200


def test_get_me_authenticated(client):
    client.post("/auth/register", json={
        "username": "meuser", "email": "me@test.com", "password": "pass1234"
    })
    login = client.post("/auth/login", json={
        "username": "meuser", "password": "pass1234"
    }).json()
    token = login["access_token"]
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "meuser"


def test_get_me_unauthenticated(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_password_not_stored_plaintext(client):
    """Verify password is hashed in DB."""
    from backend.database.repository import get_user_by_username
    client.post("/auth/register", json={
        "username": "hashtest", "email": "hash@test.com", "password": "plaintext"
    })
    db = TestingSessionLocal()
    user = get_user_by_username(db, "hashtest")
    db.close()
    assert user.password_hash != "plaintext"
    assert "$2b$" in user.password_hash  # bcrypt
