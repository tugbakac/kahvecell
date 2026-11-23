import math
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models import Product, Shop

router = APIRouter(prefix="/shops", tags=["Dükkanlar"])
EARTH_RADIUS_KM = 6371.0088


def _success(data: object) -> dict[str, object]:
    return {"success": True, "data": data, "error": None}


def _distance_km(
    origin_latitude: float,
    origin_longitude: float,
    shop_latitude: float,
    shop_longitude: float,
) -> float:
    latitude_delta = math.radians(shop_latitude - origin_latitude)
    longitude_delta = math.radians(shop_longitude - origin_longitude)
    origin_latitude = math.radians(origin_latitude)
    shop_latitude = math.radians(shop_latitude)
    haversine = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(origin_latitude)
        * math.cos(shop_latitude)
        * math.sin(longitude_delta / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(haversine)))


def _product_data(product: Product) -> dict[str, object]:
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": float(product.price),
        "currency": "TRY",
    }


def _shop_data(
    shop: Shop,
    distance_km: float | None = None,
    include_menu: bool = False,
) -> dict[str, object]:
    data: dict[str, object] = {
        "id": shop.id,
        "name": shop.name,
        "address": shop.address,
        "latitude": shop.latitude,
        "longitude": shop.longitude,
        "opening_hours": shop.opening_hours,
        "rating": float(shop.rating) if shop.rating is not None else None,
        "distance_km": round(distance_km, 2) if distance_km is not None else None,
    }
    if include_menu:
        data["menu"] = [
            _product_data(product)
            for product in sorted(shop.products, key=lambda item: item.name.casefold())
            if product.is_available
        ]
    return data


def _get_active_shop(db: Session, shop_id: int) -> Shop:
    shop = db.scalar(
        select(Shop)
        .options(selectinload(Shop.products))
        .where(Shop.id == shop_id, Shop.is_active.is_(True))
    )
    if shop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "SHOP_NOT_FOUND",
                "message": "Dukkan bulunamadi.",
            },
        )
    return shop


@router.get("")
def list_shops(
    db: Annotated[Session, Depends(get_db)],
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lng: Annotated[float | None, Query(ge=-180, le=180)] = None,
    radius_km: Annotated[float | None, Query(gt=0, le=500)] = None,
    q: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
) -> dict[str, object]:
    if (lat is None) != (lng is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "INCOMPLETE_LOCATION",
                "message": "Yakindaki dukkanlari aramak icin lat ve lng birlikte gonderilmeli.",
            },
        )
    if radius_km is not None and lat is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "LOCATION_REQUIRED",
                "message": "radius_km kullanmak icin lat ve lng de gonderilmeli.",
            },
        )

    statement = select(Shop).where(Shop.is_active.is_(True))
    if q is not None:
        search_text = q.strip()
        if search_text:
            search_pattern = f"%{search_text}%"
            statement = statement.where(
                or_(
                    Shop.name.ilike(search_pattern),
                    Shop.address.ilike(search_pattern),
                )
            )
    shops = list(db.scalars(statement).all())

    if lat is not None and lng is not None:
        shops_with_distance = [
            (
                shop,
                _distance_km(lat, lng, shop.latitude, shop.longitude),
            )
            for shop in shops
        ]
        if radius_km is not None:
            shops_with_distance = [
                (shop, distance)
                for shop, distance in shops_with_distance
                if distance <= radius_km
            ]
        shops_with_distance.sort(key=lambda result: (result[1], result[0].id))
        return _success(
            [_shop_data(shop, distance) for shop, distance in shops_with_distance]
        )

    shops.sort(key=lambda shop: (shop.name.casefold(), shop.id))
    return _success([_shop_data(shop) for shop in shops])


@router.get("/{shop_id}")
def get_shop(
    shop_id: int,
    db: Annotated[Session, Depends(get_db)],
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lng: Annotated[float | None, Query(ge=-180, le=180)] = None,
) -> dict[str, object]:
    if (lat is None) != (lng is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INCOMPLETE_LOCATION",
                "message": "Mesafe icin lat ve lng birlikte gonderilmeli.",
            },
        )
    shop = _get_active_shop(db, shop_id)
    distance = (
        _distance_km(lat, lng, shop.latitude, shop.longitude)
        if lat is not None and lng is not None
        else None
    )
    return _success(_shop_data(shop, distance, include_menu=True))


@router.get("/{shop_id}/menu")
def get_shop_menu(
    shop_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    shop = _get_active_shop(db, shop_id)
    return _success(
        {
            "shop_id": shop.id,
            "shop_name": shop.name,
            "products": [
                _product_data(product)
                for product in sorted(
                    shop.products, key=lambda item: item.name.casefold()
                )
                if product.is_available
            ],
        }
    )
