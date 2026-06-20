"""Finnhub Data Feed — Real-time market data from Finnhub API."""
import logging
import urllib.request
import json
from typing import Optional, List, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class FinnhubFeed:
    """Finnhub API client for real-time market data."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://finnhub.io/api/v1"
    
    def _get(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """Make GET request to Finnhub API."""
        try:
            url = f"{self.base_url}{endpoint}"
            if params:
                params["token"] = self.api_key
                query = "&".join(f"{k}={v}" for k, v in params.items())
                url = f"{url}?{query}"
            else:
                url = f"{url}?token={self.api_key}"
            
            req = urllib.request.Request(url, headers={"User-Agent": "VilonaSahamBot/1.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read())
        except Exception as e:
            logger.error(f"Finnhub API error: {e}")
            return None
    
    def get_quote(self, symbol: str) -> Optional[Dict]:
        """Get real-time quote for a symbol."""
        data = self._get("/quote", {"symbol": symbol})
        if data and "c" in data:
            return {
                "symbol": symbol,
                "price": data["c"],
                "change": data.get("d", 0),
                "change_pct": data.get("dp", 0),
                "high": data.get("h", 0),
                "low": data.get("l", 0),
                "open": data.get("o", 0),
                "prev_close": data.get("pc", 0),
            }
        return None
    
    def get_candles(self, symbol: str, resolution: str = "D", days: int = 30) -> Optional[List[Dict]]:
        """Get OHLCV candles."""
        import time
        to_ts = int(time.time())
        from_ts = to_ts - (days * 86400)
        
        data = self._get("/stock/candle", {
            "symbol": symbol,
            "resolution": resolution,
            "from": from_ts,
            "to": to_ts,
        })
        
        if data and data.get("s") == "ok":
            candles = []
            for i in range(len(data["t"])):
                candles.append({
                    "timestamp": data["t"][i],
                    "open": data["o"][i],
                    "high": data["h"][i],
                    "low": data["l"][i],
                    "close": data["c"][i],
                    "volume": data["v"][i],
                })
            return candles
        return None
    
    def get_company_news(self, symbol: str, days: int = 7) -> Optional[List[Dict]]:
        """Get company news."""
        import time
        to_date = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        data = self._get("/company-news", {
            "symbol": symbol,
            "from": from_date,
            "to": to_date,
        })
        
        if data:
            return [{
                "headline": n.get("headline", ""),
                "source": n.get("source", ""),
                "url": n.get("url", ""),
                "datetime": n.get("datetime", ""),
                "summary": n.get("summary", ""),
            } for n in data[:10]]
        return None


# Singleton
finnhub_feed = None

def get_finnhub_feed():
    global finnhub_feed
    if finnhub_feed is None:
        import os
        api_key = os.environ.get("finnhub_api_key", "")
        if api_key:
            finnhub_feed = FinnhubFeed(api_key)
    return finnhub_feed
