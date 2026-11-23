from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TypedDict
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import Payment, Subscription, User
from app.schemas.subscriptions import PlanType


class PlanDetails(TypedDict):
    name: str
    price: Decimal
    monthly_credits: int | None
    guest_credits: int
    priority: bool


PLAN_CATALOG: dict[PlanType, PlanDetails] = {
    "STARTER": {
        "name": "Starter",
        "price": Decimal("89.99"),
        "monthly_credits": 10,
        "guest_credits": 0,
        "priority": False,
    },
    "PREMIUM": {
        "name": "Premium",
        "price": Decimal("149.99"),
        "monthly_credits": 20,
        "guest_credits": 2,
        "priority": False,
    },
    "UNLIMITED": {
        "name": "Unlimited",
        "price": Decimal("249.99"),
        "monthly_credits": None,
        "guest_credits": 5,
        "priority": True,
    },
}

SUCCESS_CARD = "4242424242424242"
DECLINED_CARD = "4000000000000002"


@dataclass
class PaymentOutcome:
    payment: Payment
    subscription: Subscription | None


def process_subscription_payment(
    db: Session,
    user: User,
    plan_type: PlanType,
    card_number: str,
    subscription: Subscription | None = None,
) -> PaymentOutcome:
    plan = PLAN_CATALOG[plan_type]
    price = plan["price"]
    monthly_credits = plan["monthly_credits"]
    succeeded = card_number == SUCCESS_CARD
    failure_reason = (
        None
        if succeeded
        else "CARD_DECLINED"
        if card_number == DECLINED_CARD
        else "UNSUPPORTED_TEST_CARD"
    )
    payment = Payment(
        user_id=user.id,
        plan_type=plan_type,
        amount=price,
        status="SUCCEEDED" if succeeded else "FAILED",
        transaction_id=str(uuid4()),
        card_last_four=card_number[-4:],
        failure_reason=failure_reason,
    )
    db.add(payment)

    if not succeeded:
        db.commit()
        db.refresh(payment)
        return PaymentOutcome(payment=payment, subscription=None)

    now = datetime.now(UTC).replace(tzinfo=None)
    if subscription is None:
        subscription = Subscription(
            user_id=user.id,
            plan_type=plan_type,
            monthly_price=price,
            monthly_credit_limit=monthly_credits,
            remaining_credits=monthly_credits,
            status="ACTIVE",
        )
        db.add(subscription)

    subscription.plan_type = plan_type
    subscription.monthly_price = price
    subscription.monthly_credit_limit = monthly_credits
    subscription.remaining_credits = monthly_credits
    subscription.status = "ACTIVE"
    subscription.started_at = now
    subscription.expires_at = now + timedelta(days=30)
    db.flush()
    payment.subscription_id = subscription.id
    db.commit()
    db.refresh(payment)
    db.refresh(subscription)
    return PaymentOutcome(payment=payment, subscription=subscription)


def subscription_data(subscription: Subscription) -> dict[str, object]:
    return {
        "id": subscription.id,
        "plan_type": subscription.plan_type,
        "monthly_price": float(subscription.monthly_price),
        "monthly_credit_limit": subscription.monthly_credit_limit,
        "remaining_credits": subscription.remaining_credits,
        "status": subscription.status,
        "started_at": subscription.started_at.isoformat(),
        "expires_at": (
            subscription.expires_at.isoformat() if subscription.expires_at else None
        ),
    }


def payment_data(payment: Payment) -> dict[str, object]:
    return {
        "id": payment.id,
        "transaction_id": payment.transaction_id,
        "plan_type": payment.plan_type,
        "amount": float(payment.amount),
        "currency": "TRY",
        "status": payment.status,
        "card_last_four": payment.card_last_four,
        "failure_reason": payment.failure_reason,
        "created_at": payment.created_at.isoformat(),
    }
