from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Product, Shop


@pytest.fixture
def client():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    with Session(test_engine) as session:
        kizilay = Shop(
            name="Kizilay Kahve",
            address="Kizilay Mahallesi, Ankara",
            latitude=39.9204,
            longitude=32.8549,
            opening_hours={"weekdays": "08:00-20:00"},
            is_active=True,
        )
        bahcelievler = Shop(
            name="Bahcelievler Kahve",
            address="7. Cadde, Ankara",
            latitude=39.9194,
            longitude=32.8273,
            opening_hours={"weekdays": "09:00-21:00"},
            is_active=True,
        )
        cay_yolu = Shop(
            name="Cay Yolu Kahve",
            address="Cayyolu, Ankara",
            latitude=39.9009,
            longitude=32.6913,
            is_active=True,
        )
        inactive = Shop(
            name="Kapali Dukkan",
            address="Ankara",
            latitude=39.92,
            longitude=32.85,
            is_active=False,
        )
        session.add_all([kizilay, bahcelievler, cay_yolu, inactive])
        session.flush()
        session.add_all(
            [
                Product(
                    shop_id=kizilay.id,
                    name="Cappuccino",
                    price=Decimal("150.00"),
                    is_available=True,
                ),
                Product(
                    shop_id=kizilay.id,
                    name="Espresso",
                    price=Decimal("100.00"),
                    is_available=True,
                ),
                Product(
                    shop_id=kizilay.id,
                    name="Hidden Product",
                    price=Decimal("90.00"),
                    is_available=False,
                ),
            ]
        )
        session.commit()
        kizilay_id = kizilay.id

    def override_get_db():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client, kizilay_id
    finally:
        app.dependency_overrides.clear()
        test_engine.dispose()


def test_shop_list_search_distance_and_radius(client) -> None:
    test_client, _ = client

    openapi = test_client.get("/openapi.json").json()
    assert "/api/v1/shops" in openapi["paths"]
    assert "/api/v1/shops/{shop_id}" in openapi["paths"]
    assert "/api/v1/shops/{shop_id}/menu" in openapi["paths"]

    all_shops = test_client.get("/api/v1/shops")
    assert all_shops.status_code == 200
    assert len(all_shops.json()["data"]) == 3
    assert all(shop["distance_km"] is None for shop in all_shops.json()["data"])

    searched = test_client.get("/api/v1/shops?q=KIZILAY")
    assert [shop["name"] for shop in searched.json()["data"]] == ["Kizilay Kahve"]

    nearby = test_client.get(
        "/api/v1/shops",
        params={"lat": 39.9204, "lng": 32.8549},
    )
    nearby_shops = nearby.json()["data"]
    assert [shop["name"] for shop in nearby_shops] == [
        "Kizilay Kahve",
        "Bahcelievler Kahve",
        "Cay Yolu Kahve",
    ]
    assert nearby_shops[0]["distance_km"] == 0
    assert nearby_shops[0]["distance_km"] < nearby_shops[1]["distance_km"]

    within_radius = test_client.get(
        "/api/v1/shops",
        params={"lat": 39.9204, "lng": 32.8549, "radius_km": 5},
    )
    assert len(within_radius.json()["data"]) == 2

    incomplete_location = test_client.get("/api/v1/shops", params={"lat": 39.9204})
    assert incomplete_location.status_code == 422
    assert incomplete_location.json()["error"]["code"] == "INCOMPLETE_LOCATION"


def test_shop_detail_includes_available_menu(client) -> None:
    test_client, shop_id = client

    detail = test_client.get(f"/api/v1/shops/{shop_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["name"] == "Kizilay Kahve"
    assert [item["name"] for item in detail.json()["data"]["menu"]] == [
        "Cappuccino",
        "Espresso",
    ]

    detail_with_location = test_client.get(
        f"/api/v1/shops/{shop_id}",
        params={"lat": 39.9204, "lng": 32.8549},
    )
    assert detail_with_location.json()["data"]["distance_km"] == 0

    menu = test_client.get(f"/api/v1/shops/{shop_id}/menu")
    assert menu.status_code == 200
    assert menu.json()["data"]["products"][0]["price"] == 150

    missing_shop = test_client.get("/api/v1/shops/9999")
    assert missing_shop.status_code == 404
    assert missing_shop.json()["error"]["code"] == "SHOP_NOT_FOUND"
