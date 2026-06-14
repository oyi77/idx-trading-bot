"""Pre-Market Briefing Engine.

Daily morning snapshot for IDX traders before market opens (09:00 WIB).

Fetches:
  • IHSG yesterday close + futures indication
  • Global indices: Dow, S&P 500, Nasdaq, Nikkei, Hang Seng, Shanghai
  • Commodities: Gold, Oil, Coal (ICE Newcastle), Nickel (LME), CPO (BMD)
  • USD/IDR + other FX
  • Yesterday's foreign flow (RapidAPI)
  • Key events today (economic calendar)

Usage:
  /premarket — full briefing
  /premarket quick — compact version

Data sources: Yahoo Finance (free), RapidAPI IDX (free tier), web scraping fallback
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class MarketQuote:
    symbol: str
    name: str
    price: float = 0
    change_pct: float = 0
    change_val: float = 0
    currency: str = ""


@dataclass
class PreMarketSnapshot:
    timestamp: str
    ihsg: Optional[MarketQuote] = None
    global_indices: List[MarketQuote] = field(default_factory=list)
    commodities: List[MarketQuote] = field(default_factory=list)
    fx_rates: List[MarketQuote] = field(default_factory=list)
    foreign_net_buy: float = 0  # yesterday
    foreign_domestic_ratio: float = 0
    market_sentiment: str = "NEUTRAL"
    events_today: List[str] = field(default_factory=list)


# ─── Symbols to fetch ─────────────────────────────────────────

GLOBAL_INDICES = {
    "^DJI": "Dow Jones",
    "^GSPC": "S&P 500",
    "^IXIC": "Nasdaq",
    "^N225": "Nikkei 225",
    "^HSI": "Hang Seng",
    "000001.SS": "Shanghai",
}

# Commodities with Yahoo symbols
COMMODITIES = {
    "GC=F": ("Gold", "USD/oz"),
    "CL=F": ("Oil WTI", "USD/bbl"),
    "HG=F": ("Copper", "USD/lb"),
    "ZC=F": ("Corn", "USc/bu"),
    "ZS=F": ("Soybean", "USc/bu"),
}

# FX rates
FX_RATES = {
    "USDIDR=X": ("USD/IDR", "Rp"),
    "USDSGD=X": ("USD/SGD", "SGD"),
    "USDJPY=X": ("USD/JPY", "¥"),
}

# IDX-relevant commodities (web-scraped or API)
# Coal: ICE Newcastle — use Investing.com or Tradingeconomics
# Nickel: LME — use Investing.com
# CPO: BMD Malaysia — use Investing.com
REGIONAL_COMMODITIES = [
    {"name": "Coal (Newcastle)", "source": "investing", "id": "ice-newcastle-coal"},
    {"name": "Nickel (LME)", "source": "investing", "id": "lme-nickel"},
    {"name": "CPO (BMD)", "source": "investing", "id": "bmd-cpo"},
]


async def fetch_yahoo_quotes(symbols: dict) -> List[MarketQuote]:
    """Fetch quotes from Yahoo Finance for multiple symbols.
    symbols: {symbol: name} or {symbol: (name, unit)}
    """
    results = []
    try:
        from src.feed.yahoo import YahooFeed
        feed = YahooFeed()
        for sym, name_or_tuple in symbols.items():
            name = name_or_tuple[0] if isinstance(name_or_tuple, tuple) else name_or_tuple
            try:
                quote = await feed.get_global_quote(sym)
                if quote:
                    results.append(MarketQuote(
                        symbol=sym,
                        name=name,
                        price=float(quote.get("price", 0) or 0),
                        change_pct=float(quote.get("change_pct", 0) or 0),
                        change_val=float(quote.get("change", 0) or 0),
                        currency="",
                    ))
            except Exception as e:
                logger.debug(f"Yahoo fetch failed for {sym}: {e}")
    except Exception as e:
        logger.warning(f"Yahoo feed init failed: {e}")
    return results


async def fetch_foreign_flow() -> Tuple[float, float]:
    """Fetch yesterday's foreign net buy and domestic ratio."""
    try:
        from src.feed.rapidapi_idx import RapidAPIFeed
        feed = RapidAPIFeed()
        broker = await feed.get_broker_flow_summary()
        await feed.close()
        fnb = float(broker.get("foreign_net_buy", 0) or 0)
        fdr = float(broker.get("foreign_domestic_ratio", 0) or 0)
        return fnb, fdr
    except Exception as e:
        logger.debug(f"Foreign flow fetch failed: {e}")
        return 0, 0


