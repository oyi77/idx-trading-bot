#!/usr/bin/env python3
"""Meta Conversions API (CAPI) — server-side conversion tracking.

Events tracked:
  - CompleteRegistration: /start with track_ param
  - Lead: /start (organic)
  - InitiateCheckout: /subscribe
  - Purchase: payment success

Pixel ID: 771021905629860
All bots share this pixel.
"""

import hashlib
import json
import logging
import os
import time
import urllib.request
from typing import Optional

logger = logging.getLogger(__name__)

# ── Config from env ──
PIXEL_ID = os.environ.get("META_PIXEL_ID", "771021905629860")
ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "")
CAPI_URL = f"https://graph.facebook.com/v19.0/{PIXEL_ID}/events"


def _hash(value: str) -> str:
    """SHA256 hash for CAPI user data."""
    return hashlib.sha256(value.strip().lower().encode()).hexdigest()


def send_event(
    event_name: str,
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    user_phone: Optional[str] = None,
    value: Optional[float] = None,
    currency: str = "IDR",
    content_name: Optional[str] = None,
    content_category: Optional[str] = None,
    source_url: Optional[str] = None,
) -> bool:
    """Send conversion event to Meta CAPI.

    Args:
        event_name: Standard event (CompleteRegistration, Lead, InitiateCheckout, Purchase)
                    or custom event name
        user_id: Telegram chat_id (hashed)
        user_email: User email (hashed)
        user_phone: User phone (hashed)
        value: Transaction value (for Purchase)
        currency: Currency code
        content_name: Event content name
        content_category: Event category
        source_url: Source URL

    Returns:
        True if event sent successfully
    """
    if not ACCESS_TOKEN:
        logger.warning("META_ACCESS_TOKEN not set, skipping CAPI event")
        return False

    user_data = {}
    if user_id:
        user_data["external_id"] = _hash(str(user_id))
    if user_email:
        user_data["em"] = _hash(user_email)
    if user_phone:
        user_data["ph"] = _hash(user_phone)

    event = {
        "event_name": event_name,
        "event_time": int(time.time()),
        "action_source": "website",
        "user_data": user_data,
    }

    if value is not None:
        event["value"] = value
        event["currency"] = currency

    if content_name:
        event["content_name"] = content_name
    if content_category:
        event["content_category"] = content_category
    if source_url:
        event["event_source_url"] = source_url

    payload = {
        "data": [event],
        "access_token": ACCESS_TOKEN,
    }

    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            CAPI_URL,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            resp = json.loads(r.read())
            if resp.get("events_received", 0) > 0:
                logger.info(f"CAPI event sent: {event_name} (user={user_id})")
                return True
            else:
                logger.warning(f"CAPI event not received: {resp}")
                return False
    except Exception as e:
        logger.warning(f"CAPI event failed: {e}")
        return False


# ── Convenience functions ──

def track_registration(chat_id: str, source: str = "organic"):
    """Track CompleteRegistration event."""
    return send_event(
        event_name="CompleteRegistration",
        user_id=chat_id,
        content_name=f"bot_start_{source}",
    )


def track_lead(chat_id: str, source: str = "organic"):
    """Track Lead event."""
    return send_event(
        event_name="Lead",
        user_id=chat_id,
        content_name=f"bot_lead_{source}",
    )


def track_checkout(chat_id: str, tier: str, value: float = 0):
    """Track InitiateCheckout event."""
    return send_event(
        event_name="InitiateCheckout",
        user_id=chat_id,
        value=value,
        content_name=f"subscribe_{tier}",
        content_category="subscription",
    )


def track_purchase(chat_id: str, tier: str, value: float, order_ref: str = ""):
    """Track Purchase event."""
    return send_event(
        event_name="Purchase",
        user_id=chat_id,
        value=value,
        content_name=f"purchase_{tier}",
        content_category="subscription",
    )


def track_custom(chat_id: str, event_name: str, **kwargs):
    """Track custom event."""
    return send_event(event_name=event_name, user_id=chat_id, **kwargs)
