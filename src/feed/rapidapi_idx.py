"""RapidAPI IDX Market Intelligence — 70+ endpoints for Indonesian stocks.

Confirmed BASIC-tier endpoints:
  - GET /api/main/symbols          → all IDX stock codes
  - GET /api/market-detector/top-broker  → broker flow analysis
  - GET /api/sectors               → sector list

Rate limit: 1 req/sec (BASIC free tier)

Integration pattern: async aiohttp, throttled to 1 req/sec,
returns dict-compatible with Yahoo feed for seamless drop-in.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Optional

import aiohttp

from src.config import settings

log = logging.getLogger(__name__)

BASE_URL = "https://indonesia-stock-exchange-idx.p.rapidapi.com"
DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "accept": "application/json",
}


class RapidAPIFeed:
    """Throttled async client for RapidAPI IDX Market Intelligence."""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or getattr(settings, "rapidapi_key", "")
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_call: float = 0
        self._lock = asyncio.Lock()
        self._symbols_cache: Optional[list[str]] = None

    # ── Session Management ──────────────────────────────────────

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            headers = {
                **DEFAULT_HEADERS,
                "X-RapidAPI-Key": self.api_key,
                "x-rapidapi-host": "indonesia-stock-exchange-idx.p.rapidapi.com",
            }
            timeout = aiohttp.ClientTimeout(total=15)
            self._session = aiohttp.ClientSession(headers=headers, timeout=timeout)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    # ── Throttle ────────────────────────────────────────────────

    async def _throttle(self):
        """Ensure we stay under 1 req/sec for BASIC tier."""
        async with self._lock:
            elapsed = time.monotonic() - self._last_call
            if elapsed < 1.3:
                await asyncio.sleep(1.3 - elapsed)
            self._last_call = time.monotonic()

    # ── HTTP helpers ────────────────────────────────────────────

    async def _get(self, path: str, params: Optional[dict] = None) -> dict:
        """Throttled GET request."""
        await self._throttle()
        session = await self._ensure_session()
        url = f"{BASE_URL}{path}"
        try:
            async with session.get(url, params=params) as resp:
                data = await resp.json()
                if resp.status != 200:
                    log.warning(f"RapidAPI {path} → {resp.status}: {data.get('message','')}")
                return data
        except Exception as e:
            log.error(f"RapidAPI {path} request failed: {e}")
            return {"success": False, "error": str(e)}

    # ── Public API ──────────────────────────────────────────────

    async def get_symbols(self) -> list[str]:
        """Return all IDX stock symbols."""
        data = await self._get("/api/main/symbols")
        if data.get("success"):
            return data.get("data", [])
        return []

    async def get_sectors(self) -> list[dict]:
        """Return list of IDX sectors.
        
        Returns: [{"id": "3", "name": "Keuangan", "alias1": "keuangan"}, ...]
        """
        data = await self._get("/api/sectors")
        if data.get("success"):
            return data.get("data", {}).get("data", [])
        return []

    async def get_top_brokers(
        self,
        market_type: str = "MARKET_TYPE_ALL",
        period: str = "TB_PERIOD_LAST_1_DAY",
        order: str = "ORDER_BY_DESC",
        sort: str = "TB_SORT_BY_TOTAL_VALUE",
    ) -> list[dict]:
        """Get top broker flow data.
        
        Returns list of broker entries with:
          code, name, investor_type, total_value, net_value,
          buy_value, sell_value, total_volume, total_frequency, group
        """
        params = {
            "marketType": market_type,
            "period": period,
            "order": order,
            "sort": sort,
        }
        data = await self._get("/api/market-detector/top-broker", params=params)
        if data.get("success"):
            inner = data.get("data", {})
            return inner.get("data", {}).get("list", [])
        return []

    async def get_broker_flow_summary(self) -> dict:
        """Summarize broker flow: foreign net buy, total value, top brokers.
        
        Returns a dict ready for analysis:
          {
            "foreign_net_buy": float,   # total foreign net buy value
            "total_value": float,        # total market value
            "top_brokers": list[dict],   # top 5 by total value
            "foreign_domestic_ratio": float,
          }
        """
        brokers = await self.get_top_brokers(
            market_type="MARKET_TYPE_ALL",
            period="TB_PERIOD_LAST_1_DAY",
            order="ORDER_BY_DESC",
            sort="TB_SORT_BY_TOTAL_VALUE",
        )
        if not brokers:
            return {}

        total_value = sum(float(b.get("total_value", 0)) for b in brokers)
        foreign_net = sum(
            float(b.get("net_value", 0))
            for b in brokers
            if b.get("group") == "BROKER_GROUP_FOREIGN"
        )
        foreign_buy = sum(
            float(b.get("buy_value", 0))
            for b in brokers
            if b.get("group") == "BROKER_GROUP_FOREIGN"
        )
        foreign_sell = sum(
            float(b.get("sell_value", 0))
            for b in brokers
            if b.get("group") == "BROKER_GROUP_FOREIGN"
        )

        return {
            "foreign_net_buy": foreign_net,
            "foreign_buy": foreign_buy,
            "foreign_sell": foreign_sell,
            "total_value": total_value,
            "top_brokers": sorted(
                brokers,
                key=lambda b: float(b.get("total_value", 0)),
                reverse=True,
            )[:5],
            "foreign_domestic_ratio": foreign_buy / total_value if total_value > 0 else 0,
            "timestamp": datetime.now().isoformat(),
        }

    # ── Stock-specific analysis ─────────────────────────────────

    async def analyze_stock(self, symbol: str) -> dict:
        """Get comprehensive analysis for a single stock.
        
        Combines: broker flow + sector data + symbol list verification.
        Returns dict ready for bot tier-gated output.
        """
        # Verify symbol exists (cached)
        if self._symbols_cache is None:
            self._symbols_cache = await self.get_symbols()
        symbol = symbol.upper()
        if symbol not in self._symbols_cache:
            return {"found": False, "symbol": symbol}

        # Get broker flow
        broker_data = await self.get_broker_flow_summary()

        return {
            "found": True,
            "symbol": symbol,
            "broker_flow": broker_data,
            "source": "rapidapi_idx",
            "timestamp": datetime.now().isoformat(),
        }

    async def health(self) -> dict:
        """Quick health check."""
        try:
            data = await self._get("/api/main/symbols")
            if data.get("success") and isinstance(data.get("data"), list):
                return {
                    "status": "ok",
                    "source": "rapidapi_idx",
                    "symbols_count": len(data["data"]),
                }
            return {"status": "degraded", "source": "rapidapi_idx", "error": str(data)}
        except Exception as e:
            return {"status": "error", "source": "rapidapi_idx", "error": str(e)}
