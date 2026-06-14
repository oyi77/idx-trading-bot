"""
Scalev Payment Integration (Vilona Saham @ jasahub.id/product/vilona-saham).
No legacy Tripay references. This module owns only Scalev config, helpers,
reference registration/lookup, and signature verification.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)
WIB = timezone(timedelta(hours=7))

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
PAYMENT_STORE = DATA_DIR / "payments.json"


def _getenv_scalev() -> Dict[str, Optional[str]]:
    return {
        "api_key": os.environ.get("SCALEV_API_KEY") or os.environ.get("SCALEV_KEY"),
        "product_slug": os.environ.get(
            "SCALEV_PRODUCT_SLUG", "vilona-saham"
        ),
        "base_url": os.environ.get(
            "SCALEV_BASE_URL", "https://jasahub.id/api"
        ),
        "webhook_secret": os.environ.get("SCALEV_WEBHOOK_SECRET"),
    }


def _load_payments() -> Dict[str, Any]:
    if PAYMENT_STORE.exists():
        try:
            with open(PAYMENT_STORE, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            if isinstance(payload, dict) and "payments" in payload:
                return payload
        except Exception:
            pass
    return {"payments": {}}


def _save_payments(payload: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PAYMENT_STORE, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)


def _detect_ref(payload: Dict[str, Any]) -> str:
    for key in ("reference", "ref", "transaction_ref", "order_ref", "id"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return f"scalev-{int(time.time())}-{id(payload)}"


def build_purchase_link(
    tier: str,
    *,
    user_id: Optional[int] = None,
    source: str = "telegram",
    note: Optional[str] = None,
) -> Dict[str, str]:
    cfg = _getenv_scalev()
    product_slug = cfg["product_slug"]
    base = PROJECT_ROOT
    # Default to stored public product URL; avoid hardcoding network URLs.
    product_url = (
        os.environ.get("SCALEV_PRODUCT_URL")
        or "https://jasahub.id/p/vilona-saham"
    )

    params: Dict[str, str] = {
        "tier": tier,
        "source": source,
    }
    if user_id is not None:
        params["user_id"] = str(user_id)
    if note:
        params["note"] = note

    redirect = product_url
    if "?" in redirect:
        redirect = f"{redirect}&{urllib.parse.urlencode(params)}"
    else:
        redirect = f"{redirect}?{urllib.parse.urlencode(params)}"

    return {
        "product_slug": product_slug,
        "product_url": product_url,
        "purchase_url": redirect,
    }


def register_payment(
    *,
    user_id: int,
    username: Optional[str],
    tier: str,
    amount: Optional[int] = None,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    ref = _detect_ref(
        {
            "user_id": user_id,
            "username": username,
            "tier": tier,
            "amount": amount,
            "note": note,
        }
    )
    entry = {
        "user_id": user_id,
        "username": username or "",
        "tier": tier,
        "amount": amount,
        "status": "PENDING",
        "created_at": datetime.now(WIB).isoformat(),
        "reference": ref,
        "source": "scalev",
    }
    if note:
        entry["note"] = note
    data = _load_payments()
    data["payments"][ref] = entry
    _save_payments(data)
    return entry


def mark_paid(reference: str, paid_at: Optional[str] = None) -> Dict[str, Any]:
    data = _load_payments()
    entry = data["payments"].get(reference)
    if not entry:
        return {"success": False, "error": "Unknown payment reference"}
    entry["status"] = "PAID"
    entry["paid_at"] = paid_at or datetime.now(WIB).isoformat()
    _save_payments(data)
    return {"success": True, "payment": entry}


def mark_failed(reference: str, reason: str = "") -> Dict[str, Any]:
    data = _load_payments()
    entry = data["payments"].get(reference)
    if not entry:
        return {"success": False, "error": "Unknown payment reference"}
    entry["status"] = "FAILED"
    entry["failure_reason"] = reason
    _save_payments(data)
    return {"success": True, "payment": entry}


def get_payment(reference: str) -> Dict[str, Any]:
    data = _load_payments()
    entry = data["payments"].get(reference)
    if not entry:
        return {"success": False, "error": "Unknown payment reference"}
    return {"success": True, "payment": entry}


def verify_webhook(payload_bytes: bytes, signature: Optional[str]) -> bool:
    cfg = _getenv_scalev()
    secret = cfg.get("webhook_secret")
    if not secret:
        logger.warning("SCALEV_WEBHOOK_SECRET is not configured")
        return False
    if not signature:
        return False
    expected = hmac.new(
        secret.encode("utf-8"), payload_bytes, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def parse_event(payload: Dict[str, Any]) -> Dict[str, Any]:
    event_name = (
        payload.get("event")
        or payload.get("event_type")
        or payload.get("type")
        or ""
    )
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    return {
        "event": str(event_name).lower(),
        "data": data,
    }


def extract_reference(event_payload: Dict[str, Any]) -> Optional[str]:
    data = event_payload.get("data", {}) if isinstance(event_payload, dict) else {}
    for key in ("reference", "ref", "transaction_ref", "order_ref", "id"):
        candidate = data.get(key) if isinstance(data, dict) else None
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


def extract_tier(event_payload: Dict[str, Any]) -> Optional[str]:
    data = event_payload.get("data", {}) if isinstance(event_payload, dict) else {}
    for key in ("tier", "plan", "product", "variant"):
        candidate = data.get(key) if isinstance(data, dict) else None
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip().lower()
    return None


def infer_tier_from_amount(amount: Optional[int]) -> Optional[str]:
    if amount is None:
        return None
    if amount <= 0:
        return None
    if amount >= 1_990_000:
        return "lifetime"
    if amount >= 149_000:
        return "premium"
    if amount >= 49_000:
        return "pro"
    return None


def normalize_amount(value: Any) -> Optional[int]:
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        cleaned = value.replace(".", "").replace(",", "")
        try:
            return int(float(cleaned))
        except ValueError:
            return None
    return None


class PaymentError(Exception):
    pass


class PaymentNotFoundError(PaymentError):
    pass


class PaymentInvalidSignatureError(PaymentError):
    pass


class PaymentAlreadyProcessedError(PaymentError):
    pass


class PaymentValidationError(PaymentError):
    pass

