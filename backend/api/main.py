"""
FastAPI application entry point.
Defines the app, middleware, auth dependency, and includes all routers.
"""
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

# Ensure project root is on sys.path when running from the AI_Incident_Management directory
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.config import get_settings
from backend.database.connection import init_db, get_db

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialize DB and optionally warm up ChromaDB."""
    logger.info("Starting AI Incident Management backend...")
    init_db()
    _ensure_admin_exists()
    logger.info("Backend ready.")
    yield
    logger.info("Backend shutting down.")


def _ensure_admin_exists():
    """Create the default admin if the users table is empty."""
    from backend.database.connection import SessionLocal
    from backend.database.repository import get_user_by_username, create_user
    from backend.services.auth_service import hash_password
    import os

    db = SessionLocal()
    try:
        admin_username = settings.admin_username
        if not get_user_by_username(db, admin_username):
            admin_password = os.environ.get("ADMIN_PASSWORD", "")
            if not admin_password:
                import secrets
                admin_password = secrets.token_urlsafe(16)
                logger.warning(
                    "=" * 60
                )
                logger.warning("ADMIN ACCOUNT CREATED")
                logger.warning("Username: %s", admin_username)
                logger.warning("Email: %s", settings.admin_email)
                logger.warning("Password: %s", admin_password)
                logger.warning("SAVE THIS PASSWORD — it will not be shown again.")
                logger.warning("=" * 60)
            create_user(
                db,
                username=admin_username,
                email=settings.admin_email,
                password_hash=hash_password(admin_password),
                role="admin",
            )
    finally:
        db.close()


# ── FastAPI app ─────────────────────────────────────────────
app = FastAPI(
    title="AI Incident Management API",
    version="1.0.0",
    description="Enterprise AI-powered IT incident management platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include routers ─────────────────────────────────────────
from backend.api import auth, incidents, admin, evaluation  # noqa: E402

app.include_router(auth.router)
app.include_router(incidents.router)
app.include_router(admin.router)
app.include_router(evaluation.router)


@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "service": "AI Incident Management API"}


@app.get("/system/health", tags=["System"])
def system_health(db=Depends(get_db)):
    """Detailed system health check."""
    from backend.api.schemas import SystemHealth

    results = {
        "backend": "online",
        "database": "unknown",
        "chromadb": "unknown",
        "llm": "unknown",
        "rag": "unknown",
    }

    # Database check
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        results["database"] = "online"
    except Exception as exc:
        results["database"] = f"error: {type(exc).__name__}"

    # ChromaDB check
    try:
        from backend.rag.vectorstore import get_vectorstore
        vs = get_vectorstore()
        # chromadb 1.x: count() is on the collection object
        try:
            count = vs._collection.count()
        except Exception:
            count = vs.get()["ids"].__len__() if vs.get() else 0
        results["chromadb"] = "online"
        results["document_count"] = count
    except Exception as exc:
        results["chromadb"] = f"error: {type(exc).__name__}"

    # LLM check
    try:
        if settings.openai_api_key:
            results["llm"] = "configured"
            results["llm_model"] = settings.llm_model
        else:
            results["llm"] = "not configured (set OPENAI_API_KEY)"
    except Exception:
        results["llm"] = "error"

    # RAG check
    results["rag"] = "online" if results["chromadb"] == "online" else "degraded"
    results["embedding_model"] = settings.embedding_model
    results["chroma_path"] = settings.absolute_chroma_path

    return SystemHealth(**results)
