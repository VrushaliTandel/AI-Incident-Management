"""
Authentication API router.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.repository import (
    get_user_by_username_or_email,
    get_user_by_username,
    get_user_by_email,
    create_user,
    get_user_by_id,
)
from backend.services.auth_service import hash_password, verify_password, create_access_token
from backend.api.schemas import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from backend.api.deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/check-user")
def check_user_exists(login: str, db: Session = Depends(get_db)):
    """
    Check whether a username or email exists in the database.
    Returns {"exists": true/false} — used by the frontend to show
    "Please register first" instead of "Invalid credentials".
    """
    user = get_user_by_username_or_email(db, login)
    return {"exists": user is not None}


@router.post("/register", response_model=UserResponse, status_code=201)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user account."""
    if get_user_by_username(db, request.username):
        raise HTTPException(status_code=400, detail="Username already taken")
    if get_user_by_email(db, request.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    user = create_user(
        db,
        username=request.username,
        email=request.email,
        password_hash=hash_password(request.password),
        role="user",
    )
    logger.info("New user registered: %s", user.username)
    return user


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate and return a JWT token."""
    user = get_user_by_username_or_email(db, request.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found. Please register first.",
        )
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    token = create_access_token({"sub": str(user.id), "role": user.role})
    logger.info("User logged in: %s", user.username)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
        role=user.role,
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user=Depends(get_current_user)):
    """Return the current authenticated user's profile."""
    return current_user
