from uuid import uuid4

from sqlalchemy import inspect, text

import app.models  # noqa: F401
from app.db.base import Base
from app.db.session import engine


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    existing_columns = {
        column["name"] for column in inspect(engine).get_columns("users")
    }
    new_columns = {
        "password_hash": "VARCHAR(255)",
        "is_verified": "BOOLEAN NOT NULL DEFAULT 0",
        "profile_completed": "BOOLEAN NOT NULL DEFAULT 0",
        "public_id": "VARCHAR(36)",
    }
    missing_columns = {
        name: definition
        for name, definition in new_columns.items()
        if name not in existing_columns
    }
    if missing_columns:
        with engine.begin() as connection:
            for name, definition in missing_columns.items():
                connection.execute(
                    text(f"ALTER TABLE users ADD COLUMN {name} {definition}")
                )

    for table_name in ("users", "shops", "orders"):
        columns = {column["name"] for column in inspect(engine).get_columns(table_name)}
        if "public_id" not in columns:
            with engine.begin() as connection:
                connection.execute(
                    text(f"ALTER TABLE {table_name} ADD COLUMN public_id VARCHAR(36)")
                )
        with engine.begin() as connection:
            missing_ids = connection.execute(
                text(f"SELECT id FROM {table_name} WHERE public_id IS NULL")
            ).all()
            for row in missing_ids:
                connection.execute(
                    text(
                        f"UPDATE {table_name} SET public_id = :public_id WHERE id = :id"
                    ),
                    {"public_id": str(uuid4()), "id": row.id},
                )
            connection.execute(
                text(
                    f"CREATE UNIQUE INDEX IF NOT EXISTS "
                    f"ux_{table_name}_public_id ON {table_name}(public_id)"
                )
            )
