import base64
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from getpass import getpass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.init_db import create_tables
from app.db.session import SessionLocal
from app.models import Product, Shop, Subscription, User

DEMO_PHONE_NUMBER = "+905550000001"
DEMO_EMAIL = "demo@kahvecell.local"
PASSWORD_HASH_ITERATIONS = 600_000

# Shop coordinates are from OpenStreetMap; menu prices are illustrative demo values.
SHOPS = [
    {
        "name": "Simit D\u00fcnyas\u0131",
        "address": "Gazi Mustafa Kemal Bulvar\u0131, K\u0131z\u0131lay Mahallesi, \u00c7ankaya, Ankara",
        "latitude": 39.9224626,
        "longitude": 32.8509483,
        "opening_hours": {"weekdays": "07:30-21:00", "weekends": "08:00-21:00"},
        "products": [
            ("Espresso", "Tek shot espresso", "95.00"),
            ("Americano", "Espresso ve s\u0131cak su", "125.00"),
            (
                "Cappuccino",
                "Espresso, s\u00fct ve s\u00fct k\u00f6p\u00fc\u011f\u00fc",
                "155.00",
            ),
            ("T\u00fcrk Kahvesi", "Geleneksel T\u00fcrk kahvesi", "110.00"),
        ],
    },
    {
        "name": "Kronotrop",
        "address": "Tunus Caddesi 11, Kavakl\u0131dere, \u00c7ankaya, Ankara",
        "latitude": 39.9118366,
        "longitude": 32.8564128,
        "opening_hours": {"weekdays": "08:00-22:00", "weekends": "09:00-22:00"},
        "products": [
            ("Espresso", "Tek shot espresso", "115.00"),
            ("Americano", "Espresso ve s\u0131cak su", "150.00"),
            (
                "Cappuccino",
                "Espresso, s\u00fct ve s\u00fct k\u00f6p\u00fc\u011f\u00fc",
                "170.00",
            ),
            ("T\u00fcrk Kahvesi", "Geleneksel T\u00fcrk kahvesi", "135.00"),
        ],
    },
    {
        "name": "Coffee Lab Bah\u00e7elievler",
        "address": "A\u015fkabat Caddesi (7. Cadde), Yukar\u0131 Bah\u00e7elievler, \u00c7ankaya, Ankara",
        "latitude": 39.9194687,
        "longitude": 32.8273582,
        "opening_hours": {"weekdays": "08:00-23:00", "weekends": "09:00-23:00"},
        "products": [
            ("Espresso", "Tek shot espresso", "105.00"),
            ("Americano", "Espresso ve s\u0131cak su", "140.00"),
            (
                "Cappuccino",
                "Espresso, s\u00fct ve s\u00fct k\u00f6p\u00fc\u011f\u00fc",
                "165.00",
            ),
            ("T\u00fcrk Kahvesi", "Geleneksel T\u00fcrk kahvesi", "120.00"),
        ],
    },
    {
        "name": "Starbucks \u00c7ayyolu",
        "address": "Ankaral\u0131lar Caddesi, Koru Mahallesi, \u00c7ayyolu, \u00c7ankaya, Ankara",
        "latitude": 39.9009315,
        "longitude": 32.6913224,
        "opening_hours": {"weekdays": "08:00-22:00", "weekends": "09:00-22:00"},
        "products": [
            ("Espresso", "Tek shot espresso", "120.00"),
            ("Americano", "Espresso ve s\u0131cak su", "155.00"),
            (
                "Cappuccino",
                "Espresso, s\u00fct ve s\u00fct k\u00f6p\u00fc\u011f\u00fc",
                "180.00",
            ),
            (
                "Caff\u00e8 Latte",
                "Espresso ve buharda \u0131s\u0131t\u0131lm\u0131\u015f s\u00fct",
                "185.00",
            ),
        ],
    },
    {
        "name": "Arabica Coffee House Mebusevleri",
        "address": "An\u0131t Caddesi 2/A, Mebusevleri, \u00c7ankaya, Ankara",
        "latitude": 39.9347013,
        "longitude": 32.8365557,
        "opening_hours": {"weekdays": "08:00-22:00", "weekends": "09:00-22:00"},
        "products": [
            ("Espresso", "Tek shot espresso", "105.00"),
            ("Americano", "Espresso ve s\u0131cak su", "140.00"),
            (
                "Cappuccino",
                "Espresso, s\u00fct ve s\u00fct k\u00f6p\u00fc\u011f\u00fc",
                "165.00",
            ),
            ("T\u00fcrk Kahvesi", "Geleneksel T\u00fcrk kahvesi", "120.00"),
        ],
    },
]


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
    )
    salt_text = base64.urlsafe_b64encode(salt).decode("ascii").rstrip("=")
    key_text = base64.urlsafe_b64encode(derived_key).decode("ascii").rstrip("=")
    return f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}${salt_text}${key_text}"


