from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import Order, Product, Shop, Subscription, User
from seed_data import DEMO_PHONE_NUMBER, PASSWORD_HASH_ITERATIONS, seed_demo_data


def test_seed_data_is_repeatable_and_hashes_the_demo_password() -> None:
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)

    try:
        with Session(test_engine) as session, session.begin():
            seed_demo_data(session, "AnkaraKahve123!")
            seed_demo_data(session, "AnkaraKahve123!")

            assert session.scalar(select(func.count()).select_from(Shop)) == 5
            assert session.scalar(select(func.count()).select_from(Product)) == 20
            assert session.scalar(select(func.count()).select_from(User)) == 1
            assert session.scalar(select(func.count()).select_from(Subscription)) == 1
            assert session.scalar(select(func.count()).select_from(Order)) == 0

            user = session.scalar(
                select(User).where(User.phone_number == DEMO_PHONE_NUMBER)
            )
            subscription = session.scalar(select(Subscription))
            assert user is not None
            assert user.password_hash is not None
            assert user.password_hash.startswith(
                f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}$"
            )
            assert "AnkaraKahve123!" not in user.password_hash
            assert subscription is not None
            assert subscription.plan_type == "STARTER"
            assert subscription.status == "ACTIVE"
            assert subscription.remaining_credits == 10
    finally:
        test_engine.dispose()
