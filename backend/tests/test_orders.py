from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Product, Shop, Subscription, User


@pytest.fixture
def order_client():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    with Session(test_engine) as session:
        customer = User(
            phone_number="+905550000011",
            full_name="Test Customer",
            role="CUSTOMER",
            is_verified=True,
            profile_completed=True,
        )
        no_subscription_customer = User(
            phone_number="+905550000012",
            full_name="No Subscription",
            role="CUSTOMER",
            is_verified=True,
            profile_completed=True,
        )
        unlimited_customer = User(
            phone_number="+905550000013",
            full_name="Unlimited Customer",
            role="CUSTOMER",
            is_verified=True,
            profile_completed=True,
        )
        owner = User(
            phone_number="+905550000014",
            full_name="Test Shop Owner",
            role="SHOP_OWNER",
            is_verified=True,
            profile_completed=True,
        )
        shop = Shop(
            owner=owner,
            name="Test Coffee Shop",
            address="Kizilay, Ankara",
            latitude=39.9204,
            longitude=32.8549,
            is_active=True,
        )
        product = Product(
            shop=shop,
            name="Cappuccino",
            price=Decimal("150.00"),
            is_available=True,
        )
        now = datetime.now(UTC).replace(tzinfo=None)
        customer_subscription = Subscription(
            user=customer,
            plan_type="STARTER",
            monthly_price=Decimal("89.99"),
            monthly_credit_limit=10,
            remaining_credits=1,
            status="ACTIVE",
            started_at=now,
            expires_at=now + timedelta(days=30),
        )
        unlimited_subscription = Subscription(
            user=unlimited_customer,
            plan_type="UNLIMITED",
            monthly_price=Decimal("249.99"),
            monthly_credit_limit=None,
            remaining_credits=None,
            status="ACTIVE",
            started_at=now,
            expires_at=now + timedelta(days=30),
        )
        session.add_all(
            [
                customer,
                no_subscription_customer,
                unlimited_customer,
                owner,
                shop,
                product,
                customer_subscription,
                unlimited_subscription,
            ]
        )
        session.commit()
        shop_id = shop.id
        product_id = product.id

    def override_get_db():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            tokens = {}
            for phone in (
                "+905550000011",
                "+905550000012",
                "+905550000013",
                "+905550000014",
            ):
                response = test_client.post(
                    "/api/v1/auth/verify-otp",
                    json={"phone_number": phone, "otp": "1234"},
                )
                assert response.status_code == 200
                tokens[phone] = response.json()["data"]["access_token"]
            yield test_client, tokens, shop_id, product_id
    finally:
        app.dependency_overrides.clear()
        test_engine.dispose()


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_order_requires_subscription_and_consumes_one_credit(order_client) -> None:
    client, tokens, shop_id, product_id = order_client
    payload = {
        "shop_id": shop_id,
        "product_id": product_id,
        "size": "L",
        "sugar_level": 2,
        "milk_type": "OAT",
        "extra_shots": 1,
    }

    no_subscription = client.post(
        "/api/v1/orders",
        headers=_headers(tokens["+905550000012"]),
        json=payload,
    )
    assert no_subscription.status_code == 403
    assert no_subscription.json()["error"]["code"] == "ACTIVE_SUBSCRIPTION_REQUIRED"

    customer_headers = _headers(tokens["+905550000011"])
    created = client.post("/api/v1/orders", headers=customer_headers, json=payload)
    assert created.status_code == 200
    result = created.json()["data"]
    assert result["order"]["status"] == "PENDING"
    assert result["remaining_credits"] == 0
    assert result["order"]["customizations"] == {
        "size": "L",
        "sugar_level": 2,
        "milk_type": "OAT",
        "extra_shots": 1,
        "notes": None,
    }
    qr_payload = result["order"]["qr_code"]
    assert set(qr_payload) == {
        "order_id",
        "user_id",
        "shop_id",
        "created_at",
        "signature",
    }
    assert len(qr_payload["signature"]) == 64
    for key in ("order_id", "user_id", "shop_id"):
        UUID(qr_payload[key])

    exhausted = client.post("/api/v1/orders", headers=customer_headers, json=payload)
    assert exhausted.status_code == 409
    assert exhausted.json()["error"]["code"] == "NO_COFFEE_CREDITS"


def test_shop_owner_tracks_order_and_validates_qr_before_delivery(order_client) -> None:
    client, tokens, shop_id, product_id = order_client
    customer_headers = _headers(tokens["+905550000011"])
    owner_headers = _headers(tokens["+905550000014"])
    created = client.post(
        "/api/v1/orders",
        headers=customer_headers,
        json={"shop_id": shop_id, "product_id": product_id},
    )
    order = created.json()["data"]["order"]
    order_id = order["id"]

    shop_orders = client.get("/api/v1/orders/shop", headers=owner_headers)
    assert shop_orders.status_code == 200
    assert shop_orders.json()["data"][0]["id"] == order_id
    assert shop_orders.json()["data"][0]["qr_code"] is None

    for next_status in ("ACCEPTED", "PREPARING", "READY"):
        response = client.patch(
            f"/api/v1/orders/{order_id}/status",
            headers=owner_headers,
            json={"status": next_status},
        )
        assert response.status_code == 200
        assert response.json()["data"]["status"] == next_status

    forged_qr = order["qr_code"].copy()
    forged_qr["shop_id"] = str(shop_id + 1)
    rejected = client.post(
        f"/api/v1/orders/{order_id}/verify-qr",
        headers=owner_headers,
        json=forged_qr,
    )
    assert rejected.status_code == 400
    assert rejected.json()["error"]["code"] == "INVALID_QR_SIGNATURE"

    delivered = client.post(
        f"/api/v1/orders/{order_id}/verify-qr",
        headers=owner_headers,
        json=order["qr_code"],
    )
    assert delivered.status_code == 200
    assert delivered.json()["data"]["status"] == "DELIVERED"

    replay = client.post(
        f"/api/v1/orders/{order_id}/verify-qr",
        headers=owner_headers,
        json=order["qr_code"],
    )
    assert replay.status_code == 409
    assert replay.json()["error"]["code"] == "QR_ALREADY_REDEEMED"

    customer_order = client.get(f"/api/v1/orders/{order_id}", headers=customer_headers)
    assert customer_order.json()["data"]["status"] == "DELIVERED"


def test_unlimited_subscription_does_not_consume_credit(order_client) -> None:
    client, tokens, shop_id, product_id = order_client
    response = client.post(
        "/api/v1/orders",
        headers=_headers(tokens["+905550000013"]),
        json={"shop_id": shop_id, "product_id": product_id},
    )
    assert response.status_code == 200
    assert response.json()["data"]["remaining_credits"] is None
