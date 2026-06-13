"""
Tripay Payment Integration for idx-trading-bot.

Tripay API Docs: https://tripay.co.id/developer
Closed Payment flow: Create → User pays → Webhook callback → Auto-upgrade tier.
"""
import hashlib
import hmac
import json
import logging
import os
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)
WIB = timezone(timedelta(hours=7))

TRIPAY_MERCHANT_CODE = os.environ.get("TRIPAY_MERCHANT_CODE", "")
TRIPAY_API_KEY = os.environ.get("TRIPAY_API_KEY", "")
TRIPAY_PRIVATE_KEY = os.environ.get("TRIPAY_PRIVATE_KEY", "")
TRIPAY_BASE_URL = os.environ.get("TRIPAY_BASE_URL", "https://tripay.co.id/api")
TRIPAY_CALLBACK_URL = os.environ.get("TRIPAY_CALLBACK_URL", "")
DEFAULT_METHOD = os.environ.get("TRIPAY_DEFAULT_METHOD", "QRIS2")

PROJECT_ROOT = Path(__file__).parent.parent.parent
PAYMENT_STORE = PROJECT_ROOT / "data" / "payments.json"

TIER_PRICES = {
    "pro": 49000,
    "premium": 149000,
    "lifetime": 1999000,
    "whitelabel": 5000000,
}

TIER_LABELS = {
    "pro": "💎 Pro (Rp49rb/bln)",
    "premium": "👑 Premium (Rp149rb/bln)",
    "lifetime": "🌟 Lifetime (Rp1.999rb)",
    "whitelabel": "🏢 White-label (Rp5jt + Rp500rb/bln)",
}


def _sign(payload: str) -> str:
    return hmac.new(
        TRIPAY_PRIVATE_KEY.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()


def verify_callback(callback_data: str, callback_signature: str) -> bool:
    expected = _sign(callback_data)
    return hmac.compare_digest(expected, callback_signature)


def _load_payments() -> dict:
    if PAYMENT_STORE.exists():
        with open(PAYMENT_STORE) as f:
            return json.load(f)
    return {"payments": {}}


def _save_payments(data: dict):
    PAYMENT_STORE.parent.mkdir(parents=True, exist_ok=True)
    with open(PAYMENT_STORE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def create_payment(
    user_id: int,
    username: str,
    tier: str,
    method: str = None,
) -> dict:
    """Create Tripay payment transaction for a tier upgrade.

    Args:
        user_id: Telegram user ID
        username: Telegram username or first name
        tier: Target tier (pro, premium, lifetime, whitelabel)
        method: Payment method (QRIS2, BRIVA, MYBVA etc.). Default: QRIS2.

    Returns:
        {
            "success": bool,
            "payment_url": str,       # QR/payment URL
            "reference": str,          # merchant_ref for tracking
            "pay_code": str,           # QR code or VA number
            "amount": int,
            "tier": str,
            "expired_at": str,
        }
    """
    if not TRIPAY_API_KEY or not TRIPAY_PRIVATE_KEY:
        return {"success": False, "error": "Tripay credentials not configured"}

    amount = TIER_PRICES.get(tier)
    if not amount:
        return {"success": False, "error": f"Unknown tier: {tier}"}

    method = method or DEFAULT_METHOD
    label = TIER_LABELS.get(tier, f"Upgrade {tier}")
    merchant_ref = f"IDX-{user_id}-{int(time.time())}"

    payload = {
        "method": method,
        "merchant_ref": merchant_ref,
        "amount": amount,
        "customer_name": username or f"User{user_id}",
        "customer_email": f"{user_id}@idx.user",
        "customer_phone": "08123456789",
        "order_items": [
            {"name": label, "price": amount, "quantity": 1}
        ],
        "callback_url": TRIPAY_CALLBACK_URL,
        "return_url": "https://t.me/vilonasaham_bot",
        "expired_time": int(time.time()) + 86400,
        "signature": "",
    }

    raw = f"{TRIPAY_MERCHANT_CODE}{merchant_ref}{amount}"
    payload["signature"] = _sign(raw)

    url = f"{TRIPAY_BASE_URL}/transaction/create"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {TRIPAY_API_KEY}",
            "Content-Type": "application/json",
        },
    )

    try:
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read())

        if result.get("success"):
            payments = _load_payments()
            payments["payments"][merchant_ref] = {
                "user_id": user_id,
                "username": username,
                "tier": tier,
                "amount": amount,
                "status": "PENDING",
                "created_at": datetime.now(WIB).isoformat(),
                "reference": result.get("data", {}).get("reference", ""),
            }
            _save_payments(payments)

            data = result.get("data", {})
            return {
                "success": True,
                "payment_url": data.get("checkout_url", ""),
                "reference": merchant_ref,
                "pay_code": data.get("pay_code", ""),
                "amount": amount,
                "tier": tier,
                "expired_at": data.get("expired_time", ""),
                "qr_url": data.get("qr_url", ""),
            }
        else:
            return {"success": False, "error": result.get("message", "Tripay error")}

    except Exception as e:
        logger.error(f"Tripay create failed: {e}")
        return {"success": False, "error": str(e)}


