"""Password hashing, JWT issuance/verification, and the FastAPI dependencies
that guard every protected route by role.
"""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.models import Role
from backend.supabase_client import client
from ticket_router.config import config

_bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user: dict) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user["id"]),
        "role": user["role"],
        "department": user["department"],
        "iat": now,
        "exp": now + timedelta(minutes=config.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
    except jwt.PyJWTError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        ) from error


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = _decode_token(credentials.credentials)
    result = client.table("users").select("*").eq("id", int(payload["sub"])).execute()
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists"
        )
    return result.data[0]


def require_role(role: Role):
    def _dependency(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] != role.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        return user

    return _dependency


require_user = require_role(Role.USER)
require_admin = require_role(Role.ADMIN)


def require_super_admin(admin: dict = Depends(require_admin)) -> dict:
    if admin["department"] is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Super-admin access required"
        )
    return admin
