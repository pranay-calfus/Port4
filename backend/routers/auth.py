import secrets

from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth import create_access_token, get_current_user
from backend.models import Role
from backend.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from backend.services import ticket_service
from backend.supabase_client import client
from ticket_router.logger import logger

router = APIRouter(tags=["auth"])


@router.get("/auth/me", response_model=UserOut)
def me(user: dict = Depends(get_current_user)) -> dict:
    # Works for either role - used by the frontend to restore a session
    # from a persisted token (e.g. after a browser refresh) without the
    # caller needing to know in advance whether it's a user or admin token.
    return user


@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest) -> TokenResponse:
    try:
        user = ticket_service.create_user(
            client,
            name=payload.name,
            email=payload.email,
            password=payload.password,
            role=Role.USER,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error

    return TokenResponse(access_token=create_access_token(user), user=user)


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    user = ticket_service.authenticate(client, payload.email, payload.password, role=Role.USER)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password"
        )
    return TokenResponse(access_token=create_access_token(user), user=user)


@router.post("/admin/login", response_model=TokenResponse)
def admin_login(payload: LoginRequest) -> TokenResponse:
    user = ticket_service.authenticate(client, payload.email, payload.password, role=Role.ADMIN)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password"
        )
    return TokenResponse(access_token=create_access_token(user), user=user)


@router.post("/product-cx/login", response_model=TokenResponse)
def product_cx_login(payload: LoginRequest) -> TokenResponse:
    user = ticket_service.authenticate(
        client, payload.email, payload.password, role=Role.PRODUCT_CX
    )
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
def forgot_password(payload: ForgotPasswordRequest) -> dict:
    # Placeholder: no email delivery is wired up yet. A real reset token is
    # generated and logged server-side so the flow is testable end-to-end;
    # wiring up an email provider is a follow-up. Always returns the same
    # generic response regardless of whether the email exists, so this
    # endpoint can't be used to enumerate registered accounts.
    user = ticket_service.get_user_by_email(client, payload.email)
    if user is not None and user["role"] == Role.USER.value:
        reset_token = secrets.token_urlsafe(32)
        logger.info(
            "Password reset requested", {"email": payload.email, "reset_token": reset_token}
        )
    return {"message": "If an account with that email exists, a reset link has been sent."}
