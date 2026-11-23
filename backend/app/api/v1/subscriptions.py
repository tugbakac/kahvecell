from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.db.session import get_db
from app.models import Subscription, User
from app.schemas.subscriptions import SubscriptionPaymentRequest
from app.services.subscriptions import (
    PLAN_CATALOG,
    PaymentOutcome,
    payment_data,
    process_subscription_payment,
    subscription_data,
)

router = APIRouter(prefix="/subscriptions", tags=["Abonelikler"])


def _success(data: object) -> dict[str, object]:
    return {"success": True, "data": data, "error": None}


def _active_subscription(db: Session, user: User) -> Subscription | None:
    return db.scalar(
        select(Subscription)
        .where(
            Subscription.user_id == user.id,
            Subscription.status == "ACTIVE",
        )
        .order_by(Subscription.started_at.desc(), Subscription.id.desc())
    )


def _outcome_response(outcome: PaymentOutcome) -> dict[str, object]:
    result = {
        "payment": payment_data(outcome.payment),
        "subscription": (
            subscription_data(outcome.subscription)
            if outcome.subscription is not None
            else None
        ),
    }
    if outcome.payment.status == "FAILED":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": outcome.payment.failure_reason or "PAYMENT_FAILED",
                "message": "Odeme basarisiz; abonelik degistirilmedi.",
                "data": result,
            },
        )
    return _success(result)


@router.get("/plans")
def list_plans() -> dict[str, object]:
    plans = [
        {
            "plan_type": plan_type,
            "name": plan["name"],
            "monthly_price": float(plan["price"]),
            "currency": "TRY",
            "monthly_coffee_credits": plan["monthly_credits"],
            "validity_days": 30,
            "valid_at_all_shops": True,
            "guest_credits": plan["guest_credits"],
            "priority_service": plan["priority"],
        }
        for plan_type, plan in PLAN_CATALOG.items()
    ]
    return _success(plans)


@router.post("")
def start_subscription(
    request: SubscriptionPaymentRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    if _active_subscription(db, user) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "ACTIVE_SUBSCRIPTION_EXISTS",
                "message": "Aktif aboneligi degistirmek icin PATCH /subscriptions/me kullanin.",
            },
        )
    outcome = process_subscription_payment(
        db, user, request.plan_type, request.card_number
    )
    return _outcome_response(outcome)


@router.get("/me")
def get_my_subscription(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    subscription = _active_subscription(db, user)
    return _success(
        subscription_data(subscription) if subscription is not None else None
    )


@router.patch("/me")
def change_subscription(
    request: SubscriptionPaymentRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    subscription = _active_subscription(db, user)
    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ACTIVE_SUBSCRIPTION_NOT_FOUND",
                "message": "Degistirilecek aktif abonelik bulunamadi.",
            },
        )
    if subscription.plan_type == request.plan_type:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "SAME_PLAN",
                "message": "Kullanici zaten bu pakette.",
            },
        )
    outcome = process_subscription_payment(
        db,
        user,
        request.plan_type,
        request.card_number,
        subscription=subscription,
    )
    return _outcome_response(outcome)


@router.delete("/me")
def cancel_subscription(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    subscription = _active_subscription(db, user)
    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ACTIVE_SUBSCRIPTION_NOT_FOUND",
                "message": "Iptal edilecek aktif abonelik bulunamadi.",
            },
        )
    subscription.status = "CANCELLED"
    subscription.remaining_credits = 0
    subscription.expires_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    db.refresh(subscription)
    return _success(subscription_data(subscription))
