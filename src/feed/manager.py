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
        self.rapidapi_feed = None

        if settings.finnhub_api_key and settings.finnhub_api_key != "placeholder":
            try:
                from src.feed.finnhub import FinnhubFeed
                self.finnhub_feed = FinnhubFeed()
                log.info("Finnhub feed available (webhook supplement)")
            except Exception as e:
                log.warning(f"Finnhub feed init failed: {e}")

        if settings.rapidapi_key:
            try:
                from src.feed.rapidapi_idx import RapidAPIFeed
                self.rapidapi_feed = RapidAPIFeed()
                log.info("RapidAPI IDX feed available (broker flow + sectors + symbols)")
            except Exception as e:
                log.warning(f"RapidAPI feed init failed: {e}")

        log.info("FeedManager: Yahoo primary, Finnhub/RapidAPI supplement")

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

    # ── RapidAPI IDX methods ────────────────────────────────────

    async def get_broker_flow(self) -> dict:
        """Get comprehensive broker flow from RapidAPI IDX.
        
        Returns foreign net buy, top brokers, foreign ratio, etc.
        Uses RapidAPI if available, falls back to empty dict.
        """
        if self.rapidapi_feed:
            try:
                return await self.rapidapi_feed.get_broker_flow_summary()
            except Exception as e:
                log.error(f"RapidAPI broker flow failed: {e}")
        return {}

    async def get_sectors(self) -> list:
        """Get IDX sector list."""
        if self.rapidapi_feed:
            try:
                return await self.rapidapi_feed.get_sectors()
            except Exception as e:
                log.error(f"RapidAPI sectors failed: {e}")
        return []

    async def get_symbols(self) -> list:
        """Get all IDX stock symbols."""
        if self.rapidapi_feed:
            try:
                return await self.rapidapi_feed.get_symbols()
            except Exception as e:
                log.error(f"RapidAPI symbols failed: {e}")
        return []
