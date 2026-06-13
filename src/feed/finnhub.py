"""Finnhub data feed — alternative for IDX + global data."""
import time
from datetime import datetime
from typing import List, Optional

import aiohttp

from src.config import settings
from src.feed import Kline, Quote, DataFeed

BASE = "https://finnhub.io/api/v1"


class FinnhubFeed(DataFeed):
    def __init__(self, api_key: str = ""):
        self.api_key = api_key or settings.finnhub_api_key
        self._session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def _idx_to_finnhub(self, symbol: str) -> str:
        """Convert IDX code (e.g. TLKM) to Finnhub format."""
        return f"{symbol}.JK"

    async def get_quote(self, symbol: str) -> Optional[Quote]:
        session = await self._ensure_session()
        try:
            symbol_fh = self._idx_to_finnhub(symbol)
            url = f"{BASE}/quote?symbol={symbol_fh}&token={self.api_key}"
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                if not data or data.get("c", 0) == 0:
                    return None
                return Quote(
                    symbol=symbol,
                    price=data.get("c", 0),  # current
                    open=data.get("o", 0),
                    high=data.get("h", 0),
                    low=data.get("l", 0),
                    volume=0,  # Finnhub quote endpoint doesn't provide volume
                    value=0,
                    timestamp=datetime.now(),
                )
        except Exception as e:
            print(f"[FinnhubFeed] Error: {e}")
            return None

    async def get_klines(
        self, symbol: str, interval: str = "1d", limit: int = 100
    ) -> List[Kline]:
        session = await self._ensure_session()
        try:
            symbol_fh = self._idx_to_finnhub(symbol)
            resolution = {"1m": "1", "5m": "5", "15m": "15", "30m": "30", "1h": "60", "1d": "D", "1w": "W", "1M": "M"}.get(interval, "D")
            to_ts = int(time.time())
            from_ts = to_ts - (limit * 86400)  # approximate

            url = f"{BASE}/stock/candle?symbol={symbol_fh}&resolution={resolution}&from={from_ts}&to={to_ts}&token={self.api_key}"
            async with session.get(url) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                if data.get("s") != "ok":
                    return []

                klines = []
                for i in range(len(data.get("t", []))):
                    klines.append(
                        Kline(
                            symbol=symbol,
                            open=data["o"][i],
                            high=data["h"][i],
                            low=data["l"][i],
                            close=data["c"][i],
                            volume=data["v"][i],
                            timestamp=datetime.fromtimestamp(data["t"][i]),
                            interval=interval,
                        )
                    )
                return klines[:limit]
        except Exception as e:
            print(f"[FinnhubFeed] Error: {e}")
            return []

    async def health(self) -> bool:
        return self.api_key != ""
