"""iTick REST + WebSocket data feed for IDX stocks."""
import hashlib
import time
from datetime import datetime
from typing import List, Optional

import aiohttp
import requests

from src.config import settings
from src.feed import Kline, Quote, DataFeed

BASE_URL = "https://api.itick.org"
WS_URL = "wss://api.itick.org"


class ITickFeed(DataFeed):
    def __init__(self, api_key: str = ""):
        self.api_key = api_key or settings.itick_api_key
        self._session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"token": self.api_key, "accept": "application/json"}
            )
        return self._session

    async def get_quote(self, symbol: str) -> Optional[Quote]:
        """Fetch real-time quote for IDX stock."""
        session = await self._ensure_session()
        try:
            url = f"{BASE_URL}/symbol/list?type=stock&region=ID&code={symbol}"
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                if not data.get("data"):
                    return None

            # Get actual quote
            url = f"{BASE_URL}/quote?symbol={symbol}&region=ID"
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                q = data.get("data", {})
                return Quote(
                    symbol=symbol,
                    price=q.get("ld", 0),
                    open=q.get("o", 0),
                    high=q.get("h", 0),
                    low=q.get("l", 0),
                    volume=int(q.get("v", 0)),
                    value=float(q.get("tu", 0)),
                    timestamp=datetime.fromtimestamp(q.get("t", time.time()) / 1000),
                )
        except Exception as e:
            print(f"[ITickFeed] Error fetching quote for {symbol}: {e}")
            return None

    async def get_klines(
        self, symbol: str, interval: str = "1d", limit: int = 100
    ) -> List[Kline]:
        """Fetch historical klines/candlesticks."""
        interval_map = {
            "1m": "1",
            "5m": "2",
            "15m": "3",
            "30m": "4",
            "1h": "5",
            "1d": "8",
            "1w": "9",
            "1M": "10",
        }
        itick_interval = interval_map.get(interval, "8")
        session = await self._ensure_session()
        try:
            url = (
                f"{BASE_URL}/kline?symbol={symbol}&region=ID"
                f"&interval={itick_interval}&limit={limit}"
            )
            async with session.get(url) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                klines = []
                for k in data.get("data", []):
                    klines.append(
                        Kline(
                            symbol=symbol,
                            open=k.get("o", 0),
                            high=k.get("h", 0),
                            low=k.get("l", 0),
                            close=k.get("c", 0),
                            volume=int(k.get("v", 0)),
                            timestamp=datetime.fromtimestamp(
                                k.get("t", time.time()) / 1000
                            ),
                            interval=interval,
                        )
                    )
                return klines
        except Exception as e:
            print(f"[ITickFeed] Error fetching klines for {symbol}: {e}")
            return []

    async def get_ticker_list(self, region: str = "ID") -> List[dict]:
        """Fetch list of all available tickers for IDX."""
        session = await self._ensure_session()
        try:
            url = f"{BASE_URL}/symbol/list?type=stock&region={region}"
            async with session.get(url) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                return data.get("data", [])
        except Exception as e:
            print(f"[ITickFeed] Error fetching ticker list: {e}")
            return []

    async def health(self) -> bool:
        """Check if feed is alive."""
        session = await self._ensure_session()
        try:
            url = f"{BASE_URL}/symbol/list?type=stock&region=ID&limit=1"
            async with session.get(url) as resp:
                return resp.status == 200
        except Exception:
            return False
