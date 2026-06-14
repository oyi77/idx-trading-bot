"""Screener Cache — Cuts 60s → <3s for repeat screener calls.

Strategy:
- Cache all OHLC data as a single JSON file (data/screener_cache/all_stocks.json)
- TTL: 5 minutes during market hours (09:00-16:00 WIB), 60 minutes outside
- Background refresh thread that auto-updates cache every TTL/2
- First call still takes ~60s (cold start), but subsequent calls hit cache

Why single file vs per-stock: yfinance batch fetch is the IO bottleneck, not parse time.
693 individual RapidAPI calls would take 11+ minutes due to 1 req/sec rate limit.
"""

import json
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

CACHE_DIR = Path("data/screener_cache")
CACHE_FILE = CACHE_DIR / "all_stocks.json"
CACHE_TTL_MARKET = 300  # 5 minutes during market hours
CACHE_TTL_OFFHOURS = 3600  # 60 minutes outside market hours
REFRESH_INTERVAL = 150  # Background refresh every 2.5 min during market


def _is_market_hours() -> bool:
    """Check if IDX market is currently open (09:00-16:00 WIB, Mon-Fri)."""
    now = datetime.now()
    weekday = now.weekday()  # 0=Mon, 6=Sun
    if weekday >= 5:  # Sat/Sun
        return False
    hour = now.hour
    return 9 <= hour < 16


def _get_ttl() -> int:
    """Get cache TTL based on market hours."""
    return CACHE_TTL_MARKET if _is_market_hours() else CACHE_TTL_OFFHOURS


def _load_cache() -> Optional[Dict]:
    """Load cached OHLC data if still fresh."""
    if not CACHE_FILE.exists():
        return None

    try:
        with open(CACHE_FILE) as f:
            cache = json.load(f)
    except (json.JSONDecodeError, IOError):
        return None

    last_refresh = cache.get("_last_refresh", 0)
    age = time.time() - last_refresh
    ttl = _get_ttl()

    if age > ttl:
        return None  # Expired

    data = cache.get("data", {})
    stock_count = cache.get("_stock_count", 0)
    logger.info(f"📦 Cache HIT: {stock_count} stocks, age={age:.0f}s, ttl={ttl}s")
    return data


def _save_cache(data: Dict[str, List[Dict]]) -> None:
    """Save OHLC data to cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = {
        "_last_refresh": time.time(),
        "_stock_count": len(data),
        "data": data,
    }
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)
    logger.info(f"💾 Cache SAVED: {len(data)} stocks, {CACHE_FILE.stat().st_size / 1024:.0f} KB")


async def fetch_all_cached() -> Dict[str, List[Dict]]:
    """Fetch OHLC data for all IDX stocks — cached version.

    Returns cached data if fresh, otherwise fetches from yfinance.
    First call is ~60s; subsequent calls within TTL are <0.1s.
    """
    # Try cache first
    cached = _load_cache()
    if cached is not None:
        return cached

    # Cache miss — fetch fresh
    from src.engine.screener_categories import CategoryScreener
    from src.engine.idx_universe import IDX_UNIVERSE

    logger.info(f"🔄 Cache MISS — fetching {len(IDX_UNIVERSE)} stocks...")
    data = await CategoryScreener.fetch_all()

    # Save to cache
    if data:
        _save_cache(data)

    return data


def _background_refresh_worker() -> None:
    """Background thread: refresh cache periodically during market hours."""
    import asyncio

    while True:
        time.sleep(60)  # Check every minute

        if not _is_market_hours():
            continue

        # Check cache age
        if not CACHE_FILE.exists():
            continue

        try:
            with open(CACHE_FILE) as f:
                cache = json.load(f)
            age = time.time() - cache.get("_last_refresh", 0)
        except Exception:
            continue

        if age < REFRESH_INTERVAL:
            continue  # Still fresh enough

        # Time to refresh
        logger.info("🔄 Background cache refresh starting...")
        try:
            from src.engine.screener_categories import CategoryScreener
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            data = loop.run_until_complete(CategoryScreener.fetch_all())
            loop.close()
            if data:
                _save_cache(data)
        except Exception as e:
            logger.error(f"Background refresh failed: {e}")


def start_background_refresh() -> None:
    """Start background cache refresh thread."""
    thread = threading.Thread(target=_background_refresh_worker, daemon=True)
    thread.start()
    logger.info("🔁 Background cache refresh started")


def invalidate_cache() -> None:
    """Force cache invalidation (e.g., after market close for fresh next day)."""
    if CACHE_FILE.exists():
        CACHE_FILE.unlink()
        logger.info("🗑️ Cache invalidated")


def get_cache_stats() -> Dict:
    """Get cache statistics for debugging."""
    if not CACHE_FILE.exists():
        return {"status": "empty", "stocks": 0, "age": None, "size_kb": 0}

    try:
        with open(CACHE_FILE) as f:
            cache = json.load(f)
        age = time.time() - cache.get("_last_refresh", 0)
        return {
            "status": "fresh" if age < _get_ttl() else "stale",
            "stocks": cache.get("_stock_count", 0),
            "age": round(age),
            "size_kb": round(CACHE_FILE.stat().st_size / 1024),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
