"""Watchlist Smart — Premium feature.

Auto-track up to 10 favorite stocks. Daily digest with:
  • Price changes
  • Foreign flow per stock
  • Technical signals

Locked to Premium tier. Free users get CTA.
"""

import asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class WatchlistEntry:
    """Single stock in watchlist."""
    symbol: str
    name: str = ""
    added_at: str = ""
    last_price: float = 0
    change_pct: float = 0
    alerts_enabled: bool = True


@dataclass
class WatchlistDigest:
    """Daily watchlist summary."""
    timestamp: str
    entries: List[Dict] = field(default_factory=list)
    market_sentiment: str = "NEUTRAL"
    top_mover: str = ""
    summary: str = ""


class WatchlistEngine:
    """Manage user watchlists and generate daily digests."""

    MAX_STOCKS_FREE = 3
    MAX_STOCKS_PRO = 10
    MAX_STOCKS_PREMIUM = 10
    STORAGE_DIR = os.path.expanduser("~/idx-trading-bot/data/watchlists")

    def __init__(self):
        os.makedirs(self.STORAGE_DIR, exist_ok=True)

    def _path(self, user_id: int) -> str:
        return os.path.join(self.STORAGE_DIR, f"watchlist_{user_id}.json")

    def load(self, user_id: int) -> List[WatchlistEntry]:
        """Load user watchlist from disk."""
        path = self._path(user_id)
        if not os.path.exists(path):
            return []
        try:
            with open(path) as f:
                data = json.load(f)
            return [
                WatchlistEntry(
                    symbol=e.get("symbol", ""),
                    name=e.get("name", ""),
                    added_at=e.get("added_at", ""),
                    last_price=e.get("last_price", 0),
                    change_pct=e.get("change_pct", 0),
                    alerts_enabled=e.get("alerts_enabled", True),
                )
                for e in data
            ]
        except Exception:
            return []

    def save(self, user_id: int, entries: List[WatchlistEntry]):
        """Save user watchlist to disk."""
        path = self._path(user_id)
        data = [
            {
                "symbol": e.symbol,
                "name": e.name,
                "added_at": e.added_at,
                "last_price": e.last_price,
                "change_pct": e.change_pct,
                "alerts_enabled": e.alerts_enabled,
            }
            for e in entries
        ]
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def add(self, user_id: int, symbol: str, tier: str = "free") -> tuple[bool, str]:
        """Add a stock to watchlist. Returns (success, message)."""
        max_count = {
            "free": self.MAX_STOCKS_FREE,
            "pro": self.MAX_STOCKS_PRO,
            "premium": self.MAX_STOCKS_PREMIUM,
        }.get(tier, self.MAX_STOCKS_FREE)

        entries = self.load(user_id)

        # Check if already in watchlist
        if any(e.symbol == symbol.upper() for e in entries):
            return False, f"{symbol} sudah ada di watchlist"

        # Check limit
        if len(entries) >= max_count:
            if tier == "free":
                return False, (
                    f"Free tier max {max_count} saham. "
                    f"Upgrade ke Pro (Rp49rb) untuk 10 saham: /pricing"
                )
            return False, f"Watchlist penuh ({max_count} saham max)"

        entries.append(WatchlistEntry(
            symbol=symbol.upper(),
            added_at=datetime.now().isoformat(),
        ))
        self.save(user_id, entries)
        return True, f"✅ {symbol.upper()} ditambahkan ke watchlist ({len(entries)}/{max_count})"

    def remove(self, user_id: int, symbol: str) -> tuple[bool, str]:
        """Remove a stock from watchlist."""
        entries = self.load(user_id)
        new_entries = [e for e in entries if e.symbol != symbol.upper()]
        if len(new_entries) == len(entries):
            return False, f"{symbol.upper()} tidak ada di watchlist"
        self.save(user_id, new_entries)
        return True, f"✅ {symbol.upper()} dihapus dari watchlist"

    def list_stocks(self, user_id: int) -> List[WatchlistEntry]:
        """List all stocks in watchlist."""
        return self.load(user_id)

    async def generate_digest(self, user_id: int) -> WatchlistDigest:
        """Generate daily digest for a user's watchlist.

        Fetches:
          - Current prices from Yahoo Finance
          - Market sentiment from RapidAPI
          - Best/worst performer in watchlist
        """
        entries = self.load(user_id)
        if not entries:
            return WatchlistDigest(
                timestamp=datetime.now().isoformat(),
                summary="Watchlist kosong. Tambah saham dengan: `watchlist add BBCA`",
            )

        # Fetch quotes
        quotes = {}
        try:
            from src.feed.yahoo import YahooFeed
            yahoo = YahooFeed()
            for e in entries:
                quote = await yahoo.get_quote(e.symbol)
                if quote:
                    quotes[e.symbol] = quote
        except Exception:
            pass

        # Update prices
        updated_entries = []
        for e in entries:
            q = quotes.get(e.symbol, {})
            if q:
                e.last_price = q.get("price", 0)
                e.change_pct = q.get("change_pct", 0)
                e.name = q.get("name", e.symbol)
            updated_entries.append({
                "symbol": e.symbol,
                "name": e.name or e.symbol,
                "price": e.last_price,
                "change_pct": e.change_pct,
                "direction": "🟢" if e.change_pct > 0 else ("🔴" if e.change_pct < 0 else "⚪"),
            })
        self.save(user_id, entries)

        # Market sentiment
        sentiment_label = "NEUTRAL"
        try:
            from src.feed.rapidapi_idx import RapidAPIFeed
            from src.engine.market_sentiment import MarketSentimentEngine
            feed = RapidAPIFeed()
            broker = await feed.get_broker_flow_summary()
            await feed.close()
            sent = MarketSentimentEngine()
            result = sent.analyze(broker)
            sentiment_label = result.sentiment
        except Exception:
            pass

        # Find top/bottom mover
        sorted_by_change = sorted(
            updated_entries, key=lambda e: e["change_pct"], reverse=True
        )
        top_mover = ""
        if updated_entries:
            top = sorted_by_change[0]
            top_mover = f"{top['direction']} {top['symbol']} {top['change_pct']:+.1f}%"

        # Build summary
        gainers = [e for e in updated_entries if e["change_pct"] > 0]
        losers = [e for e in updated_entries if e["change_pct"] < 0]

        summary = (
            f"{sentiment_label} | "
            f"{len(gainers)}🟢 {len(losers)}🔴 | "
            f"{top_mover}"
        )

        return WatchlistDigest(
            timestamp=datetime.now().isoformat(),
            entries=updated_entries,
            market_sentiment=sentiment_label,
            top_mover=top_mover,
            summary=summary,
        )

    def format_digest(self, digest: WatchlistDigest) -> str:
        """Format digest for Telegram output."""
        ts = datetime.fromisoformat(digest.timestamp)
        date_str = ts.strftime("%d %b %Y, %H:%M WIB")

        out = f"📋 *Watchlist Digest — {date_str}*\n"
        out += f"━━━━━━━━━━━━━━━━━━━━\n\n"
        out += f"Pasar: {digest.market_sentiment}\n\n"

        if not digest.entries:
            out += "Watchlist kosong.\n"
            out += "Tambah: `watchlist add BBCA`\n"
        else:
            for e in digest.entries:
                price_str = f"Rp{e['price']:,.0f}" if e['price'] else "—"
                change_str = f"{e['change_pct']:+.1f}%" if e['change_pct'] else "—"
                out += (
                    f"{e['direction']} *{e['symbol']}*  {price_str}  "
                    f"{change_str}\n"
                )

        out += f"\n━━━━━━━━━━━━━━━━━━━━\n"
        out += f"💡 `analisa <saham>` atau `/bandarmology`"

        return out


# ── Tier-gated CTA ──────────────────────────────────────────────

WATCHLIST_CTA_FREE = """
📋 *Watchlist Terbatas*

Free: max 3 saham.
💎 Upgrade ke Pro (Rp49rb/bln) untuk 10 saham + daily digest.

Ketik /pricing
"""


def get_watchlist_response(tier: str, action: str = "show") -> str:
    """Return tier-appropriate watchlist message."""
    if tier == "free" and action != "show":
        return WATCHLIST_CTA_FREE
    return ""
