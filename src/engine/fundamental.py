"""Fundamental analysis engine — PER, PBV, ROE, EPS, Dividend from Yahoo Finance."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import yfinance as yf

logger = logging.getLogger(__name__)


@dataclass
class FundamentalData:
    """Fundamental metrics for a stock."""
    symbol: str = ""
    name: str = ""
    sector: str = ""
    industry: str = ""
    per: float = 0.0
    forward_per: float = 0.0
    pbv: float = 0.0
    roe: float = 0.0
    der: float = 0.0
    eps: float = 0.0
    dividend_yield: float = 0.0
    market_cap: float = 0.0
    revenue_growth: float = 0.0
    high_52w: float = 0.0
    low_52w: float = 0.0

    def is_undervalued(self) -> bool:
        if self.per <= 0:
            return False
        return self.per < 15 and self.pbv < 2.0

    def _format_billion(self, value: float) -> str:
        if value >= 1e12:
            return f"Rp{value / 1e12:.1f}T"
        if value >= 1e9:
            return f"Rp{value / 1e9:.1f}B"
        return f"Rp{value:,.0f}"


class FundamentalEngine:
    """Fetch fundamental data for IDX stocks via Yahoo Finance."""

    async def fetch(self, symbol: str) -> Optional[FundamentalData]:
        """Get fundamental metrics for a stock."""
        try:
            ticker = yf.Ticker(f"{symbol}.JK")
            info = ticker.info

            if not info or info.get("trailingPE") is None:
                logger.warning("No fundamental data for %s", symbol)
                return None

            return FundamentalData(
                symbol=symbol,
                name=info.get("shortName", symbol),
                sector=info.get("sector", "N/A"),
                industry=info.get("industry", "N/A"),
                per=info.get("trailingPE") or 0,
                forward_per=info.get("forwardPE") or 0,
                pbv=info.get("priceToBook") or 0,
                roe=(info.get("returnOnEquity") or 0) * 100,
                der=info.get("debtToEquity") or 0,
                eps=info.get("trailingEps") or 0,
                dividend_yield=info.get("dividendYield") or 0,
                market_cap=info.get("marketCap") or 0,
                revenue_growth=(info.get("revenueGrowth") or 0) * 100,
                high_52w=info.get("fiftyTwoWeekHigh") or 0,
                low_52w=info.get("fiftyTwoWeekLow") or 0,
            )
        except Exception as e:
            logger.warning("Fundamental fetch failed for %s: %s", symbol, e)
            return None
