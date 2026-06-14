"""Portfolio Tracker — Real-time position tracking & P&L.

Stockpick Signal-inspired: hari ke-N, BOW/BOS tag, performance distribution,
controlled loss, status zones, risk management.

Commands:
  /portfolio                         — view all positions + stats
  /portfolio add BBCA 4500 100      — add position
  /portfolio close BBCA 4800        — close position
  /portfolio history                — closed positions log
  /jejak                             — profit trail + performance distribution
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

PORTFOLIO_DIR = os.path.expanduser("~/idx-trading-bot/data/portfolios")


@dataclass
class Position:
    symbol: str
    entry_price: float
    quantity: int  # lots (100 shares per lot)
    entry_date: str
    name: str = ""
    status: str = "open"  # open | closed
    exit_price: float = 0
    exit_date: str = ""
    pnl: float = 0
    pnl_pct: float = 0
    current_price: float = 0
    current_value: float = 0
    unrealized_pnl: float = 0
    unrealized_pnl_pct: float = 0
    tag: str = ""  # BOW / BOS / NONE
    holding_days: int = 0


@dataclass
class PortfolioStats:
    total_positions: int
    total_value: float
    total_pnl: float
    total_pnl_pct: float
    win_rate: float
    controlled_loss: int  # positions >3% loss
    controlled_loss_pct: float
    perf_distribution: Dict[str, int]  # e.g., {">10%": 3, "5-10%": 5, ...}
    status_zones: Dict[str, int]  # e.g., {"Neutral": 10, "Risk Zone": 4}


class PortfolioEngine:
    """Manage user portfolio positions with advanced analytics."""

    def __init__(self):
        os.makedirs(PORTFOLIO_DIR, exist_ok=True)

    def _path(self, user_id: int) -> str:
        return os.path.join(PORTFOLIO_DIR, f"portfolio_{user_id}.json")

    def load(self, user_id: int) -> List[Position]:
        path = self._path(user_id)
        if not os.path.exists(path):
            return []
        try:
            with open(path) as f:
                data = json.load(f)
            return [
                Position(
                    symbol=d.get("symbol", ""),
                    entry_price=d.get("entry_price", 0),
                    quantity=d.get("quantity", 0),
                    entry_date=d.get("entry_date", ""),
                    name=d.get("name", ""),
                    status=d.get("status", "open"),
                    exit_price=d.get("exit_price", 0),
                    exit_date=d.get("exit_date", ""),
                    pnl=d.get("pnl", 0),
                    pnl_pct=d.get("pnl_pct", 0),
                    holding_days=d.get("holding_days", 0),
                    tag=d.get("tag", ""),
                )
                for d in data
            ]
        except Exception:
            return []

    def save(self, user_id: int, positions: List[Position]):
        data = [
            {
                "symbol": p.symbol,
                "entry_price": p.entry_price,
                "quantity": p.quantity,
                "entry_date": p.entry_date,
                "name": p.name,
                "status": p.status,
                "exit_price": p.exit_price,
                "exit_date": p.exit_date,
                "pnl": p.pnl,
                "pnl_pct": p.pnl_pct,
                "holding_days": p.holding_days,
                "tag": p.tag,
            }
            for p in positions
        ]
        with open(self._path(user_id), "w") as f:
            json.dump(data, f, indent=2)

    def add(self, user_id: int, symbol: str, entry_price: float, quantity: int) -> Tuple[bool, str]:
        """Add a new position with auto BOW/BOS tag detection."""
        positions = self.load(user_id)
        symbol_upper = symbol.upper()

        if any(p.symbol == symbol_upper and p.status == "open" for p in positions):
            return False, f"Sudah punya posisi {symbol_upper} yang open."

        # Auto-detect tag
        tag = self._detect_tag(symbol_upper, entry_price)

        positions.append(Position(
            symbol=symbol_upper,
            entry_price=entry_price,
            quantity=quantity,
            entry_date=datetime.now().isoformat(),
            tag=tag,
        ))
        self.save(user_id, positions)
        return True, f"✅ {symbol_upper} {quantity} lot @ Rp{entry_price:,.0f} ditambahkan {f'[{tag}]' if tag else ''}"

    def _detect_tag(self, symbol: str, entry_price: float) -> str:
        """Detect BOW/BOS tag from SMC structure."""
        try:
            import yfinance as yf
            from src.engine.smc_structure import SMCStructureEngine

            ticker = yf.Ticker(f"{symbol}.JK")
            df = ticker.history(period="3mo")
            if df.empty:
                return ""

            ohlc = []
            for idx, row in df.iterrows():
                ohlc.append({
                    "timestamp": str(idx), "open": float(row["Open"]),
                    "high": float(row["High"]), "low": float(row["Low"]),
                    "close": float(row["Close"]), "volume": float(row["Volume"]),
                })

            smc = SMCStructureEngine().analyze(ohlc, symbol)

            if smc.trend == "BULLISH":
                return "BOS" if smc.recent_bos else "BOW"
            elif smc.trend == "BEARISH":
                return "CHoCH" if smc.recent_choch else ""

        except Exception:
            pass

        return ""

    def close(self, user_id: int, symbol: str, exit_price: float) -> Tuple[bool, str]:
        """Close a position at exit price."""
        positions = self.load(user_id)
        symbol_upper = symbol.upper()

        for p in positions:
            if p.symbol == symbol_upper and p.status == "open":
                p.status = "closed"
                p.exit_price = exit_price
                p.exit_date = datetime.now().isoformat()
                p.holding_days = self._calc_holding_days(p.entry_date)
                p.pnl = (exit_price - p.entry_price) * p.quantity * 100
                p.pnl_pct = ((exit_price / p.entry_price) - 1) * 100 if p.entry_price else 0
                self.save(user_id, positions)
                pnl_sign = "+" if p.pnl >= 0 else ""
                return True, (
                    f"🔒 Closed {symbol_upper}: {p.quantity} lot ({p.holding_days} hari)\n"
                    f"Entry: Rp{p.entry_price:,.0f} → Exit: Rp{exit_price:,.0f}\n"
                    f"P&L: {pnl_sign}Rp{p.pnl:,.0f} ({p.pnl_pct:+.1f}%)"
                )

        return False, f"Tidak ada posisi open untuk {symbol_upper}"

    def _calc_holding_days(self, entry_date: str) -> int:
        """Calculate days holding a position."""
        try:
            entry_dt = datetime.fromisoformat(entry_date)
            now = datetime.now(timezone.utc)
            entry_dt = entry_dt.replace(tzinfo=timezone.utc)
            return (now - entry_dt).days
        except Exception:
            return 0

    async def refresh_prices(self, positions: List[Position]) -> List[Position]:
        """Refresh current prices and holding days for all open positions."""
        from src.feed.yahoo import YahooFeed
        feed = YahooFeed()

        for p in positions:
            if p.status != "open":
                continue
            p.holding_days = self._calc_holding_days(p.entry_date)
            try:
                quote = await feed.get_quote(p.symbol)
                if quote and quote.get("price"):
                    p.current_price = float(quote.get("price") or 0)
                    p.name = quote.get("name", p.symbol)
                    lot_value = p.current_price * 100
                    p.current_value = lot_value * p.quantity
                    entry_value = p.entry_price * 100 * p.quantity
                    p.unrealized_pnl = p.current_value - entry_value
                    p.unrealized_pnl_pct = ((p.current_price / p.entry_price) - 1) * 100 if p.entry_price else 0
            except Exception:
                pass

        return positions

    def get_stats(self, positions: List[Position]) -> PortfolioStats:
        """Calculate comprehensive portfolio statistics."""
        open_positions = [p for p in positions if p.status == "open"]
        closed_positions = [p for p in positions if p.status == "closed"]

        total_value = sum(p.current_value for p in open_positions)
        total_entry = sum(p.entry_price * 100 * p.quantity for p in open_positions)
        total_pnl = total_value - total_entry
        total_pnl_pct = ((total_value / total_entry) - 1) * 100 if total_entry else 0

        wins = sum(1 for p in closed_positions if p.pnl > 0)
        wr = wins / len(closed_positions) * 100 if closed_positions else 0

        # Controlled loss: open positions with >3% loss
        loss_positions = [
            p for p in open_positions
            if p.unrealized_pnl_pct < -3
        ]
        controlled_loss = len(loss_positions)

        # Performance distribution (all positions: open + closed)
        perf_dist = {
            ">10%": 0, "5–10%": 0, "0–5%": 0, "-0–3%": 0, "<-3%": 0,
        }
        all_positions = list(open_positions) + list(closed_positions)
        for p in all_positions:
            pnl = p.unrealized_pnl_pct if p.status == "open" else p.pnl_pct
            if pnl > 10:
                perf_dist[">10%"] += 1
            elif pnl > 5:
                perf_dist["5–10%"] += 1
            elif pnl >= 0:
                perf_dist["0–5%"] += 1
            elif pnl > -3:
                perf_dist["-0–3%"] += 1
            else:
                perf_dist["<-3%"] += 1

        # Status zones
        status_zones = {"Neutral": 0, "Risk Zone": 0}
        for p in open_positions:
            if p.unrealized_pnl_pct < -5:
                status_zones["Risk Zone"] += 1
            else:
                status_zones["Neutral"] += 1

        return PortfolioStats(
            total_positions=len(open_positions),
            total_value=total_value,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            win_rate=wr,
            controlled_loss=controlled_loss,
            controlled_loss_pct=(controlled_loss / len(open_positions) * 100) if open_positions else 0,
            perf_distribution=perf_dist,
            status_zones=status_zones,
        )

    def format_portfolio(self, positions: List[Position]) -> str:
        """Stockpick-style portfolio display."""
        open_positions = [p for p in positions if p.status == "open"]
        stats = self.get_stats(positions)

        pnl_emoji = "🟢" if stats.total_pnl >= 0 else "🔴"

        out = "⚡ *Active Positions* — "
        out += f"{stats.total_positions} positions\n"
        out += "━━━━━━━━━━━━━━━━━━━━\n"

        if not open_positions:
            out += "📭 Belum ada posisi aktif.\n\n"
            out += "Tambah: `/portfolio add BBCA 4500 100`\n"
            return out

        # Summary line
        out += f"💰 *{pnl_emoji} P&L: Rp{stats.total_pnl:,.0f} ({stats.total_pnl_pct:+.1f}%)*  |  "
        out += f"📍 {stats.status_zones.get('Risk Zone', 0)} in Risk Zone\n\n"

        # Controlled Loss section (Stockpick style)
        if stats.controlled_loss > 0:
            out += f"⚠️ *CONTROLLED LOSS* — {stats.controlled_loss} posisi >3% loss\n\n"
        else:
            out += "✅ *CONTROLLED LOSS* — 0 posisi >3% loss\n\n"

        # Tab-style display
        out += "*📌 Positions:*\n"
        for p in open_positions:
            if not p.current_price:
                out += f"  ⚪ *{p.symbol}* {p.quantity} lot @ Rp{p.entry_price:,.0f}\\n"
                out += f"     _Menunggu data harga..._\\n\\n"
                continue

            pnl_icon = "🟢" if p.unrealized_pnl >= 0 else "🔴"
            pnl_sign = "+" if p.unrealized_pnl >= 0 else ""

            # Status
            if p.unrealized_pnl_pct < -5:
                status = "🔴 Risk Zone"
            elif p.unrealized_pnl_pct < -1:
                status = "⚠️ Watch"
            else:
                status = "🟢 Neutral"

            # BOW/BOS tag
            tag_display = f"  `{p.tag}` " if p.tag else ""

            out += (
                f"  ⚡ *{p.symbol}*{tag_display}| Hari ke-{p.holding_days} | {status}\n"
                f"     Entry Rp{p.entry_price:,.0f} | "
                f"Now Rp{p.current_price:,.0f}\n"
                f"     {pnl_icon} P&L: {pnl_sign}Rp{p.unrealized_pnl:,.0f} "
                f"({pnl_sign}{p.unrealized_pnl_pct:.1f}%)\n\n"
            )

        # Performance Distribution
        out += "━━━━━━━━━━━━━━━━━━━━\n"
        out += "📊 *Performance Distribution*\n"

        perf = stats.perf_distribution
        dist_lines = [
            ("🟢", ">10%", perf[">10%"]),
            ("🟢", "5–10%", perf["5–10%"]),
            ("⚪", "0–5%", perf["0–5%"]),
            ("🔴", "-0–3%", perf["-0–3%"]),
            ("🔴", "<-3%", perf["<-3%"]),
        ]
        for icon, label, count in dist_lines:
            bar = "█" * count if count > 0 else "—"
            out += f"  {icon} *{label}* {bar} — {count} trades\n"

        # All-time stats
        closed_positions = [p for p in positions if p.status == "closed"]
        if closed_positions:
            total_closed_pnl = sum(p.pnl for p in closed_positions)
            out += (
                f"\n📈 *All-Time:* {len(closed_positions)} trades  |  "
                f"Win: {stats.win_rate:.0f}%  |  P&L: Rp{total_closed_pnl:,.0f}\n"
            )

        out += (
            f"\n💡 `/portfolio add SYMBOL PRICE LOT` — tambah posisi\n"
            f"💡 `/portfolio close SYMBOL PRICE` — tutup posisi\n"
            f"💡 `/jejak` — profit trail lengkap"
        )

        return out

    def format_jejak(self, positions: List[Position]) -> str:
        """Profit trail display — Stockpick 'Jejak Cuan' style."""
        open_positions = [p for p in positions if p.status == "open"]
        closed_positions = [p for p in positions if p.status == "closed"]
        stats = self.get_stats(positions)

        out = "🏆 *Jejak Cuan* — Profit Trail\n"
        out += "━━━━━━━━━━━━━━━━━━━━\n\n"

        # Controlled Loss
        if stats.controlled_loss > 0:
            out += f"⚠️ *CONTROLLED LOSS* — {stats.controlled_loss} posisi >3%\\n\\n"
        else:
            out += "✅ *CONTROLLED LOSS* — 0 posisi\\n\\n"

        # Performance Distribution
        out += "*Performance Distribution*\\n"
        perf = stats.perf_distribution
        dist_items = [
            ("🟢 >10%", perf[">10%"]),
            ("🟢 5–10%", perf["5–10%"]),
            ("⚪ 0–5%", perf["0–5%"]),
            ("🔴 -0–3%", perf["-0–3%"]),
            ("🔴 <-5%", perf["<-3%"]),
        ]
        for label, count in dist_items:
            out += f"  {label} — {count} trades\\n"

        out += "\\n*Active Positions* — "
        out += f"{stats.total_positions} positions\\n"

        has_any = False
        for p in open_positions:
            has_any = True
            if not p.current_price:
                continue
            pnl_icon = "🟢" if p.unrealized_pnl >= 0 else "🔴"
            pnl_sign = "+" if p.unrealized_pnl >= 0 else ""
            tag_display = f"  `{p.tag}` " if p.tag else ""

            status = "🟢 Neutral" if p.unrealized_pnl_pct >= -5 else "🔴 Risk Zone"

            out += (
                f"  ⚡ *{p.symbol}*{tag_display}| Hari ke-{p.holding_days} | {status}\\n"
                f"     Entry Rp{p.entry_price:,.0f} | "
                f"{pnl_icon} {pnl_sign}{p.unrealized_pnl_pct:.1f}%\\n"
            )

        if not has_any:
            out += "  📭 Belum ada posisi aktif\\n"

        # Recent closed
        if closed_positions:
            out += "\\n*Recent Closed Trades*\\n"
            closed_sorted = sorted(closed_positions, key=lambda p: p.exit_date, reverse=True)
            for p in closed_sorted[:5]:
                pnl_icon = "🟢" if p.pnl >= 0 else "🔴"
                pnl_sign = "+" if p.pnl >= 0 else ""
                out += (
                    f"  {pnl_icon} *{p.symbol}* {p.holding_days}d | "
                    f"{pnl_sign}{p.pnl_pct:.1f}%\\n"
                )

        total_closed_pnl = sum(p.pnl for p in closed_positions)
        out += (
            f"\\n📈 *All-Time:* {len(closed_positions)} trades  |  "
            f"Win: {stats.win_rate:.0f}%  |  P&L: Rp{total_closed_pnl:,.0f}\\n"
        )

        return out

    def format_history(self, positions: List[Position]) -> str:
        """Format closed positions history."""
        closed = [p for p in positions if p.status == "closed"]
        if not closed:
            return "📜 Belum ada posisi yang ditutup."

        closed_sorted = sorted(closed, key=lambda p: p.exit_date, reverse=True)
        total_pnl = sum(p.pnl for p in closed)
        wins = sum(1 for p in closed if p.pnl > 0)
        wr = wins / len(closed) * 100 if closed else 0

        out = f"📜 *Trading History — {len(closed)} trades*\\n"
        out += "━━━━━━━━━━━━━━━━━━━━\\n\\n"
        out += f"Win Rate: {wr:.0f}% | Total P&L: Rp{total_pnl:,.0f}\\n\\n"

        for p in closed_sorted[:15]:
            d = "🟢" if p.pnl >= 0 else "🔴"
            date = p.exit_date[:10] if p.exit_date else "?"
            out += (
                f"{d} *{p.symbol}* {date} ({p.holding_days}d)\\n"
                f"  Rp{p.entry_price:,.0f} → Rp{p.exit_price:,.0f} | "
                f"P&L: Rp{p.pnl:,.0f} ({p.pnl_pct:+.1f}%)\\n"
            )

        if len(closed) > 15:
            out += f"\\n... dan {len(closed) - 15} trades lainnya"

        return out
