"""Feed factory — RapidAPI IDX primary (real-time), Yahoo fallback (delay 15m)."""
import logging
from datetime import datetime, timedelta
from typing import Optional

from src.config import settings
from src.feed import DataFeed
from src.feed.yahoo import YahooFeed

log = logging.getLogger(__name__)


class FeedManager:
    """Manages data feeds with auto-fallback.

    Priority chain: RapidAPI IDX (real-time) → Yahoo (15 min delay)
    RapidAPI IDX provides: OHLCV, broker flow, sectors, company data
    """

    def __init__(self):
        self.yahoo = YahooFeed()
        self.rapidapi = None
        self._rapidapi_available: bool | None = None

        if settings.rapidapi_key:
            try:
                from src.feed.rapidapi_idx import RapidAPIFeed
                self.rapidapi = RapidAPIFeed()
                log.info("RapidAPI IDX feed initialized (real-time)")
            except Exception as e:
                log.warning(f"RapidAPI init failed: {e}")
        else:
            log.info("RapidAPI key not configured — using Yahoo only")

    async def _check_rapidapi(self) -> bool:
        """Lazy-check RapidAPI availability."""
        if self._rapidapi_available is not None:
            return self._rapidapi_available
        if self.rapidapi is None:
            self._rapidapi_available = False
            return False
        try:
            health = await self.rapidapi.health()
            self._rapidapi_available = health.get("status") == "ok"
            if self._rapidapi_available:
                log.info("RapidAPI IDX: ✅ REAL-TIME ACTIVE")
            else:
                log.warning("RapidAPI IDX: ❌ degraded, using Yahoo")
        except Exception as e:
            log.warning(f"RapidAPI health check: {e}")
            self._rapidapi_available = False
        return self._rapidapi_available

    @property
    def is_realtime(self) -> bool:
        return self._rapidapi_available is True

    @property
    def data_source_label(self) -> str:
        if self._rapidapi_available:
            return "real-time (IDX)"
        return "delay 15 menit (Yahoo)"

    async def get_quote(self, symbol: str) -> Optional[dict]:
        """Get quote — RapidAPI IDX real-time first, Yahoo fallback."""
        # Try RapidAPI IDX
        if await self._check_rapidapi():
            try:
                candle = await self.rapidapi.get_latest_price(symbol)
                if candle:
                    close = candle.get("close", 0)
                    prev_close = candle.get("open", close)  # approximate
                    change_pct = ((close - prev_close) / prev_close * 100) if prev_close else 0
                    return {
                        "price": close,
                        "open": candle.get("open", 0),
                        "high": candle.get("high", 0),
                        "low": candle.get("low", 0),
                        "volume": candle.get("volume", 0),
                        "value": candle.get("value", 0),
                        "change_pct": change_pct,
                        "source": "rapidapi_idx",
                    }
            except Exception as e:
                log.warning(f"RapidAPI quote failed for {symbol}: {e}")

        # Fallback: Yahoo
        try:
            return await self.yahoo.get_quote(symbol)
        except Exception as e:
            log.error(f"Yahoo quote failed for {symbol}: {e}")
        return None

    async def get_klines(
        self, symbol: str, interval: str = "1d", limit: int = 100
    ) -> list:
        """Get historical OHLCV — RapidAPI IDX first, Yahoo fallback."""
        # Map bot interval → RapidAPI interval
        interval_map = {"1d": "daily", "1w": "weekly", "1M": "monthly", "1m": "daily"}

        # Try RapidAPI IDX
        if await self._check_rapidapi():
            try:
                api_interval = interval_map.get(interval, "daily")
                candles = await self.rapidapi.get_klines(symbol, api_interval, limit)
                if candles:
                    # Convert to dict format expected by bot
                    result = []
                    for c in candles:
                        result.append({
                            "open": c.get("open", 0),
                            "high": c.get("high", 0),
                            "low": c.get("low", 0),
                            "close": c.get("close", 0),
                            "volume": c.get("volume", 0),
                            "timestamp": c.get("date", ""),
                        })
                    return result
            except Exception as e:
                log.warning(f"RapidAPI klines failed for {symbol}: {e}")

        # Fallback: Yahoo
        try:
            return await self.yahoo.get_klines(symbol, interval, limit)
        except Exception as e:
            log.error(f"Yahoo klines failed for {symbol}: {e}")
        return []

    async def get_company_profile(self, symbol: str) -> Optional[dict]:
        """Get company fundamental data from Yahoo."""
        try:
            return await self.yahoo.get_company_profile(symbol)
        except Exception as e:
            log.error(f"Yahoo profile failed for {symbol}: {e}")
        return None

    async def search_symbols(self, query: str) -> list:
        """Search stocks by name/symbol."""
        try:
            return await self.yahoo.search_symbols(query)
        except Exception as e:
            log.error(f"Yahoo search failed for {query}: {e}")
        return []

    # ── RapidAPI IDX methods ────────────────────────────────────

    async def get_broker_flow(self) -> dict:
        """Get comprehensive broker flow from RapidAPI IDX."""
        if self.rapidapi:
            try:
                return await self.rapidapi.get_broker_flow_summary()
            except Exception as e:
                log.error(f"RapidAPI broker flow failed: {e}")
        return {}

    async def get_sectors(self) -> list:
        """Get IDX sector list."""
        if self.rapidapi:
            try:
                return await self.rapidapi.get_sectors()
            except Exception as e:
                log.error(f"RapidAPI sectors failed: {e}")
        return []

    async def get_symbols(self) -> list:
        """Get all IDX stock symbols."""
        if self.rapidapi:
            try:
                return await self.rapidapi.get_symbols()
            except Exception as e:
                log.error(f"RapidAPI symbols failed: {e}")
        return []
