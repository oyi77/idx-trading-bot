"""Massive.com Data Feed — Indonesian stock market data."""
import logging
import os
import json
import urllib.request
from typing import Optional, List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class MassiveFeed:
    """Massive.com API client for Indonesian stock data."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.massive.com/v1"

    def _get(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """Make GET request to Massive API."""
        try:
            url = f"{self.base_url}{endpoint}"
            if params:
                params["api_key"] = self.api_key
                query = "&".join(f"{k}={v}" for k, v in params.items())
                url = f"{url}?{query}"
            else:
                url = f"{url}?api_key={self.api_key}"

            req = urllib.request.Request(url, headers={"User-Agent": "VilonaSahamBot/1.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read())
        except Exception as e:
            logger.error(f"Massive API error: {e}")
            return None

    def get_quote(self, symbol: str) -> Optional[Dict]:
        """Get real-time quote for an Indonesian stock."""
        data = self._get("/quote", {"symbol": symbol})
        if data and ("price" in data or "last" in data):
            return {
                "symbol": symbol,
                "price": data.get("price") or data.get("last", 0),
                "change": data.get("change", 0),
                "change_pct": data.get("change_pct", 0),
                "high": data.get("high", 0),
                "low": data.get("low", 0),
                "open": data.get("open", 0),
                "prev_close": data.get("prev_close", 0),
                "volume": data.get("volume", 0),
                "timestamp": data.get("timestamp", datetime.now().isoformat()),
            }
        return None

    def get_ohlcv(
        self, symbol: str, timeframe: str = "1d", limit: int = 100
    ) -> Optional[List[Dict]]:
        """Get OHLCV candles for an Indonesian stock.

        Args:
            symbol: Stock ticker (e.g. "BBCA", "BBRI").
            timeframe: Candle interval — "1m","5m","15m","30m","1h","1d","1wk","1mo".
            limit: Number of candles to return.
        """
        data = self._get("/ohlcv", {
            "symbol": symbol,
            "interval": timeframe,
            "limit": limit,
        })

        if data and isinstance(data, list):
            candles = []
            for d in data:
                candles.append({
                    "timestamp": d.get("timestamp", d.get("t", 0)),
                    "open": d.get("open", d.get("o", 0)),
                    "high": d.get("high", d.get("h", 0)),
                    "low": d.get("low", d.get("l", 0)),
                    "close": d.get("close", d.get("c", 0)),
                    "volume": d.get("volume", d.get("v", 0)),
                })
            return candles
        return None

    def health(self) -> Optional[Dict]:
        """Check if Massive API is reachable."""
        try:
            url = f"{self.base_url}/ping?api_key={self.api_key}"
            req = urllib.request.Request(url, headers={"User-Agent": "VilonaSahamBot/1.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                return {"status": "ok", "source": "massive"}
        except Exception as e:
            logger.warning(f"Massive health check failed: {e}")
            return {"status": "error", "source": "massive", "error": str(e)}


# Singleton
massive_feed = None


def get_massive_feed():
    global massive_feed
    if massive_feed is None:
        api_key = os.environ.get("massive_api_key", "")
        if api_key:
            massive_feed = MassiveFeed(api_key)
    return massive_feed
