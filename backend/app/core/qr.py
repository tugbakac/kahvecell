import hashlib
import hmac
import json
from datetime import UTC, datetime
from pathlib import Path

from app.core.security import load_signing_key

_QR_SIGNING_KEY_FILE = Path(__file__).resolve().parents[2] / "data" / "qr_signing_key"
_QR_SIGNING_KEY = load_signing_key(_QR_SIGNING_KEY_FILE, "KAHVECELL_QR_SECRET")


def create_qr_payload(
    order_id: str,
    user_id: str,
    shop_id: str,
    created_at: datetime,
) -> dict[str, str]:
    timestamp = created_at
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    unsigned_payload = {
        "order_id": order_id,
        "user_id": user_id,
        "shop_id": shop_id,
        "created_at": timestamp.astimezone(UTC).isoformat().replace("+00:00", "Z"),
    }
    canonical_json = json.dumps(
        unsigned_payload, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    signature = hmac.new(_QR_SIGNING_KEY, canonical_json, hashlib.sha256).hexdigest()
    return {**unsigned_payload, "signature": signature}


def verify_qr_signature(payload: dict[str, str]) -> bool:
    unsigned_payload = {
        key: payload[key] for key in ("order_id", "user_id", "shop_id", "created_at")
    }
    canonical_json = json.dumps(
        unsigned_payload, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    expected_signature = hmac.new(
        _QR_SIGNING_KEY, canonical_json, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, payload["signature"])
