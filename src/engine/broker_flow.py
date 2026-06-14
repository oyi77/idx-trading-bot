"""Broker & foreign flow tracking engine for IDX stocks.
Data source: Infovesta public API (direct JSON, no browser needed).

API endpoints:
  topbuy:  https://infovesta.com/index2/data_info/saham/topbuy  → Top 5 Net Foreign Buy
  topsell: https://infovesta.com/index2/data_info/saham/topsell → Top 5 Net Foreign Sell

Foreign flow data is limited to top 5 each category (10 stocks total/day).
Historical tracking enables accumulation/distribution detection over time.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import json
import os
import cloudscraper


@dataclass
class BrokerFlow:
    """Net buy/sell from a specific broker."""
    broker_name: str
    symbol: str
    net_buy: float
    volume: int
    date: str


@dataclass
class ForeignFlow:
    """Foreign investor flow data for one stock."""
    symbol: str
    name: str = ""
    foreign_buy: float = 0
    foreign_sell: float = 0
    net_buy: float = 0
    volume: int = 0
    total_volume: int = 0
    date: str = ""
    streak_days: int = 0

    def is_net_buy(self) -> bool:
        return self.net_buy > 0

    def summary(self) -> str:
        direction = "🟢 NET BUY" if self.is_net_buy() else "🔴 NET SELL"
        net_str = f"Rp{abs(self.net_buy):,.0f}"
        return f"{direction} Asing: {net_str} (B: Rp{self.foreign_buy:,.0f} | J: Rp{self.foreign_sell:,.0f})"

    def detail(self) -> str:
        strength = "Weak"
        if abs(self.net_buy) >= 500_000_000_000:
            strength = "Very Strong"
        elif abs(self.net_buy) >= 200_000_000_000:
            strength = "Strong"
        elif abs(self.net_buy) >= 50_000_000_000:
            strength = "Moderate"

        lines = [
            f"🏦 *Foreign Flow {self.symbol}*",
            f"  Aksi: {'🟢 Akumulasi (Net Buy)' if self.is_net_buy() else '🔴 Distribusi (Net Sell)'}",
            f"  Net: Rp{abs(self.net_buy):,.0f} ({strength})",
            f"  Buy: Rp{self.foreign_buy:,.0f}",
            f"  Sell: Rp{self.foreign_sell:,.0f}",
            f"  Streak: {self.streak_days} hari",
        ]
        return "\n".join(lines)


class BrokerFlowEngine:
    """Analyze broker and foreign investor flows for IDX stocks.
    
    Uses Infovesta public API for daily top 5 foreign buy/sell data.
    Caches results locally for offline access and historical tracking.
    """

    API_BASE = "https://infovesta.com/index2/data_info/saham"
    CACHE_PATH = os.path.expanduser("~/idx-trading-bot/data/foreign_flow_cache.json")

    def __init__(self):
        self._scraper = cloudscraper.create_scraper()
        self._cache: Dict = {}
        self._load_cache()

    # ─── Cache ───────────────────────────────────────────────────

    def _load_cache(self):
        try:
            if os.path.exists(self.CACHE_PATH):
                with open(self.CACHE_PATH) as f:
                    self._cache = json.load(f)
        except Exception:
            self._cache = {}

    def _save_cache(self):
        os.makedirs(os.path.dirname(self.CACHE_PATH), exist_ok=True)
        with open(self.CACHE_PATH, "w") as f:
            json.dump(self._cache, f, indent=2, ensure_ascii=False)

    def _is_cache_fresh(self) -> bool:
        if not self._cache or "last_updated" not in self._cache:
            return False
        cache_date = self._cache.get("last_updated", "")
        today = datetime.now().strftime("%Y-%m-%d")
        return cache_date == today

    # ─── API Fetch ───────────────────────────────────────────────

    async def _fetch_topbuy(self) -> List[Dict]:
        """Fetch top 5 foreign buy stocks from Infovesta."""
        import asyncio
        import cloudscraper
        def _sync():
            s = cloudscraper.create_scraper()
            r = s.get(f"{self.API_BASE}/topbuy", timeout=30)
            r.raise_for_status()
            return r.json()
        return await asyncio.to_thread(_sync)

    async def _fetch_topsell(self) -> List[Dict]:
        """Fetch top 5 foreign sell stocks from Infovesta."""
        import asyncio
        import cloudscraper
        def _sync():
            s = cloudscraper.create_scraper()
            r = s.get(f"{self.API_BASE}/topsell", timeout=30)
            r.raise_for_status()
            return r.json()
        return await asyncio.to_thread(_sync)

    async def refresh_cache(self) -> bool:
        """Fetch latest foreign flow data and update cache."""
        try:
            buy_data = await self._fetch_topbuy()
            sell_data = await self._fetch_topsell()
        except Exception as e:
            print(f"[BrokerFlow] API fetch failed: {e}")
            return False

        today = datetime.now().strftime("%Y-%m-%d")
        if not self._cache:
            self._cache = {}

        self._cache["last_updated"] = today
        self._cache["stocks"] = {}
        self._cache["top_foreign_buy"] = []
        self._cache["top_foreign_sell"] = []

        # Process buy data
        for item in buy_data:
            symbol = item.get("id", "").upper()
            entry = {
                "symbol": symbol,
                "foreign_buy": float(item.get("buy", 0) or 0),
                "foreign_sell": float(item.get("sell", 0) or 0),
                "net_buy": float(item.get("nett", 0) or 0),
                "volume": float(item.get("buy", 0) or 0) + float(item.get("sell", 0) or 0),
                "name": "",
            }
            self._cache["top_foreign_buy"].append(entry)
            self._cache["stocks"][symbol] = entry

        # Process sell data
        for item in sell_data:
            symbol = item.get("id", "").upper()
            entry = {
                "symbol": symbol,
                "foreign_buy": float(item.get("buy", 0) or 0),
                "foreign_sell": float(item.get("sell", 0) or 0),
                "net_buy": float(item.get("nett", 0) or 0),  # already negative
                "volume": float(item.get("buy", 0) or 0) + float(item.get("sell", 0) or 0),
                "name": "",
            }
            self._cache["top_foreign_sell"].append(entry)
            # Don't overwrite buy entry if already exists
            if symbol not in self._cache["stocks"]:
                self._cache["stocks"][symbol] = entry

        # Update history for streak tracking
        self._update_history(self._cache["top_foreign_buy"] + self._cache["top_foreign_sell"])
        self._save_cache()
        return True

    # ─── Public API ──────────────────────────────────────────────

    async def get_foreign_flow(self, symbol: str, days: int = 5) -> Optional[ForeignFlow]:
        """Get foreign investor net flow for a specific stock."""
        symbol = symbol.upper()

        # Refresh if cache is stale
        if not self._is_cache_fresh():
            await self.refresh_cache()

        # Check cache
        data = self._cache.get("stocks", {}).get(symbol)
        if not data:
            return None

        return ForeignFlow(
            symbol=symbol,
            name=data.get("name", ""),
            foreign_buy=data.get("foreign_buy", 0),
            foreign_sell=data.get("foreign_sell", 0),
            net_buy=data.get("net_buy", 0),
            volume=data.get("volume", 0),
            date=self._cache.get("last_updated", ""),
            streak_days=self._calculate_streak(symbol),
        )

    async def get_top_foreign_buy(self, top_n: int = 5) -> List[ForeignFlow]:
        if not self._is_cache_fresh():
            await self.refresh_cache()
        stocks = self._cache.get("top_foreign_buy", [])[:top_n]
        return [
            ForeignFlow(
                symbol=s["symbol"], name=s.get("name", ""),
                foreign_buy=s.get("foreign_buy", 0),
                foreign_sell=s.get("foreign_sell", 0),
                net_buy=s.get("net_buy", 0),
                volume=s.get("volume", 0),
                date=self._cache.get("last_updated", ""),
                streak_days=self._calculate_streak(s["symbol"]),
            ) for s in stocks
        ]

    async def get_top_foreign_sell(self, top_n: int = 5) -> List[ForeignFlow]:
        if not self._is_cache_fresh():
            await self.refresh_cache()
        stocks = self._cache.get("top_foreign_sell", [])[:top_n]
        return [
            ForeignFlow(
                symbol=s["symbol"], name=s.get("name", ""),
                foreign_buy=s.get("foreign_buy", 0),
                foreign_sell=s.get("foreign_sell", 0),
                net_buy=s.get("net_buy", 0),
                volume=s.get("volume", 0),
                date=self._cache.get("last_updated", ""),
                streak_days=self._calculate_streak(s["symbol"]),
            ) for s in stocks
        ]

    async def detect_accumulation(
        self, symbol: str, min_streak: int = 3, min_value: float = 1_000_000_000
    ) -> Optional[Dict]:
        flow = await self.get_foreign_flow(symbol, min_streak)
        if flow and flow.streak_days >= min_streak and abs(flow.net_buy) >= min_value:
            direction = "accumulation" if flow.net_buy > 0 else "distribution"
            return {
                "symbol": symbol,
                "direction": direction,
                "streak_days": flow.streak_days,
                "net_value": flow.net_buy,
                "signal": f"Foreign {direction} {flow.streak_days} days in a row",
                "date": flow.date,
            }
        return None

    async def get_top_brokers(self, symbol: str, top_n: int = 5) -> List[BrokerFlow]:
        """Get top N brokers by net buy/sell for a symbol.
        Note: Per-broker data not available from Infovesta.
        Returns foreign flow as approximation.
        """
        flow = await self.get_foreign_flow(symbol)
        if flow and flow.net_buy != 0:
            return [
                BrokerFlow(
                    broker_name="ALL FOREIGN",
                    symbol=symbol,
                    net_buy=flow.net_buy,
                    volume=flow.volume,
                    date=flow.date,
                )
            ]
        return []

    def get_foreign_market_summary(self) -> str:
        """One-line summary of today's foreign activity."""
        buys = self._cache.get("top_foreign_buy", [])
        sells = self._cache.get("top_foreign_sell", [])
        total_buy = sum(s.get("net_buy", 0) for s in buys)
        total_sell = sum(abs(s.get("net_buy", 0)) for s in sells)
        net_total = total_buy - total_sell

        direction = "🟢 Net Buy" if net_total > 0 else "🔴 Net Sell"
        return (
            f"🏦 *Foreign Flow Market*\n"
            f"  {direction}: Rp{abs(net_total):,.0f}\n"
            f"  Top Buy: {', '.join(s['symbol'] for s in buys[:3])}\n"
            f"  Top Sell: {', '.join(s['symbol'] for s in sells[:3])}"
        )

    # ─── Internal ────────────────────────────────────────────────

    def _calculate_streak(self, symbol: str) -> int:
        """Calculate consecutive days of foreign net buy/sell."""
        history = self._cache.get("history", {}).get(symbol, [])
        if len(history) < 2:
            return 0
        sorted_hist = sorted(history, key=lambda x: x.get("date", ""), reverse=True)
        streak = 0
        prev_dir = None
        for entry in sorted_hist:
            net = entry.get("net_buy", 0)
            direction = "buy" if net > 0 else "sell" if net < 0 else "neutral"
            if prev_dir is None:
                prev_dir = direction
                streak = 1
            elif direction == prev_dir and direction != "neutral":
                streak += 1
            else:
                break
        return streak

    def _update_history(self, stocks: List[Dict]):
        today = datetime.now().strftime("%Y-%m-%d")
        if "history" not in self._cache:
            self._cache["history"] = {}
        for stock in stocks:
            sym = stock["symbol"]
            if sym not in self._cache["history"]:
                self._cache["history"][sym] = []
            self._cache["history"][sym].append({
                "date": today,
                "net_buy": stock.get("net_buy", 0),
                "foreign_buy": stock.get("foreign_buy", 0),
                "foreign_sell": stock.get("foreign_sell", 0),
            })
            self._cache["history"][sym] = self._cache["history"][sym][-30:]
