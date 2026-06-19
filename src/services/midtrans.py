"""
Midtrans Payment Integration for idx-trading-bot.

Docs: https://docs.midtrans.com/reference/overview
Flow: Create Snap transaction → User pays → Webhook notification → Auto-upgrade tier
"""
import base64
import hashlib
import hmac
import json
import logging
import os
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)
WIB = timezone(timedelta(hours=7))

MIDTRANS_SERVER_KEY = os.environ.get("MIDTRANS_SERVER_KEY", "")
MIDTRANS_CLIENT_KEY = os.environ.get("MIDTRANS_CLIENT_KEY", "")
MIDTRANS_MERCHANT_ID = os.environ.get("MIDTRANS_MERCHANT_ID", "")
MIDTRANS_IS_PRODUCTION = os.environ.get("MIDTRANS_IS_PRODUCTION", "false").lower() == "true"

MIDTRANS_BASE_URL = (
    "https://app.midtrans.com/snap/v1" 
    if MIDTRANS_IS_PRODUCTION 
    else "https://app.sandbox.midtrans.com/snap/v1"
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
PAYMENT_STORE = DATA_DIR / "midtrans_payments.json"

TIER_PRICES = {
    "pro": 79900,
    "premium": 149900,
    "lifetime": 1999900,
    "whitelabel": 5000000,
}


def _load_payments() -> Dict[str, Any]:
    """Load payment records from disk."""
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
    """Save payment records to disk."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PAYMENT_STORE, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)


def verify_signature(order_id: str, status_code: str, gross_amount: str, signature_key: str) -> bool:
    """
    Verify Midtrans notification signature.
    
    SHA512(order_id + status_code + gross_amount + ServerKey)
    """
    if not MIDTRANS_SERVER_KEY:
        logger.warning("MIDTRANS_SERVER_KEY not configured")
        return False
    
    payload = f"{order_id}{status_code}{gross_amount}{MIDTRANS_SERVER_KEY}"
    expected = hashlib.sha512(payload.encode()).hexdigest()
    return hmac.compare_digest(expected, signature_key)


def create_snap_transaction(
    order_id: str,
    tier: str,
    amount: int,
    user_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create Midtrans Snap transaction.
    
    Returns: {"token": "snap_token", "redirect_url": "https://..."}
    """
    if not MIDTRANS_SERVER_KEY:
        raise ValueError("MIDTRANS_SERVER_KEY not configured")
    
    transaction_data = {
        "transaction_details": {
            "order_id": order_id,
            "gross_amount": amount,
        },
        "item_details": [
            {
                "id": tier,
                "price": amount,
                "quantity": 1,
                "name": f"Vilona Saham IDX - {tier.upper()} Tier",
            }
        ],
        "customer_details": {
            "first_name": user_data.get("username", "User"),
            "email": user_data.get("email", f"user_{user_data.get('chat_id')}@vilona.id"),
            "phone": user_data.get("phone", ""),
        },
        "custom_field1": str(user_data.get("chat_id", "")),
        "custom_field2": tier,
        "custom_field3": user_data.get("username", ""),
    }
    
    # Register payment locally
    payments = _load_payments()
    payments["payments"][order_id] = {
        "order_id": order_id,
        "tier": tier,
        "amount": amount,
        "chat_id": user_data.get("chat_id"),
        "username": user_data.get("username"),
        "status": "pending",
        "created_at": datetime.now(WIB).isoformat(),
        "provider": "midtrans",
    }
    _save_payments(payments)
    
    # Call Midtrans Snap API
    url = f"{MIDTRANS_BASE_URL}/transactions"
    auth_string = base64.b64encode(f"{MIDTRANS_SERVER_KEY}:".encode()).decode()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_string}",
        "Accept": "application/json",
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(transaction_data).encode(),
        headers=headers,
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode())
            logger.info(f"Midtrans Snap created: order_id={order_id}, token={result.get('token')}")
            return result
    except Exception as e:
        logger.error(f"Midtrans Snap creation failed: {e}")
        raise


def mark_paid(order_id: str) -> None:
    """Mark payment as paid."""
    payments = _load_payments()
    if order_id in payments["payments"]:
        payments["payments"][order_id]["status"] = "paid"
        payments["payments"][order_id]["paid_at"] = datetime.now(WIB).isoformat()
        _save_payments(payments)
        logger.info(f"Midtrans payment marked paid: {order_id}")


def get_payment(order_id: str) -> Optional[Dict[str, Any]]:
    """Get payment record by order_id."""
    payments = _load_payments()
    return payments["payments"].get(order_id)


def infer_tier_from_amount(amount: int) -> str:
    """Infer tier from payment amount."""
    if amount >= 1999900:
        return "lifetime"
    elif amount >= 149900:
        return "premium"
    elif amount >= 79900:
        return "pro"
    return "free"


def generate_order_id(chat_id: int, tier: str) -> str:
    """Generate unique order_id for Midtrans."""
    timestamp = int(time.time())
    return f"IDX-{chat_id}-{tier.upper()}-{timestamp}"
