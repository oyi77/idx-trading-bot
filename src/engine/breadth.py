"""Market Breadth Indicators — overall market health.

Computes from IDX stock universe:
  • Advance/Decline ratio — stocks up vs down today
  • Stocks above MA50 — % of stocks above 50-day MA
  • New Highs / New Lows — 52-week
  • Total volume vs average
  • Breadth score (0-100)

Usage:
  /breadth — full market breadth report
  /breadth quick — compact

Data: Yahoo Finance (free) on ~39 major IDX stocks.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


# Major IDX stocks for breadth calculation
BREADTH_SYMBOLS = [
    "BBCA", "BBRI", "BMRI", "BBNI", "BRIS",  # Banking
    "TLKM", "EXCL", "ISAT", "MTEL", "TOWR",    # Telco
    "ASII", "UNTR",                              # Auto/Heavy
    "ADRO", "PTBA", "ITMG", "ANTM", "INCO",     # Mining
    "UNVR", "ICBP", "INDF", "KLBF", "HMSP",    # Consumer
    "GGRM", "CPIN", "JPFA",                     # Agri/Food
    "SMGR", "INTP",                              # Cement
    "PGAS", "AKRA",                              # Energy
    "AMRT", "ACES", "MAPI",                     # Retail
    "BSDE", "CTRA", "PWON",                     # Property
    "MDKA", "BRPT", "MEDC",                     # Others
    "GOTO", "BUKA", "EMTK",                     # Tech
]


@dataclass
class BreadthData:
    timestamp: str
    total_stocks: int = 0
    advancers: int = 0
    decliners: int = 0
    unchanged: int = 0
    ad_ratio: float = 0
    above_ma50: int = 0
    above_ma50_pct: float = 0
    new_highs_52w: int = 0
    new_lows_52w: int = 0
    total_volume: float = 0
    avg_volume: float = 0
    volume_ratio: float = 0  # today vs avg
    breadth_score: int = 50


async def compute_breadth() -> BreadthData:
    """Compute market breadth from Yahoo Finance data."""
    data = BreadthData(timestamp=datetime.now().isoformat())

    try:
        from src.feed.yahoo import YahooFeed
        feed = YahooFeed()

        # Fetch all symbols
        tasks = [feed.get_quote(sym) for sym in BREADTH_SYMBOLS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid = [r for r in results if r and not isinstance(r, Exception)]
        data.total_stocks = len(valid)

        for quote in valid:
            change_pct = float(quote.get("change_pct", 0) or 0)
            price = float(quote.get("price", 0) or 0)

            if change_pct > 0.1:
                data.advancers += 1
            elif change_pct < -0.1:
                data.decliners += 1
            else:
                data.unchanged += 1

            # Check vs MA50 using prev_close and price
            # Simplified: use Yahoo info for 50-day avg if available
            info = quote.get("raw_info", {})
            ma50 = info.get("fiftyDayAverage") or info.get("50DayAverage")
            if ma50 and price:
                if price > ma50:
                    data.above_ma50 += 1

            # 52-week high/low
            high52 = info.get("fiftyTwoWeekHigh")
            low52 = info.get("fiftyTwoWeekLow")
            if price and high52:
                if price >= high52 * 0.98:
                    data.new_highs_52w += 1
            if price and low52:
                if price <= low52 * 1.02:
                    data.new_lows_52w += 1

            # Volume
            vol = float(info.get("regularMarketVolume", 0) or 0)
            avg_vol = float(info.get("averageVolume", 0) or 0)
            data.total_volume += vol
            data.avg_volume += avg_vol

        # Ratios
        if data.total_stocks:
            data.ad_ratio = data.advancers / max(data.decliners, 1)
            data.above_ma50_pct = (data.above_ma50 / data.total_stocks) * 100
            data.volume_ratio = data.total_volume / max(data.avg_volume, 1)

        # Breadth score (0-100)
        score = 50
        if data.ad_ratio > 2:
            score += 20
        elif data.ad_ratio > 1.5:
            score += 10
        elif data.ad_ratio < 0.5:
            score -= 20
        elif data.ad_ratio < 0.7:
            score -= 10

        if data.above_ma50_pct > 60:
            score += 15
        elif data.above_ma50_pct > 45:
            score += 5
        elif data.above_ma50_pct < 30:
            score -= 15

        if data.volume_ratio > 1.5:
            score += 10
        elif data.volume_ratio < 0.7:
            score -= 5

        data.breadth_score = max(0, min(100, score))

    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Breadth compute error: {e}")

    return data


def format_breadth(data: BreadthData) -> str:
    """Format market breadth for Telegram."""
    score_emoji = "🟢" if data.breadth_score >= 60 else ("🟡" if data.breadth_score >= 40 else "🔴")
    signal = "BULLISH" if data.breadth_score >= 60 else ("NEUTRAL" if data.breadth_score >= 40 else "BEARISH")

    out = f"📊 *Market Breadth*\n"
    out += "━━━━━━━━━━━━━━━━━━━━\n\n"

    out += f"{score_emoji} *Breadth Score: {data.breadth_score}/100* — {signal}\n\n"

    out += f"*Advance/Decline* (dari {data.total_stocks} saham)\n"
    out += f"  🟢 Advancers: *{data.advancers}*\n"
    out += f"  🔴 Decliners: *{data.decliners}*\n"
    out += f"  ⚪ Unchanged: *{data.unchanged}*\n"
    out += f"  📈 A/D Ratio: *{data.ad_ratio:.1f}x*\n\n"

    out += f"*Trend Strength*\n"
    out += f"  📊 Above MA50: *{data.above_ma50}* ({data.above_ma50_pct:.0f}%)\n"
    out += f"  🔝 New Highs (52w): *{data.new_highs_52w}*\n"
    out += f"  🔻 New Lows (52w): *{data.new_lows_52w}*\n\n"

    out += f"*Volume*\n"
    out += f"  📊 Volume Ratio: *{data.volume_ratio:.1f}x* normal\n\n"

    out += "━━━━━━━━━━━━━━━━━━━━\n"

    if data.breadth_score >= 60:
        out += "💡 Market bullish — banyak saham naik, tren kuat. Fokus entry.\n"
    elif data.breadth_score >= 40:
        out += "💡 Market netral — selektif entry. Cek sektor kuat: `/sector`\n"
    else:
        out += "⚠️ Market bearish — dominan merah, banyak new lows. Kurangi posisi.\n"

    out += "📊 Pre-market context: `/premarket`"

    return out