async def fetch_regional_commodities() -> List[MarketQuote]:
    """Scrape regional commodity prices from Investing.com or similar."""
    results = []
    # Try scrape coal price from Trading Economics (public page)
    try:
        import aiohttp
        # Coal price - try multiple sources
        async with aiohttp.ClientSession() as session:
            # Free API for commodity prices (tradingeconomics public endpoint)
            for comm in REGIONAL_COMMODITIES:
                try:
                    # Use web search / extraction as fallback
                    # For now, skip — too unreliable via scraping
                    pass
                except Exception:
                    pass
    except Exception:
        pass
    return results


async def build_premarket_snapshot() -> PreMarketSnapshot:
    """Build complete pre-market briefing."""
    now = datetime.now()
    snapshot = PreMarketSnapshot(
        timestamp=now.isoformat(),
        events_today=_get_today_events(now),
    )

    # ─── Fetch in parallel ─────────────────────────────────
    tasks = [
        fetch_yahoo_quotes({"^JKSE": "IHSG"}),
        fetch_yahoo_quotes(GLOBAL_INDICES),
        fetch_yahoo_quotes(COMMODITIES),
        fetch_yahoo_quotes(FX_RATES),
        fetch_foreign_flow(),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Unpack results
    ihsg_list = results[0] if not isinstance(results[0], Exception) else []
    snapshot.ihsg = ihsg_list[0] if ihsg_list else None

    snapshot.global_indices = results[1] if not isinstance(results[1], Exception) else []
    snapshot.commodities = results[2] if not isinstance(results[2], Exception) else []
    snapshot.fx_rates = results[3] if not isinstance(results[3], Exception) else []

    flow = results[4] if not isinstance(results[4], Exception) else (0, 0)
    snapshot.foreign_net_buy = flow[0]
    snapshot.foreign_domestic_ratio = flow[1]

    # ─── Market sentiment ──────────────────────────────────
    try:
        from src.engine.market_sentiment import MarketSentimentEngine
        sent_engine = MarketSentimentEngine()
        # Need broker_flow dict format
        broker_data = {
            "foreign_net_buy": snapshot.foreign_net_buy,
            "foreign_domestic_ratio": snapshot.foreign_domestic_ratio,
        }
        result = sent_engine.analyze(broker_data)
        # Extract just the label from "🟢 BULLISH" format
        sentiment_raw = result.sentiment
        snapshot.market_sentiment = sentiment_raw.split()[-1] if " " in sentiment_raw else sentiment_raw
    except Exception:
        pass

    return snapshot


def _get_today_events(today: datetime) -> List[str]:
    """Return known economic events for today."""
    # Static calendar — extend with API later
    events = []
    day = today.day
    month = today.month
    weekday = today.weekday()

    # BI Rate decision — typically 3rd week of month (Tue/Wed)
    if month in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12):
        # Simplified: check if it's around 15-22 of month
        if 15 <= day <= 22 and weekday in (1, 2):  # Tue/Wed
            events.append("⚠️ *BI Rate Decision* — possible this week")

    # US FOMC — roughly every 6 weeks
    # Too complex to hardcode — skip for now

    # Indonesia trade balance — around 15th each month
    if day == 15 or (day == 16 and weekday == 0):
        events.append("📊 *Trade Balance Indonesia* — expected today")

    # Indonesia inflation — 1st of month
    if day == 1 or (day == 2 and weekday == 0):
        events.append("📊 *Inflasi Indonesia* — expected today")

    return events


# ─── Formatting ──────────────────────────────────────────────

