"""
Root-level runner and setup script.

Usage:
    python run.py backend          - Start FastAPI backend
    python run.py frontend         - Start Streamlit frontend
    python run.py setup-admin      - Interactively set admin password
    python run.py init-db          - Initialize database only
    python run.py init-rag         - Build/rebuild ChromaDB from knowledge base
    python run.py test             - Run pytest tests
"""
import sys
import os
import subprocess
from pathlib import Path

# Project root on PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env if present (python-dotenv may not be installed yet)
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file)
    except ImportError:
        pass  # dotenv not installed yet; env vars must be set manually


def run_backend():
    print("Starting FastAPI backend on http://127.0.0.1:8000")
    os.chdir(PROJECT_ROOT)
    subprocess.run(
        [sys.executable, "-m", "uvicorn", "backend.api.main:app",
         "--reload", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(PROJECT_ROOT),
    )


def run_frontend():
    print("Starting Streamlit frontend on http://127.0.0.1:8501")
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run",
         str(PROJECT_ROOT / "frontend" / "app.py"),
         "--server.address", "127.0.0.1",
         "--server.port", "8501"],
        cwd=str(PROJECT_ROOT),
    )


def setup_admin():
    """Interactively create or update the admin account."""
    import getpass
    from backend.database.connection import SessionLocal, init_db
    from backend.database import models  # noqa
    from backend.database.repository import (
        get_user_by_username, create_user, update_user
    )
    from backend.services.auth_service import hash_password
    from backend.config import get_settings

    init_db()
    settings = get_settings()
    db = SessionLocal()

    try:
        admin_username = input(f"Admin username [{settings.admin_username}]: ").strip()
        if not admin_username:
            admin_username = settings.admin_username

        admin_email = input(f"Admin email [{settings.admin_email}]: ").strip()
        if not admin_email:
            admin_email = settings.admin_email

        while True:
            password = getpass.getpass("Admin password (min 8 chars): ")
            if len(password) < 8:
                print("Password must be at least 8 characters.")
                continue
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                print("Passwords do not match.")
                continue
            break

        existing = get_user_by_username(db, admin_username)
        if existing:
            update_user(db, existing.id,
                        password_hash=hash_password(password),
                        email=admin_email,
                        role="admin",
                        is_active=True)
            print(f"[OK] Admin account updated: {admin_username}")
        else:
            create_user(db, admin_username, admin_email, hash_password(password), role="admin")
            print(f"✅ Admin account created: {admin_username}")
    finally:
        db.close()


def init_db():
    from backend.database.connection import init_db as _init_db
    from backend.database import models  # noqa
    _init_db()
    print("[OK] Database initialized.")


def init_rag():
    from backend.rag.vectorstore import get_vectorstore
    vs = get_vectorstore(force_rebuild=True)
    print("[OK] RAG vector store built.")


def run_tests():
    subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"], cwd=str(PROJECT_ROOT))


COMMANDS = {
    "backend": run_backend,
    "frontend": run_frontend,
    "setup-admin": setup_admin,
    "init-db": init_db,
    "init-rag": init_rag,
    "test": run_tests,
}


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        print(f"Available commands: {', '.join(COMMANDS.keys())}")
        sys.exit(1)

    COMMANDS[sys.argv[1]]()
