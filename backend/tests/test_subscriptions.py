import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import User


@pytest.fixture
def authorized_client():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    with Session(test_engine) as session:
        session.add(
            User(
                phone_number="+905550000001",
                full_name="Test Kullanici",
                is_verified=True,
                profile_completed=True,
            )
        )
        session.commit()

    def override_get_db():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            login = test_client.post(
                "/api/v1/auth/verify-otp",
                json={"phone_number": "+905550000001", "otp": "1234"},
            )
            assert login.status_code == 200
            token = login.json()["data"]["access_token"]
            test_client.headers.update({"Authorization": f"Bearer {token}"})
            yield test_client
    finally:
        app.dependency_overrides.clear()
        test_engine.dispose()


def test_subscription_plans_purchase_upgrade_failure_and_cancel(
    authorized_client: TestClient,
) -> None:
    openapi = authorized_client.get("/openapi.json").json()
    assert "/api/v1/subscriptions/plans" in openapi["paths"]
    assert "/api/v1/subscriptions" in openapi["paths"]
    assert "/api/v1/subscriptions/me" in openapi["paths"]
    assert "/api/v1/payments/process" in openapi["paths"]
    assert "/api/v1/payments/history" in openapi["paths"]

    plans = authorized_client.get("/api/v1/subscriptions/plans")
    assert plans.status_code == 200
    assert [plan["plan_type"] for plan in plans.json()["data"]] == [
        "STARTER",
        "PREMIUM",
        "UNLIMITED",
    ]
    assert [plan["monthly_price"] for plan in plans.json()["data"]] == [
        89.99,
        149.99,
        249.99,
    ]

    purchase = authorized_client.post(
        "/api/v1/subscriptions",
        json={
            "plan_type": "STARTER",
            "card_number": "4242-4242-4242-4242",
        },
    )
    assert purchase.status_code == 200
    assert purchase.json()["data"]["payment"]["status"] == "SUCCEEDED"
    assert purchase.json()["data"]["payment"]["amount"] == 89.99
    assert purchase.json()["data"]["subscription"]["remaining_credits"] == 10
    assert purchase.json()["data"]["payment"]["card_last_four"] == "4242"

    failed_upgrade = authorized_client.patch(
        "/api/v1/subscriptions/me",
        json={
            "plan_type": "PREMIUM",
            "card_number": "4000-0000-0000-0002",
        },
    )
    assert failed_upgrade.status_code == 402
    assert failed_upgrade.json()["success"] is False
    assert failed_upgrade.json()["data"]["payment"]["status"] == "FAILED"

    active_after_decline = authorized_client.get("/api/v1/subscriptions/me")
    assert active_after_decline.json()["data"]["plan_type"] == "STARTER"
    assert active_after_decline.json()["data"]["remaining_credits"] == 10

    upgrade = authorized_client.patch(
        "/api/v1/subscriptions/me",
        json={
            "plan_type": "PREMIUM",
            "card_number": "4242-4242-4242-4242",
        },
    )
    assert upgrade.status_code == 200
    assert upgrade.json()["data"]["payment"]["amount"] == 149.99
    assert upgrade.json()["data"]["subscription"]["remaining_credits"] == 20

    payment_route = authorized_client.post(
        "/api/v1/payments/process",
        json={
            "plan_type": "UNLIMITED",
            "card_number": "4242-4242-4242-4242",
        },
    )
    assert payment_route.status_code == 200
    assert payment_route.json()["data"]["subscription"]["remaining_credits"] is None

    history = authorized_client.get("/api/v1/payments/history")
    assert history.status_code == 200
    assert [payment["status"] for payment in history.json()["data"]] == [
        "SUCCEEDED",
        "SUCCEEDED",
        "FAILED",
        "SUCCEEDED",
    ]

    cancelled = authorized_client.delete("/api/v1/subscriptions/me")
    assert cancelled.status_code == 200
    assert cancelled.json()["data"]["status"] == "CANCELLED"
    assert cancelled.json()["data"]["remaining_credits"] == 0
    assert authorized_client.get("/api/v1/subscriptions/me").json()["data"] is None
