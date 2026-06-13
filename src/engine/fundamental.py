"""Fundamental data analysis for IDX stocks.
Fetches real data via yfinance (Yahoo Finance).
Covers all IDX stocks with .JK suffix.
"""
from dataclasses import dataclass
from typing import Dict, Optional
import asyncio


@dataclass
class FundamentalData:
    symbol: str
    name: str = ""
    sector: str = ""
    industry: str = ""
    market_cap: float = 0
    per: float = 0  # Price to Earnings Ratio
    pbv: float = 0  # Price to Book Value
    roe: float = 0  # Return on Equity (%)
    roa: float = 0  # Return on Assets (%)
    der: float = 0  # Debt to Equity Ratio
    eps: float = 0  # Earnings Per Share (TTM)
    dividend_yield: float = 0  # in %
    ev_ebitda: float = 0
    net_profit_margin: float = 0
    revenue_ttm: float = 0
    revenue_growth: float = 0  # YoY %
    high_52w: float = 0
    low_52w: float = 0
    shares_outstanding: float = 0

    def is_undervalued(self) -> bool:
        """Value check: low PER + low PBV = potensi undervalued."""
        return 0 < self.per < 12 and 0 < self.pbv < 1.5

    def is_growth(self) -> bool:
        """Growth check: ROE > 15% + revenue growth positive."""
        return self.roe > 15 and self.revenue_growth > 5

    def is_high_divider(self) -> bool:
        """Dividend check: yield > 3%."""
        return self.dividend_yield > 3

    def valuation_status(self) -> str:
        """Overall valuation description."""
        if self.is_undervalued():
            return "Undervalued ⚡"
        per_str = f"Wajar" if self.per < 20 else "Premium"
        return per_str

    def summary(self) -> str:
        """One-line fundamental snapshot."""
        return (
            f"{self.symbol} | {self.name}\n"
            f"  PER: {self.per:.1f} | PBV: {self.pbv:.2f} | "
            f"ROE: {self.roe:.1f}% | DER: {self.der:.2f}\n"
            f"  MCap: {self._format_billion(self.market_cap)} | "
            f"DY: {self.dividend_yield:.1f}% | "
            f"Revenue: {self._format_billion(self.revenue_ttm)}"
        )

    def detail(self) -> str:
        lines = [
            f"📊 *Fundamental {self.symbol}*",
            f"  Nama: {self.name}",
            f"  Sektor: {self.sector} / {self.industry}",
            f"  MCap: {self._format_billion(self.market_cap)}",
            f"  PER: {self.per:.1f}x | PBV: {self.pbv:.2f}x",
            f"  ROE: {self.roe:.1f}% | ROA: {self.roa:.1f}%",
            f"  DER: {self.der:.2f} | EPS: Rp{self.eps:,.0f}",
            f"  Div Yield: {self.dividend_yield:.2f}%",
            f"  Revenue (TTM): {self._format_billion(self.revenue_ttm)}",
            f"  Revenue Growth: {self.revenue_growth:+.1f}%",
            f"  EV/EBITDA: {self.ev_ebitda:.1f}x" if self.ev_ebitda else None,
            f"  Net Margin: {self.net_profit_margin:.1f}%",
            f"  52w Range: Rp{self.low_52w:,.0f} - Rp{self.high_52w:,.0f}",
            f"  Valuasi: {self.valuation_status()}",
        ]
        return "\n".join(l for l in lines if l)

    @staticmethod
    def _format_billion(value: float) -> str:
        if value >= 1_000_000_000_000:
            return f"{value / 1_000_000_000_000:.2f}T"
        elif value >= 1_000_000_000:
            return f"{value / 1_000_000_000:.2f}B"
        elif value >= 1_000_000:
            return f"{value / 1_000_000:.2f}M"
        return f"{value:.0f}"


class FundamentalEngine:
    """Fetch and analyze fundamental data from Yahoo Finance via yfinance.
    
    Primary: yfinance (synchronous wrapper, run in thread pool).
    Fallback: cached database if available.
    """

    async def fetch(self, symbol: str) -> Optional[FundamentalData]:
        """Fetch fundamental data for an IDX stock.
        
        Uses yfinance under the hood. Runs in a thread to avoid
        blocking the async event loop.
        """
        try:
            data = await asyncio.to_thread(self._fetch_sync, symbol)
            return data
        except Exception as e:
            print(f"[FundamentalEngine] Error fetching {symbol}: {e}")
            return None

    def _fetch_sync(self, symbol: str) -> Optional[FundamentalData]:
        import yfinance as yf

        ticker = yf.Ticker(f"{symbol}.JK")
        info = ticker.info

        if not info or info.get("regularMarketPrice") is None:
            # Maybe it's already without .JK — try anyway
            ticker = yf.Ticker(symbol)
            info = ticker.info
            if not info or info.get("regularMarketPrice") is None:
                return None

        # Parse fields safely
        def _safe_float(val, default=0.0):
            if val is None:
                return default
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        def _safe_decimal_to_pct(val):
            """Convert decimal (0.15) to percentage (15.0)."""
            v = _safe_float(val)
            return v * 100 if v != 0 else 0.0

        roe = _safe_decimal_to_pct(info.get("returnOnEquity"))
        roa = _safe_decimal_to_pct(info.get("returnOnAssets"))
        # Yahoo Finance returns dividendYield already in % for IDX stocks
        div_yield = _safe_float(info.get("dividendYield"))
        # Fallback: use trailingAnnualDividendYield (proper decimal)
        if div_yield == 0 and info.get("trailingAnnualDividendYield"):
            div_yield = _safe_decimal_to_pct(info.get("trailingAnnualDividendYield"))
        # Second fallback: manual calc
        if div_yield == 0 and info.get("dividendRate") and info.get("currentPrice"):
            div_yield = (info.get("dividendRate", 0) / info.get("currentPrice", 1)) * 100
        profit_margin = _safe_decimal_to_pct(info.get("profitMargins"))
        revenue_growth = _safe_decimal_to_pct(info.get("revenueGrowth"))

        return FundamentalData(
            symbol=symbol,
            name=info.get("longName") or info.get("shortName", ""),
            sector=info.get("sector", ""),
            industry=info.get("industry", ""),
            market_cap=_safe_float(info.get("marketCap")),
            per=_safe_float(info.get("trailingPE")),
            pbv=_safe_float(info.get("priceToBook")),
            roe=roe,
            roa=roa,
            der=_safe_float(info.get("debtToEquity")),
            eps=_safe_float(info.get("trailingEps")),
            dividend_yield=div_yield,
            ev_ebitda=_safe_float(info.get("enterpriseToEbitda")),
            net_profit_margin=profit_margin,
            revenue_ttm=_safe_float(info.get("totalRevenue")),
            revenue_growth=revenue_growth,
            high_52w=_safe_float(info.get("fiftyTwoWeekHigh")),
            low_52w=_safe_float(info.get("fiftyTwoWeekLow")),
            shares_outstanding=_safe_float(info.get("sharesOutstanding")),
        )

    def screen(self, data_list: list[FundamentalData]) -> list[FundamentalData]:
        """Screen stocks by value criteria (LKH-style)."""
        return [d for d in data_list if d.per > 0 and d.is_undervalued()]
