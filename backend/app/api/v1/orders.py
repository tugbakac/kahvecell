import hmac
from datetime import UTC, datetime
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, or_, select, update
from sqlalchemy.orm import Session, joinedload

from app.api.v1.auth import get_current_user, require_roles
from app.core.qr import create_qr_payload, verify_qr_signature
from app.db.session import get_db
from app.models import Order, Product, Shop, Subscription, User
from app.schemas.orders import (
    OrderCreateRequest,
    OrderStatusUpdateRequest,
    QRCodePayload,
)

router = APIRouter(prefix="/orders", tags=["Siparişler"])


def _success(data: object) -> dict[str, object]:
    return {"success": True, "data": data, "error": None}


def _raise_order_error(status_code: int, code: str, message: str) -> NoReturn:
    raise HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def _public_status(status_value: str) -> str:
    return "DELIVERED" if status_value == "COMPLETED" else status_value


def _order_data(
    order: Order,
    *,
    include_qr: bool,
    include_customer: bool = False,
) -> dict[str, object]:
    data: dict[str, object] = {
        "id": order.id,
        "status": _public_status(order.status),
        "shop": {
            "id": order.shop.id,
            "name": order.shop.name,
            "address": order.shop.address,
        },
        "product": {
            "id": order.product.id,
            "name": order.product.name,
            "unit_price": float(order.unit_price),
            "quantity": order.quantity,
        },
        "customizations": order.customizations,
        "created_at": order.created_at.isoformat() + "Z",
        "updated_at": order.updated_at.isoformat() + "Z",
        "qr_code": (
            create_qr_payload(
                order.public_id,
                order.user.public_id,
                order.shop.public_id,
                order.created_at,
            )
            if include_qr
            else None
        ),
    }
    if include_customer:
        data["customer"] = {
            "id": order.user.id,
            "full_name": order.user.full_name,
            "phone_number": order.user.phone_number,
        }
    return data


def _get_order(db: Session, order_id: int) -> Order:
    order = db.scalar(
        select(Order)
        .options(
            joinedload(Order.shop),
            joinedload(Order.product),
            joinedload(Order.user),
        )
        .where(Order.id == order_id)
    )
    if order is None:
        _raise_order_error(
            status.HTTP_404_NOT_FOUND, "ORDER_NOT_FOUND", "Siparis bulunamadi."
        )
    return order


def _ensure_shop_owner(order: Order, user: User) -> None:
    if user.role != "ADMIN" and order.shop.owner_user_id != user.id:
        _raise_order_error(
            status.HTTP_403_FORBIDDEN,
            "SHOP_ACCESS_DENIED",
            "Bu siparis kendi dukkaniniza ait degil.",
        )


