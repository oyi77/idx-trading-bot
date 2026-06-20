"""Geolocation and market hours utilities using ipstack API."""

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

IPSTACK_URL = "http://api.ipstack.com/{ip}?access_key={key}"

WIB = timezone(timedelta(hours=7))
IDX_OPEN_HOUR = 9
IDX_CLOSE_HOUR = 16


def get_user_location(ip_address: str) -> Optional[dict]:
    """Look up geolocation for *ip_address* via ipstack.

    Returns dict with ``country``, ``timezone``, and ``is_idx_open`` keys,
    or ``None`` on failure.
    """
    key = os.environ.get("ipstack_api_key")
    if not key:
        logger.error("ipstack_api_key not set in environment")
        return None

    url = IPSTACK_URL.format(ip=ip_address, key=key)
    try:
        resp = httpx.get(url, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        logger.exception("ipstack request failed for %s", ip_address)
        return None

    if data.get("error"):
        logger.error("ipstack error: %s", data["error"])
        return None

    tz_id = (data.get("time_zone") or {}).get("id", "Asia/Jakarta")
    now_wib = datetime.now(WIB)

    return {
        "country": data.get("country_name"),
        "timezone": tz_id,
        "is_idx_open": _is_idx_open(now_wib),
    }


def get_market_hours(tz_name: Optional[str] = None) -> dict:
    """Return IDX market status for the given timezone (defaults to WIB).

    Keys: ``is_open``, ``open_utc``, ``close_utc``, ``current_wib``.
    """
    now_wib = datetime.now(WIB)
    open_utc = datetime(now_wib.year, now_wib.month, now_wib.day,
                        IDX_OPEN_HOUR, 0, tzinfo=WIB).astimezone(timezone.utc)
    close_utc = datetime(now_wib.year, now_wib.month, now_wib.day,
                         IDX_CLOSE_HOUR, 0, tzinfo=WIB).astimezone(timezone.utc)

    return {
        "is_open": _is_idx_open(now_wib),
        "open_utc": open_utc.isoformat(),
        "close_utc": close_utc.isoformat(),
        "current_wib": now_wib.strftime("%Y-%m-%d %H:%M:%S WIB"),
    }


def _is_idx_open(now_wib: datetime) -> bool:
    """True if *now_wib* falls within IDX trading hours (Mon-Fri 09:00-16:00)."""
    if now_wib.weekday() >= 5:  # Saturday / Sunday
        return False
    return IDX_OPEN_HOUR <= now_wib.hour < IDX_CLOSE_HOUR
