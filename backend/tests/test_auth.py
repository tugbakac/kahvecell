import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture
def client():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        test_engine.dispose()


def test_phone_otp_registration_refresh_and_profile(client: TestClient) -> None:
    invalid_role = client.post(
        "/api/v1/auth/register",
        json={"phone_number": "05550000001", "role": "ADMIN"},
    )
    assert invalid_role.status_code == 422
    assert invalid_role.json()["error"]["code"] == "VALIDATION_ERROR"

    unauthenticated = client.get("/api/v1/auth/me")
    assert unauthenticated.status_code == 401
    assert unauthenticated.json()["success"] is False

    registration = client.post(
        "/api/v1/auth/register", json={"phone_number": "05550000001"}
    )
    assert registration.status_code == 200
    assert registration.json()["data"]["phone_number"] == "+905550000001"
    assert registration.json()["data"]["otp_code"] == "1234"

    invalid_otp = client.post(
        "/api/v1/auth/verify-otp",
        json={"phone_number": "+905550000001", "otp": "0000"},
    )
    assert invalid_otp.status_code == 401
    assert invalid_otp.json()["error"]["code"] == "INVALID_OTP"

    verification = client.post(
        "/api/v1/auth/verify-otp",
        json={"phone_number": "+905550000001", "otp": "1234"},
    )
    assert verification.status_code == 200
    token_data = verification.json()["data"]
    assert token_data["user"]["role"] == "CUSTOMER"
    assert token_data["user"]["profile_completed"] is False

    access_headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    profile = client.get("/api/v1/auth/me", headers=access_headers)
    assert profile.status_code == 200
    assert profile.json()["data"]["phone_number"] == "+905550000001"

    profile_update = client.patch(
        "/api/v1/auth/me",
        headers=access_headers,
        json={"full_name": "Test Kullanici", "preferences": {"coffee": ["espresso"]}},
    )
    assert profile_update.status_code == 200
    assert profile_update.json()["data"]["profile_completed"] is True

    refreshed = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": token_data["refresh_token"]},
    )
    assert refreshed.status_code == 200
    refreshed_token = refreshed.json()["data"]["access_token"]
    refreshed_profile = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refreshed_token}"},
    )
    assert refreshed_profile.status_code == 200
    assert refreshed_profile.json()["data"]["full_name"] == "Test Kullanici"

    rejected_access_as_refresh = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": token_data["access_token"]},
    )
    assert rejected_access_as_refresh.status_code == 401
    assert rejected_access_as_refresh.json()["error"]["code"] == "INVALID_TOKEN"


def test_auth_endpoints_are_documented_in_openapi(client: TestClient) -> None:
    openapi = client.get("/openapi.json").json()
    paths = openapi["paths"]

    assert "/api/v1/auth/register" in paths
    assert "/api/v1/auth/verify-otp" in paths
    assert "/api/v1/auth/refresh" in paths
    assert "/api/v1/auth/me" in paths
    assert "HTTPBearer" in openapi["components"]["securitySchemes"]
