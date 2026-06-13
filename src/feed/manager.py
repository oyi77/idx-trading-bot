"""Feed factory — Yahoo Finance primary, Finnhub webhook as supplement."""
import logging
from typing import Optional

from src.config import settings
from src.feed import DataFeed
from src.feed.yahoo import YahooFeed

log = logging.getLogger(__name__)


class FeedManager:
    """Manages data feeds — Yahoo primary, Finnhub webhook supplement."""

    def __init__(self):
        self.yahoo = YahooFeed()
        self.finnhub_feed = None

        if settings.finnhub_api_key and settings.finnhub_api_key != "placeholder":
            try:
                from src.feed.finnhub import FinnhubFeed
                self.finnhub_feed = FinnhubFeed()
                log.info("Finnhub feed available (webhook supplement)")
            except Exception as e:
                log.warning(f"Finnhub feed init failed: {e}")

        log.info("FeedManager: Yahoo Finance primary, Finnhub supplement")

    async def get_quote(self, symbol: str) -> Optional[dict]:
        """Get quote from Yahoo Finance."""
        try:
            return await self.yahoo.get_quote(symbol)
        except Exception as e:
            log.error(f"Yahoo quote failed for {symbol}: {e}")
            if self.finnhub_feed:
                try:
                    return await self.finnhub_feed.get_quote(symbol)
                except Exception:
                    pass
        return None

    async def get_klines(
        self, symbol: str, interval: str = "1d", limit: int = 100
    ) -> list:
        """Get historical OHLCV data from Yahoo Finance."""
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
