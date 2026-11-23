from sqlalchemy import select

from app.db.init_db import create_tables
from app.db.session import SessionLocal
from app.models import Shop, User

TEST_OWNER_PHONE = "+905550000002"
TEST_OWNER_EMAIL = "shop-owner@kahvecell.local"
TEST_SHOP_NAME = "Coffee Lab Bah\u00e7elievler"


def main() -> None:
    create_tables()
    with SessionLocal.begin() as session:
        owner = session.scalar(
            select(User).where(User.phone_number == TEST_OWNER_PHONE)
        )
        if owner is None:
            owner = User(
                phone_number=TEST_OWNER_PHONE,
                full_name="Test Dukkan Sahibi",
                email=TEST_OWNER_EMAIL,
                role="SHOP_OWNER",
                is_verified=True,
                profile_completed=True,
            )
            session.add(owner)
            session.flush()
        elif owner.role != "SHOP_OWNER":
            raise RuntimeError(
                f"{TEST_OWNER_PHONE} is already registered with a different role."
            )

        shop = session.scalar(select(Shop).where(Shop.name == TEST_SHOP_NAME))
        if shop is None:
            raise RuntimeError(
                "Test shop is missing. Run seed_data.py before this script."
            )
        if shop.owner_user_id not in (None, owner.id):
            raise RuntimeError("The test shop is already assigned to another owner.")
        shop.owner_user_id = owner.id

    print("Test shop-owner account is ready.")
    print(f"Phone: {TEST_OWNER_PHONE}")
    print("Login with the simulated OTP: 1234")
    print(f"Assigned shop: {TEST_SHOP_NAME}")


if __name__ == "__main__":
    main()
