import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth import create_access_token, get_current_user
from backend.db import get_db
from backend.models import Role, User
from backend.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from backend.services import ticket_service
from ticket_router.logger import logger

router = APIRouter(tags=["auth"])


@router.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    # Works for either role - used by the frontend to restore a session
    # from a persisted token (e.g. after a browser refresh) without the
    # caller needing to know in advance whether it's a user or admin token.
    return user


@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        user = ticket_service.create_user(
            db, name=payload.name, email=payload.email, password=payload.password, role=Role.USER
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error

    return TokenResponse(access_token=create_access_token(user), user=user)


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = ticket_service.authenticate(db, payload.email, payload.password, role=Role.USER)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password"
        )
    return TokenResponse(access_token=create_access_token(user), user=user)


@router.post("/admin/login", response_model=TokenResponse)
def admin_login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = ticket_service.authenticate(db, payload.email, payload.password, role=Role.ADMIN)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password"
        )
    return TokenResponse(access_token=create_access_token(user), user=user)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout() -> None:
    # Access tokens are stateless JWTs with a short expiry - there is no
    # server-side session to invalidate. The client is responsible for
    # discarding the token it holds.
    return None


@router.post("/auth/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)) -> dict:
    # Placeholder: no email delivery is wired up yet. A real reset token is
    # generated and logged server-side so the flow is testable end-to-end;
    # wiring up an email provider is a follow-up. Always returns the same
    # generic response regardless of whether the email exists, so this
    # endpoint can't be used to enumerate registered accounts.
    user = ticket_service.get_user_by_email(db, payload.email)
    if user is not None and user.role == Role.USER:
        reset_token = secrets.token_urlsafe(32)
        logger.info(
            "Password reset requested", {"email": payload.email, "reset_token": reset_token}
        )
    return {"message": "If an account with that email exists, a reset link has been sent."}
