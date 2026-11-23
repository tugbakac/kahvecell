from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.orm import configure_mappers

from app.db.session import engine
from app.main import app


def test_startup_creates_sqlite_tables_and_relationships() -> None:
    configure_mappers()

    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200

    inspector = inspect(engine)
    assert set(inspector.get_table_names()) == {
        "users",
        "subscriptions",
        "shops",
        "products",
        "orders",
        "payments",
    }
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    assert {
        "password_hash",
        "is_verified",
        "profile_completed",
        "public_id",
    } <= user_columns
    assert "public_id" in {column["name"] for column in inspector.get_columns("shops")}
    assert "public_id" in {column["name"] for column in inspector.get_columns("orders")}
    assert {
        foreign_key["referred_table"]
        for foreign_key in inspector.get_foreign_keys("orders")
    } == {"users", "shops", "products", "subscriptions"}
    assert {
        foreign_key["referred_table"]
        for foreign_key in inspector.get_foreign_keys("payments")
    } == {"users", "subscriptions"}

    with engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
