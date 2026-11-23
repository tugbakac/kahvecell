from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.api.v1.subscriptions import _active_subscription, _outcome_response
from app.db.session import get_db
from app.models import Payment, User
from app.schemas.subscriptions import SubscriptionPaymentRequest
from app.services.subscriptions import payment_data, process_subscription_payment

router = APIRouter(prefix="/payments", tags=["Paycell ödeme simülasyonu"])


def _success(data: object) -> dict[str, object]:
    return {"success": True, "data": data, "error": None}


@router.post("/process")
def process_payment(
    request: SubscriptionPaymentRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    subscription = _active_subscription(db, user)
    outcome = process_subscription_payment(
        db,
        user,
        request.plan_type,
        request.card_number,
        subscription=subscription,
    )
    return _outcome_response(outcome)


@router.get("/history")
def payment_history(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    payments = db.scalars(
        select(Payment)
        .where(Payment.user_id == user.id)
        .order_by(Payment.created_at.desc(), Payment.id.desc())
    ).all()
    return _success([payment_data(payment) for payment in payments])