@router.post("")
def create_order(
    request: OrderCreateRequest,
    user: Annotated[User, Depends(require_roles("CUSTOMER"))],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    now = datetime.now(UTC).replace(tzinfo=None)
    subscription = db.scalar(
        select(Subscription)
        .where(
            Subscription.user_id == user.id,
            Subscription.status == "ACTIVE",
            or_(
                Subscription.expires_at.is_(None),
                Subscription.expires_at > now,
            ),
        )
        .order_by(Subscription.started_at.desc(), Subscription.id.desc())
    )
    if subscription is None:
        _raise_order_error(
            status.HTTP_403_FORBIDDEN,
            "ACTIVE_SUBSCRIPTION_REQUIRED",
            "Siparis vermek icin aktif bir abonelik gereklidir.",
        )
    if subscription.remaining_credits == 0:
        _raise_order_error(
            status.HTTP_409_CONFLICT,
            "NO_COFFEE_CREDITS",
            "Kahve hakkiniz bitmis. Siparis veremezsiniz.",
        )

    shop = db.scalar(
        select(Shop).where(
            Shop.id == request.shop_id,
            Shop.is_active.is_(True),
        )
    )
    if shop is None:
        _raise_order_error(
            status.HTTP_404_NOT_FOUND, "SHOP_NOT_FOUND", "Dukkan bulunamadi."
        )
    product = db.scalar(
        select(Product).where(
            Product.id == request.product_id,
            Product.shop_id == shop.id,
            Product.is_available.is_(True),
        )
    )
    if product is None:
        _raise_order_error(
            status.HTTP_404_NOT_FOUND,
            "PRODUCT_NOT_AVAILABLE",
            "Urun bu dukkanin menusunde bulunamadi veya satista degil.",
        )

    credit_update = db.execute(
        update(Subscription)
        .where(
            Subscription.id == subscription.id,
            Subscription.status == "ACTIVE",
            or_(
                Subscription.remaining_credits.is_(None),
                Subscription.remaining_credits > 0,
            ),
            or_(
                Subscription.expires_at.is_(None),
                Subscription.expires_at > now,
            ),
        )
        .values(
            remaining_credits=case(
                (
                    Subscription.remaining_credits.is_(None),
                    None,
                ),
                else_=Subscription.remaining_credits - 1,
            )
        )
        .execution_options(synchronize_session=False)
    )
    if credit_update.rowcount != 1:
        db.rollback()
        _raise_order_error(
            status.HTTP_409_CONFLICT,
            "NO_COFFEE_CREDITS",
            "Kahve hakkiniz bitmis veya aboneliginiz sona ermis.",
        )

    order = Order(
        user_id=user.id,
        shop_id=shop.id,
        product_id=product.id,
        subscription_id=subscription.id,
        quantity=1,
        unit_price=product.price,
        customizations=request.customizations(),
        status="PENDING",
        created_at=now,
        updated_at=now,
    )
    db.add(order)
    db.flush()
    qr_payload = create_qr_payload(order.public_id, user.public_id, shop.public_id, now)
    order.qr_code_token = qr_payload["signature"]
    db.commit()
    db.refresh(order)
    db.refresh(subscription)

    return _success(
        {
            "order": _order_data(order, include_qr=True),
            "remaining_credits": subscription.remaining_credits,
        }
    )


@router.get("/history")
def get_order_history(
    user: Annotated[User, Depends(require_roles("CUSTOMER"))],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    orders = db.scalars(
        select(Order)
        .options(joinedload(Order.shop), joinedload(Order.product))
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc(), Order.id.desc())
    ).all()
    return _success([_order_data(order, include_qr=True) for order in orders])


@router.get("/shop")
def get_shop_orders(
    user: Annotated[User, Depends(require_roles("SHOP_OWNER", "ADMIN"))],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    statement = select(Order).options(
        joinedload(Order.shop),
        joinedload(Order.product),
        joinedload(Order.user),
    )
    if user.role != "ADMIN":
        shop_ids = select(Shop.id).where(Shop.owner_user_id == user.id)
        statement = statement.where(Order.shop_id.in_(shop_ids))
    orders = db.scalars(
        statement.order_by(Order.created_at.asc(), Order.id.asc())
    ).all()
    return _success(
        [
            _order_data(order, include_qr=False, include_customer=True)
            for order in orders
        ]
    )


@router.get("/{order_id}")
def get_order(
    order_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    order = _get_order(db, order_id)
    is_customer = order.user_id == user.id
    is_shop_owner = user.role == "SHOP_OWNER" and order.shop.owner_user_id == user.id
    if not is_customer and not is_shop_owner and user.role != "ADMIN":
        _raise_order_error(
            status.HTTP_403_FORBIDDEN,
            "ORDER_ACCESS_DENIED",
            "Bu siparisi goruntuleme yetkiniz yok.",
        )
    return _success(
        _order_data(
            order,
            include_qr=is_customer,
            include_customer=not is_customer,
        )
    )


@router.patch("/{order_id}/status")
def update_order_status(
    order_id: int,
    request: OrderStatusUpdateRequest,
    user: Annotated[User, Depends(require_roles("SHOP_OWNER", "ADMIN"))],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    order = _get_order(db, order_id)
    _ensure_shop_owner(order, user)
    allowed_next_status = {
        "PENDING": "ACCEPTED",
        "ACCEPTED": "PREPARING",
        "PREPARING": "READY",
    }
    if allowed_next_status.get(order.status) != request.status:
        _raise_order_error(
            status.HTTP_409_CONFLICT,
            "INVALID_ORDER_TRANSITION",
            f"Siparis {order.status} durumundan {request.status} durumuna gecemez.",
        )
    order.status = request.status
    db.commit()
    db.refresh(order)
    return _success(_order_data(order, include_qr=False, include_customer=True))


@router.post("/{order_id}/verify-qr")
def verify_order_qr(
    order_id: int,
    request: QRCodePayload,
    user: Annotated[User, Depends(require_roles("SHOP_OWNER", "ADMIN"))],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    order = _get_order(db, order_id)
    _ensure_shop_owner(order, user)
    if order.status == "COMPLETED":
        _raise_order_error(
            status.HTTP_409_CONFLICT,
            "QR_ALREADY_REDEEMED",
            "QR kod daha once kullanilmis.",
        )
    if order.status != "READY":
        _raise_order_error(
            status.HTTP_409_CONFLICT,
            "ORDER_NOT_READY",
            "QR kod yalnizca hazir siparislerde okutulabilir.",
        )

    submitted_payload = request.model_dump()
    expected_payload = create_qr_payload(
        order.public_id,
        order.user.public_id,
        order.shop.public_id,
        order.created_at,
    )
    matches_order = all(
        submitted_payload[key] == expected_payload[key]
        for key in ("order_id", "user_id", "shop_id", "created_at")
    )
    signature_is_valid = verify_qr_signature(submitted_payload)
    signature_matches_order = hmac.compare_digest(
        submitted_payload["signature"], order.qr_code_token or ""
    )
    if not matches_order or not signature_is_valid or not signature_matches_order:
        _raise_order_error(
            status.HTTP_400_BAD_REQUEST,
            "INVALID_QR_SIGNATURE",
            "QR kod imzasi gecersiz veya siparisle eslesmiyor.",
        )

    order.status = "COMPLETED"
    db.commit()
    db.refresh(order)
    return _success(_order_data(order, include_qr=False, include_customer=True))
