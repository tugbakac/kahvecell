import os
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import jwt

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 15
REFRESH_TOKEN_DAYS = 30
_SECRET_FILE = Path(__file__).resolve().parents[2] / "data" / "jwt_signing_key"


def load_signing_key(secret_file: Path, environment_variable: str) -> bytes:
    environment_key = os.getenv(environment_variable)
    if environment_key:
        if len(environment_key) < 32:
            raise RuntimeError(
                f"{environment_variable} must be at least 32 characters."
            )
        return environment_key.encode("utf-8")

    secret_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        with secret_file.open("xb") as output_file:
            output_file.write(secrets.token_bytes(32))
    except FileExistsError:
        pass

    secret = secret_file.read_bytes()
    if len(secret) < 32:
        raise RuntimeError(f"Signing key file is invalid: {secret_file}")
    return secret


JWT_SECRET_KEY = load_signing_key(_SECRET_FILE, "KAHVECELL_JWT_SECRET")


def _create_token(user_id: int, role: str, token_use: str, lifetime: timedelta) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "token_use": token_use,
        "iat": now,
        "exp": now + lifetime,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_access_token(user_id: int, role: str) -> str:
    return _create_token(
        user_id,
        role,
        "access",
        timedelta(minutes=ACCESS_TOKEN_MINUTES),
    )


def create_refresh_token(user_id: int, role: str) -> str:
    return _create_token(
        user_id,
        role,
        "refresh",
        timedelta(days=REFRESH_TOKEN_DAYS),
    )


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
