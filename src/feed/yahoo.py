"""Yahoo Finance data feed — free, no API key required."""
import logging
from datetime import datetime, timedelta
from typing import Optional

import yfinance as yf

from src.feed import DataFeed

log = logging.getLogger(__name__)

# Map our intervals to yfinance periods/intervals
INTERVAL_MAP = {
    "1d": ("3mo", "1d"),
    "60m": ("1mo", "60m"),
    "30m": ("5d", "30m"),
    "15m": ("5d", "15m"),
    "5m": ("2d", "5m"),
    "1wk": ("1y", "1wk"),
    "1mo": ("2y", "1mo"),
}

class YahooFeed(DataFeed):
    """Free data feed via Yahoo Finance. No API key needed."""

    async def get_quote(self, symbol: str) -> Optional[dict]:
        """Get current quote for an IDX stock."""
        try:
            yf_symbol = f"{symbol}.JK"
            ticker = yf.Ticker(yf_symbol)
            info = ticker.info or {}

            price = (
                info.get("currentPrice")
                or info.get("regularMarketPrice")
                or info.get("previousClose")
            )
            if not price:
                # Fallback: try fast_info
                try:
                    fast = ticker.fast_info
                    price = fast.last_price if hasattr(fast, "last_price") else None
                except Exception:
                    pass

            if not price:
                log.warning(f"No price found for {symbol}")
                return None

            change = info.get("regularMarketChange", 0)
            change_pct = info.get("regularMarketChangePercent", 0)
            prev_close = info.get("previousClose", price)
            high = info.get("regularMarketDayHigh")
            low = info.get("regularMarketDayLow")
            volume = info.get("regularMarketVolume", 0)
            name = info.get("longName") or info.get("shortName") or symbol

            return {
                "symbol": symbol,
                "price": price,
                "change": round(change, 2) if change else None,
                "change_pct": round(change_pct, 2) if change_pct else None,
                "high": high,
                "low": low,
                "open": info.get("regularMarketOpen"),
                "prev_close": prev_close,
                "volume": volume,
                "name": name,
                "source": "yahoo",
                "timestamp": datetime.now().isoformat(),
                "raw_info": info,
            }
        except Exception as e:
            log.error(f"Yahoo quote error for {symbol}: {e}")
            return None

    async def get_global_quote(self, symbol: str) -> Optional[dict]:
        """Get quote for a global/non-IDX symbol (no .JK suffix)."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}

            price = (
                info.get("currentPrice")
                or info.get("regularMarketPrice")
                or info.get("previousClose")
            )
            if not price:
                try:
                    fast = ticker.fast_info
                    price = fast.last_price if hasattr(fast, "last_price") else None
                except Exception:
                    pass

            if not price:
                log.warning(f"No price found for {symbol}")
                return None

            change = info.get("regularMarketChange", 0)
            change_pct = info.get("regularMarketChangePercent", 0)
            prev_close = info.get("previousClose", price)
            name = info.get("longName") or info.get("shortName") or symbol

            return {
                "symbol": symbol,
                "price": price,
                "change": round(change, 2) if change else None,
                "change_pct": round(change_pct, 2) if change_pct else None,
                "high": info.get("regularMarketDayHigh"),
                "low": info.get("regularMarketDayLow"),
                "open": info.get("regularMarketOpen"),
                "prev_close": prev_close,
                "volume": info.get("regularMarketVolume", 0),
                "name": name,
                "source": "yahoo",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            log.error(f"Yahoo global quote error for {symbol}: {e}")
            return None

    async def get_klines(
        self, symbol: str, interval: str = "1d", limit: int = 100
    ) -> list:
        """Get historical OHLCV data."""
        try:
            yf_symbol = f"{symbol}.JK"
            period, yf_interval = INTERVAL_MAP.get(interval, ("3mo", "1d"))

            ticker = yf.Ticker(yf_symbol)
            hist = ticker.history(period=period, interval=yf_interval)

            if hist.empty:
                log.warning(f"No historical data for {symbol}")
                return []

            klines = []
            for idx, row in hist.iterrows():
                kline = {
                    "timestamp": int(idx.timestamp()),
                    "open": round(float(row["Open"]), 2),
                    "high": round(float(row["High"]), 2),
                    "low": round(float(row["Low"]), 2),
                    "close": round(float(row["Close"]), 2),
                    "volume": int(row["Volume"]),
                }
                klines.append(kline)

            # Limit and return
            return klines[-limit:] if len(klines) > limit else klines

        except Exception as e:
            log.error(f"Yahoo klines error for {symbol}: {e}")
            return []

    async def search_symbols(self, query: str) -> list:
        """Search for stocks by name/symbol. Uses Yahoo search."""
        try:
            # yfinance doesn't have great search, use a simple approach
            ticker = yf.Ticker(f"{query.upper()}.JK")
            info = ticker.info or {}
            if info.get("currentPrice") or info.get("regularMarketPrice"):
                name = info.get("longName") or info.get("shortName") or query
                return [{"symbol": query.upper(), "name": name, "source": "yahoo"}]
            return []
        except Exception:
            return []

    async def health(self) -> dict:
        """Check if Yahoo Finance is reachable."""
        try:
            import yfinance as yf
            ticker = yf.Ticker("BBCA.JK")
            info = ticker.info or {}
            name = info.get("longName", "")
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            return {
                "status": "ok" if price else "degraded",
                "source": "yahoo",
                "last_price": price,
                "symbol": "BBCA" if name else None,
            }
        except Exception as e:
            return {"status": "error", "source": "yahoo", "error": str(e)}

    async def get_company_profile(self, symbol: str) -> Optional[dict]:
        """Get company fundamental data."""
        try:
            yf_symbol = f"{symbol}.JK"
            ticker = yf.Ticker(yf_symbol)
            info = ticker.info or {}

            if not info or not info.get("longName"):
                return None

            return {
                "symbol": symbol,
                "name": info.get("longName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "pb_ratio": info.get("priceToBook"),
                "roe": info.get("returnOnEquity"),
                "der": info.get("debtToEquity"),
                "dividend_yield": info.get("dividendYield"),
                "eps": info.get("trailingEps"),
                "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
                "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
                "avg_volume": info.get("averageVolume"),
                "source": "yahoo",
            }
        except Exception as e:
            log.error(f"Yahoo profile error for {symbol}: {e}")
            return None