def check_payment(reference: str) -> dict:
    """Check Tripay transaction status.

    Returns:
        {"success": bool, "status": "PAID"|"PENDING"|"EXPIRED"|"FAILED", ...}
    """
    if not TRIPAY_API_KEY or not TRIPAY_PRIVATE_KEY:
        return {"success": False, "error": "Tripay credentials not configured"}

    raw = reference + TRIPAY_MERCHANT_CODE
    payload = {
        "merchant_ref": reference,
        "signature": _sign(raw),
    }

    url = f"{TRIPAY_BASE_URL}/transaction/detail"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {TRIPAY_API_KEY}",
            "Content-Type": "application/json",
        },
    )

    try:
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())

        if result.get("success"):
            data = result.get("data", {})
            return {
                "success": True,
                "status": data.get("status", "UNPAID"),
                "amount": data.get("amount", 0),
                "amount_received": data.get("amount_received", 0),
                "fee_merchant": data.get("fee_merchant", 0),
                "paid_at": data.get("paid_at", ""),
            }
        else:
            return {"success": False, "error": result.get("message")}

    except Exception as e:
        logger.error(f"Tripay check failed: {e}")
        return {"success": False, "error": str(e)}


def handle_callback(payload: dict) -> dict:
    """Process Tripay webhook callback. Auto-upgrade user tier if PAID.

    Returns:
        {"success": bool, "action": "upgraded"|"ignored"|"error", ...}
    """
    merchant_ref = payload.get("merchant_ref", "")
    status = payload.get("status", "")
    amount = int(payload.get("total_amount", 0))

    logger.info(f"Callback: ref={merchant_ref} status={status} amount={amount}")

    if status != "PAID":
        return {"success": True, "action": "ignored", "reason": f"Status: {status}"}

    payments = _load_payments()
    entry = payments["payments"].get(merchant_ref)

    if not entry:
        logger.warning(f"Unknown payment ref: {merchant_ref}")
        return {"success": False, "error": "Unknown reference"}

    if entry["status"] == "PAID":
        return {"success": True, "action": "ignored", "reason": "Already processed"}

    user_id = entry["user_id"]
    tier = entry["tier"]

    try:
        from src.services.user_manager import UserManager
        manager = UserManager()
        success, msg = manager.upgrade_tier(user_id, tier, amount)
        if success:
            entry["status"] = "PAID"
            entry["paid_at"] = datetime.now(WIB).isoformat()
            _save_payments(payments)
            return {"success": True, "action": "upgraded", "user_id": user_id, "tier": tier}
        else:
            return {"success": False, "error": msg}
    except Exception as e:
        logger.error(f"Upgrade failed: {e}")
        return {"success": False, "error": str(e)}
