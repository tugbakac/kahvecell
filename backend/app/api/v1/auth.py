from collections.abc import Callable
from typing import Annotated, NoReturn

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    ACCESS_TOKEN_MINUTES,
    REFRESH_TOKEN_DAYS,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.db.session import get_db
from app.models import User
from app.schemas.auth import (
    ProfileUpdateRequest,
    RefreshRequest,
    RegisterRequest,
    VerifyOTPRequest,
)

router = APIRouter(prefix="/auth", tags=["Kimlik doğrulama"])
bearer_scheme = HTTPBearer(auto_error=False)
SIMULATED_OTP = "1234"


def _success(data: dict[str, object]) -> dict[str, object]:
    return {"success": True, "data": data, "error": None}


def _raise_auth_error(status_code: int, code: str, message: str) -> NoReturn:
    raise HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
        headers={"WWW-Authenticate": "Bearer"} if status_code == 401 else None,
    )


def _user_data(user: User) -> dict[str, object]:
    return {
        "id": user.id,
        "phone_number": user.phone_number,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "profile_completed": user.profile_completed,
    }


def _token_data(user: User) -> dict[str, object]:
    return {
        "access_token": create_access_token(user.id, user.role),
        "refresh_token": create_refresh_token(user.id, user.role),
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_MINUTES * 60,
        "refresh_expires_in": REFRESH_TOKEN_DAYS * 24 * 60 * 60,
        "user": _user_data(user),
    }


def _verified_user_from_token(token: str, expected_use: str, db: Session) -> User:
    try:
        payload = decode_token(token)
    except jwt.InvalidTokenError:
        _raise_auth_error(
            status.HTTP_401_UNAUTHORIZED,
            "INVALID_TOKEN",
            "Token gecersiz veya suresi dolmus.",
        )

    subject = payload.get("sub")
    if payload.get("token_use") != expected_use or not isinstance(subject, str):
        _raise_auth_error(
            status.HTTP_401_UNAUTHORIZED, "INVALID_TOKEN", "Token turu gecersiz."
        )
    try:
        user_id = int(subject)
    except ValueError:
        _raise_auth_error(
            status.HTTP_401_UNAUTHORIZED, "INVALID_TOKEN", "Token kullanicisi gecersiz."
        )

    user = db.get(User, user_id)
    if user is None or not user.is_verified:
        _raise_auth_error(
            status.HTTP_401_UNAUTHORIZED,
            "USER_NOT_VERIFIED",
            "Kullanici bulunamadi veya dogrulanmamis.",
        )
    return user


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None:
        _raise_auth_error(
            status.HTTP_401_UNAUTHORIZED,
            "AUTHENTICATION_REQUIRED",
            "Bearer token gerekli.",
        )
    return _verified_user_from_token(credentials.credentials, "access", db)


def require_roles(*allowed_roles: str) -> Callable[..., User]:
    def role_guard(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in allowed_roles:
            _raise_auth_error(
                status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Bu islem icin yetkiniz yok."
            )
        return user

    return role_guard


@router.post("/register")
def register(
    request: RegisterRequest, db: Annotated[Session, Depends(get_db)]
) -> dict[str, object]:
    user = db.scalar(select(User).where(User.phone_number == request.phone_number))
    if user is None:
        user = User(phone_number=request.phone_number)
        db.add(user)

    if request.full_name and not user.profile_completed:
        user.full_name = request.full_name.strip()
        user.profile_completed = True
    db.commit()
    db.refresh(user)

    return _success(
        {
            "message": "SMS OTP simule edildi.",
            "phone_number": user.phone_number,
            "otp_code": SIMULATED_OTP,
        }
    )


@router.post("/verify-otp")
def verify_otp(
    request: VerifyOTPRequest, db: Annotated[Session, Depends(get_db)]
) -> dict[str, object]:
    user = db.scalar(select(User).where(User.phone_number == request.phone_number))
    if user is None:
        _raise_auth_error(
            status.HTTP_404_NOT_FOUND,
            "REGISTRATION_REQUIRED",
            "Once GSM numaranizla kayit baslatin.",
        )
    if request.otp != SIMULATED_OTP:
        _raise_auth_error(
            status.HTTP_401_UNAUTHORIZED, "INVALID_OTP", "OTP kodu hatali."
        )

    user.is_verified = True
    if request.full_name and not user.profile_completed:
        user.full_name = request.full_name.strip()
        user.profile_completed = True
    db.commit()
    db.refresh(user)
    return _success(_token_data(user))


@router.post("/refresh")
def refresh(
    request: RefreshRequest, db: Annotated[Session, Depends(get_db)]
) -> dict[str, object]:
    user = _verified_user_from_token(request.refresh_token, "refresh", db)
    return _success(
        {
            "access_token": create_access_token(user.id, user.role),
            "refresh_token": request.refresh_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_MINUTES * 60,
            "refresh_expires_in": REFRESH_TOKEN_DAYS * 24 * 60 * 60,
            "user": _user_data(user),
        }
    )


@router.get("/me")
def read_current_user(
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, object]:
    return _success(_user_data(user))


@router.patch("/me")
def update_current_user(
    request: ProfileUpdateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    fields = request.model_fields_set
    if "full_name" in fields and request.full_name is not None:
        user.full_name = request.full_name
        user.profile_completed = True
    if "email" in fields:
        if request.email is not None:
            existing_user = db.scalar(
                select(User).where(User.email == request.email, User.id != user.id)
            )
            if existing_user is not None:
                _raise_auth_error(
                    status.HTTP_409_CONFLICT,
                    "EMAIL_IN_USE",
                    "E-posta adresi kullaniliyor.",
                )
        user.email = request.email
    if "preferences" in fields:
        user.preferences = request.preferences

    db.commit()
    db.refresh(user)
    return _success(_user_data(user))
