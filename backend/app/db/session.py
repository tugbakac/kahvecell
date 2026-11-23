import os
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import URL, create_engine, event, make_url
from sqlalchemy.orm import Session, sessionmaker

DATABASE_PATH = Path(__file__).resolve().parents[2] / "data" / "kahvecell.db"


def resolve_database_url(
    configured_url: str | None,
    local_database_path: Path = DATABASE_PATH,
) -> URL:
    if not configured_url:
        local_database_path.parent.mkdir(parents=True, exist_ok=True)
        return URL.create("sqlite", database=str(local_database_path))

    url = make_url(configured_url)
    if url.drivername in {"postgres", "postgresql"}:
        return url.set(drivername="postgresql+psycopg")
    return url


DATABASE_URL = resolve_database_url(os.getenv("DATABASE_URL"))
engine_options = {"pool_pre_ping": True}
connect_args = {}
if DATABASE_URL.get_backend_name() == "sqlite":
    connect_args["check_same_thread"] = False
    engine_options["connect_args"] = connect_args

engine = create_engine(DATABASE_URL, **engine_options)

if DATABASE_URL.get_backend_name() == "sqlite":

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(connection, _record) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