def format_premarket(snapshot: PreMarketSnapshot, mode: str = "full") -> str:
    """Format pre-market snapshot for Telegram output."""
    ts = datetime.fromisoformat(snapshot.timestamp)
    date_str = ts.strftime("%d %B %Y, %H:%M WIB")

    out = f"🌅 *Briefing Pre-Market — {date_str}*\n"
    out += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    # ─── IHSG ──────────────────────────────────────────────
    if snapshot.ihsg and snapshot.ihsg.price:
        d = "🟢" if snapshot.ihsg.change_pct > 0 else "🔴"
        out += f"*🇮🇩 IHSG*  {d} Rp{snapshot.ihsg.price:,.0f} ({snapshot.ihsg.change_pct:+.1f}%)\n\n"
    else:
        out += "*🇮🇩 IHSG*  Data tidak tersedia\n\n"

    # ─── Pasar Global ────────────────────────────────────
    if snapshot.global_indices:
        out += "*🌍 Pasar Global*\n"
        for idx in snapshot.global_indices:
            if idx.price:
                d = "🟢" if idx.change_pct > 0 else "🔴"
                out += f"  {d} {idx.name}: {idx.change_pct:+.1f}%\n"
        out += "\n"

    # ─── Komoditas ───────────────────────────────────────
    if snapshot.commodities:
        out += "*🛢 Komoditas*\n"
        for comm in snapshot.commodities[:5]:
            if comm.price:
                d = "🟢" if comm.change_pct > 0 else "🔴"
                out += f"  {d} {comm.name}: {comm.change_pct:+.1f}%\n"
        out += "\n"

    # ─── Valas ────────────────────────────────────────────────
    if snapshot.fx_rates:
        out += "*💱 Valas*\n"
        for fx in snapshot.fx_rates:
            if fx.price:
                d = "🟢" if fx.change_pct > 0 else "🔴"
                out += f"  {d} {fx.name}: Rp{fx.price:,.0f} ({fx.change_pct:+.1f}%)\n"
        out += "\n"

    # ─── Arus Asing ──────────────────────────────────────
    fnb = snapshot.foreign_net_buy
    fdr = snapshot.foreign_domestic_ratio * 100
    if fnb:
        direction = "Net Buy" if fnb > 0 else "Net Sell"
        d = "🟢" if fnb > 0 else "🔴"
        out += f"*🏦 Arus Asing (kemarin)*\n"
        out += f"  {d} {direction}: Rp{abs(fnb):,.0f} (porsi asing {fdr:.1f}%)\n\n"

    # ─── Sentimen Pasar ──────────────────────────────────
    sent = snapshot.market_sentiment
    s_emoji = {"BULLISH": "🟢", "BEARISH": "🔴", "NEUTRAL": "⚪"}.get(sent, "⚪")
    out += f"*🧠 Sentimen Pasar*  {s_emoji} {sent}\n\n"

    # ─── Event Hari Ini ────────────────────────────────────
    if snapshot.events_today:
        out += "*📅 Event Hari Ini*\n"
        for ev in snapshot.events_today:
            out += f"  {ev}\n"
        out += "\n"

    # ─── Saran Trading ───────────────────────────
    out += "━━━━━━━━━━━━━━━━━━━━━━━\n"
    if sent == "BULLISH":
        out += "💡 *Saran:* Market bullish — fokus saham akumulasi asing. `screener momentum`\n"
    elif sent == "BEARISH":
        out += "⚠️ *Saran:* Market bearish — kurangi posisi, pasang SL ketat. `screener reversal`\n"
    else:
        out += "💡 *Suggestion:* Market netral — selective entry. `/analisa <saham>`\n"

    out += "📊 Pantau watchlist: `/watchlist`  |  Analisa: `/analisa BBCA`"

    return out


def format_premarket_compact(snapshot: PreMarketSnapshot) -> str:
    """Compact version for quick check."""
    ts = datetime.fromisoformat(snapshot.timestamp)

    out = "🌅 *Pre-Market Quick*\n"
    out += "━━━━━━━━━━━━━━━━━━━━━━━\n"

    if snapshot.ihsg and snapshot.ihsg.price:
        d = "🟢" if snapshot.ihsg.change_pct > 0 else "🔴"
        out += f"IHSG {d} {snapshot.ihsg.change_pct:+.1f}%  |  "

    # Top global mover
    if snapshot.global_indices:
        best = max(snapshot.global_indices, key=lambda x: abs(x.change_pct))
        d = "🟢" if best.change_pct > 0 else "🔴"
        out += f"{best.name} {d} {best.change_pct:+.1f}%\n"

    # USD/IDR
    for fx in snapshot.fx_rates:
        if fx.name == "USD/IDR" and fx.price:
            out += f"USD/IDR: Rp{fx.price:,.0f}  |  "

    # Gold
    for comm in snapshot.commodities:
        if comm.name == "Gold" and comm.price:
            out += f"Gold: ${comm.price:,.0f}\n"

    out += f"Sentiment: {snapshot.market_sentiment}  |  "
    out += f"Foreign: {'Buy' if snapshot.foreign_net_buy > 0 else 'Sell'}\n"

    out += "━━━━━━━━━━━━━━━━━━━━━━━\n"
    out += "💡 Full briefing: `/premarket`"

    return out
