"""Market Mapper — Daily & Weekly market mapping for IDX.

Daily Mapping:
  - IHSG trend + key levels
  - Top movers (gainers/losers)
  - Sector rotation
  - Foreign flow summary
  - Hot stocks to watch

Weekly Mapping:
  - Weekly sector performance
  - Weekly top performers
  - Market breadth trend
  - Key events calendar
  - Week-ahead outlook
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class DailyMap:
    """Daily market mapping output."""
    date: str
    ihsg_close: float = 0.0
    ihsg_change_pct: float = 0.0
    ihsg_trend: str = ""        # "bullish" | "bearish" | "sideways"
    ihsg_support: float = 0.0
    ihsg_resistance: float = 0.0
    top_gainers: List[Dict] = field(default_factory=list)   # [{symbol, change_pct, volume}]
    top_losers: List[Dict] = field(default_factory=list)
    sector_summary: List[Dict] = field(default_factory=list)  # [{sector, change_pct}]
    hot_stocks: List[Dict] = field(default_factory=list)     # signals for today
    market_sentiment: str = ""   # "Risk-On" | "Risk-Off" | "Neutral"
    summary: str = ""


@dataclass
class WeeklyMap:
    """Weekly market mapping output."""
    week_start: str
    week_end: str
    ihsg_weekly_change: float = 0.0
    weekly_winners: List[Dict] = field(default_factory=list)
    weekly_losers: List[Dict] = field(default_factory=list)
    sector_rotation: List[Dict] = field(default_factory=list)
    breadth_trend: str = ""
    key_levels: Dict = field(default_factory=dict)
    week_ahead_outlook: str = ""
    summary: str = ""


async def generate_daily_map() -> DailyMap:
    """Generate daily market mapping using available engines."""
    from src.engine.screener_cache import fetch_all_cached
    from src.engine.signal_engine import scan_signals

    now = datetime.now()
    daily = DailyMap(date=now.strftime("%d %B %Y"))

    data = await fetch_all_cached()
    if not data:
        daily.summary = "Data tidak tersedia — market mungkin belum buka."
        return daily

    # ── Calculate daily changes ──
    movers = []
    for sym, bars in data.items():
        if not isinstance(bars, list) or len(bars) < 2:
            continue
        try:
            prev_close = bars[-2]["close"]
            curr_close = bars[-1]["close"]
            curr_vol = bars[-1]["volume"]
            if prev_close > 0:
                change_pct = (curr_close - prev_close) / prev_close * 100
                movers.append({
                    "symbol": sym,
                    "price": curr_close,
                    "change_pct": round(change_pct, 2),
                    "volume": int(curr_vol),
                })
        except (KeyError, IndexError, ZeroDivisionError):
            continue

    if not movers:
        daily.summary = "Tidak ada data pergerakan hari ini."
        return daily

    # Sort movers
    movers.sort(key=lambda m: m["change_pct"], reverse=True)
    daily.top_gainers = movers[:10]
    daily.top_losers = movers[-10:]
    daily.top_losers.reverse()

    # ── IHSG approximation (top 10 weighted) ──
    if movers:
        avg_change = sum(m["change_pct"] for m in movers) / len(movers)
        daily.ihsg_change_pct = round(avg_change, 2)
        if avg_change > 0.5:
            daily.ihsg_trend = "bullish"
            daily.market_sentiment = "Risk-On"
        elif avg_change < -0.5:
            daily.ihsg_trend = "bearish"
            daily.market_sentiment = "Risk-Off"
        else:
            daily.ihsg_trend = "sideways"
            daily.market_sentiment = "Neutral"

    # ── Hot stocks (signals) ──
    try:
        swing_batch = await scan_signals("swing", limit=3)
        scalp_batch = await scan_signals("scalp", limit=3)
        daily.hot_stocks = [
            {"symbol": s.symbol, "type": s.signal_type, "confidence": s.confidence, "entry": s.entry_price}
            for s in swing_batch.signals + scalp_batch.signals
        ]
    except Exception as e:
        logger.warning(f"Daily signal scan error: {e}")

    # ── Summary ──
    gainer_str = ", ".join(f"{g['symbol']} (+{g['change_pct']}%)" for g in daily.top_gainers[:5])
    loser_str = ", ".join(f"{l['symbol']} ({l['change_pct']}%)" for l in daily.top_losers[:5])

    daily.summary = (
        f"📊 *Daily Market Map — {daily.date}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📈 *IHSG:* {daily.ihsg_change_pct:+.2f}% ({daily.ihsg_trend})\n"
        f"🎯 *Sentimen:* {daily.market_sentiment}\n\n"
        f"🟢 *Top Gainers:*\n{gainer_str}\n\n"
        f"🔴 *Top Losers:*\n{loser_str}\n"
    )

    if daily.hot_stocks:
        daily.summary += "\n⚡ *Signal Hari Ini:*\n"
        for h in daily.hot_stocks:
            daily.summary += f"  • {h['symbol']} ({h['type'].upper()}) Conf: {h['confidence']}\n"

    return daily


async def generate_weekly_map() -> WeeklyMap:
    """Generate weekly market mapping."""
    from src.engine.screener_cache import fetch_all_cached

    now = datetime.now()
    week_start = (now - timedelta(days=now.weekday())).strftime("%d %b")
    weekly = WeeklyMap(
        week_start=week_start,
        week_end=now.strftime("%d %b %Y"),
    )

    data = await fetch_all_cached()
    if not data:
        weekly.summary = "Data tidak tersedia."
        return weekly

    # ── Weekly performance (5-day change) ──
    performers = []
    for sym, bars in data.items():
        if not isinstance(bars, list) or len(bars) < 6:
            continue
        try:
            week_open = bars[-6]["close"]
            week_close = bars[-1]["close"]
            if week_open > 0:
                change_pct = (week_close - week_open) / week_open * 100
                performers.append({
                    "symbol": sym,
                    "change_pct": round(change_pct, 2),
                    "close": week_close,
                })
        except (KeyError, IndexError, ZeroDivisionError):
            continue

    performers.sort(key=lambda p: p["change_pct"], reverse=True)
    weekly.weekly_winners = performers[:10]
    weekly.weekly_losers = performers[-10:]
    weekly.weekly_losers.reverse()

    if performers:
        weekly.ihsg_weekly_change = round(
            sum(p["change_pct"] for p in performers) / len(performers), 2
        )

    # ── Summary ──
    winners_str = "\n".join(
        f"  🟢 {w['symbol']}: +{w['change_pct']}%" for w in weekly.weekly_winners[:5]
    )
    losers_str = "\n".join(
        f"  🔴 {l['symbol']}: {l['change_pct']}%" for l in weekly.weekly_losers[:5]
    )

    weekly.summary = (
        f"📊 *Weekly Market Map*\n"
        f"📅 {weekly.week_start} — {weekly.week_end}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📈 *IHSG Weekly:* {weekly.ihsg_weekly_change:+.2f}%\n\n"
        f"*Top Weekly Winners:*\n{winners_str}\n\n"
        f"*Top Weekly Losers:*\n{losers_str}\n"
    )

    return weekly