def seed_demo_data(session: Session, password: str) -> None:
    for shop_data in SHOPS:
        shop = session.scalar(select(Shop).where(Shop.name == shop_data["name"]))
        if shop is None:
            shop = Shop(name=shop_data["name"], address=shop_data["address"])
            session.add(shop)

        shop.address = shop_data["address"]
        shop.latitude = shop_data["latitude"]
        shop.longitude = shop_data["longitude"]
        shop.opening_hours = shop_data["opening_hours"]
        shop.is_active = True
        session.flush()

        for product_name, description, price in shop_data["products"]:
            product = session.scalar(
                select(Product).where(
                    Product.shop_id == shop.id,
                    Product.name == product_name,
                )
            )
            if product is None:
                product = Product(
                    shop_id=shop.id,
                    name=product_name,
                    price=Decimal(price),
                )
                session.add(product)

            product.description = description
            product.price = Decimal(price)
            product.is_available = True

    user = session.scalar(select(User).where(User.phone_number == DEMO_PHONE_NUMBER))
    if user is None:
        user = User(
            phone_number=DEMO_PHONE_NUMBER,
            full_name="Demo Kullan\u0131c\u0131s\u0131",
            email=DEMO_EMAIL,
            role="CUSTOMER",
        )
        session.add(user)

    user.full_name = "Demo Kullan\u0131c\u0131s\u0131"
    user.email = DEMO_EMAIL
    user.role = "CUSTOMER"
    user.password_hash = hash_password(password)
    user.is_verified = True
    user.profile_completed = True
    session.flush()

    subscription = session.scalar(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.plan_type == "STARTER",
            Subscription.status == "ACTIVE",
        )
    )
    now = datetime.now(UTC).replace(tzinfo=None)
    if subscription is None:
        subscription = Subscription(
            user_id=user.id,
            plan_type="STARTER",
            monthly_price=Decimal("89.99"),
            monthly_credit_limit=10,
            remaining_credits=10,
            status="ACTIVE",
        )
        session.add(subscription)

    subscription.monthly_price = Decimal("89.99")
    subscription.monthly_credit_limit = 10
    subscription.remaining_credits = 10
    subscription.started_at = now
    subscription.expires_at = now + timedelta(days=30)


def main() -> None:
    password = getpass("Demo kullanici sifresi: ")
    if not password:
        raise SystemExit("Sifre bos birakilamaz.")
    if len(password) < 10:
        raise SystemExit("Sifre en az 10 karakter olmalidir.")

    create_tables()
    with SessionLocal.begin() as session:
        seed_demo_data(session, password)

    print("Seed verileri hazir.")
    print(f"Demo telefon: {DEMO_PHONE_NUMBER}")
    print("Abonelik: STARTER, aktif, 10 kahve hakki")
    print(
        "Menu fiyatlari ornek/test fiyatlaridir; resmi guncel menu fiyatlari degildir."
    )


if __name__ == "__main__":
    main()
