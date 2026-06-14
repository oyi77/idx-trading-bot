"""Portfolio Tracker — Real-time position tracking & P&L.

Commands:
  /portfolio                         — view all positions
  /portfolio add BBCA 4500 100      — add position (entry price, quantity in lots)
  /portfolio close BBCA 4800        — close position at exit price
  /portfolio history                — closed positions log

Storage: JSON per user in data/portfolios/
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple


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


class PortfolioEngine:
    """Manage user portfolio positions."""

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
            }
            for p in positions
        ]
        with open(self._path(user_id), "w") as f:
            json.dump(data, f, indent=2)

    def add(self, user_id: int, symbol: str, entry_price: float, quantity: int) -> Tuple[bool, str]:
        """Add a new position."""
        positions = self.load(user_id)
        symbol_upper = symbol.upper()

        # Check if already have open position for this symbol
        if any(p.symbol == symbol_upper and p.status == "open" for p in positions):
            return False, f"Sudah punya posisi {symbol_upper} yang open."

        positions.append(Position(
            symbol=symbol_upper,
            entry_price=entry_price,
            quantity=quantity,
            entry_date=datetime.now().isoformat(),
        ))
        self.save(user_id, positions)
        return True, f"✅ {symbol_upper} {quantity} lot @ Rp{entry_price:,.0f} ditambahkan ke portfolio"

    def close(self, user_id: int, symbol: str, exit_price: float) -> Tuple[bool, str]:
        """Close a position at exit price."""
        positions = self.load(user_id)
        symbol_upper = symbol.upper()

        for p in positions:
            if p.symbol == symbol_upper and p.status == "open":
                p.status = "closed"
                p.exit_price = exit_price
                p.exit_date = datetime.now().isoformat()
                # Calculate P&L (100 shares per lot)
                p.pnl = (exit_price - p.entry_price) * p.quantity * 100
                p.pnl_pct = ((exit_price / p.entry_price) - 1) * 100 if p.entry_price else 0
                self.save(user_id, positions)
                pnl_sign = "+" if p.pnl >= 0 else ""
                return True, (
                    f"🔒 Closed {symbol_upper}: {p.quantity} lot\n"
                    f"Entry: Rp{p.entry_price:,.0f} → Exit: Rp{exit_price:,.0f}\n"
                    f"P&L: {pnl_sign}Rp{p.pnl:,.0f} ({p.pnl_pct:+.1f}%)"
                )

        return False, f"Tidak ada posisi open untuk {symbol_upper}"

    async def refresh_prices(self, positions: List[Position]) -> List[Position]:
        """Refresh current prices for all open positions."""
        from src.feed.yahoo import YahooFeed
        feed = YahooFeed()

        for p in positions:
            if p.status != "open":
                continue
            try:
                quote = await feed.get_quote(p.symbol)
                if quote and quote.get("price"):
                    p.current_price = float(quote.get("price") or 0)
                    p.name = quote.get("name", p.symbol)
                    lot_value = p.current_price * 100  # 1 lot = 100 shares
                    p.current_value = lot_value * p.quantity
                    entry_value = p.entry_price * 100 * p.quantity
                    p.unrealized_pnl = p.current_value - entry_value
                    p.unrealized_pnl_pct = ((p.current_price / p.entry_price) - 1) * 100 if p.entry_price else 0
            except Exception:
                pass

        return positions

    def format_portfolio(self, positions: List[Position]) -> str:
        """Format portfolio for Telegram output."""
        open_positions = [p for p in positions if p.status == "open"]
        closed_positions = [p for p in positions if p.status == "closed"]

        total_value = sum(p.current_value for p in open_positions)
        total_entry = sum(p.entry_price * 100 * p.quantity for p in open_positions)
        total_pnl = total_value - total_entry
        total_pnl_pct = ((total_value / total_entry) - 1) * 100 if total_entry else 0

        pnl_emoji = "🟢" if total_pnl >= 0 else "🔴"

        out = "📊 *Portfolio Kamu*\n"
        out += "━━━━━━━━━━━━━━━━━━━━\n\n"

        if not open_positions:
            out += "🔹 *Tidak ada posisi open.*\n\n"
            out += "Tambah: `/portfolio add BBCA 4500 100`\n"
        else:
            out += f"💰 Total Value: *Rp{total_value:,.0f}*\n"
            out += f"{pnl_emoji} Unrealized P&L: Rp{total_pnl:,.0f} ({total_pnl_pct:+.1f}%)\n\n"

            out += "*📌 Open Positions:*\n"
            for p in open_positions:
                if p.current_price:
                    pnl = p.unrealized_pnl
                    pnl_pct = p.unrealized_pnl_pct
                    d = "🟢" if pnl >= 0 else "🔴"
                    out += (
                        f"{d} *{p.symbol}*  {p.quantity} lot\n"
                        f"  Entry Rp{p.entry_price:,.0f} → Now Rp{p.current_price:,.0f}\n"
                        f"  P&L: Rp{pnl:,.0f} ({pnl_pct:+.1f}%)\n"
                    )
                else:
                    out += (
                        f"⚪ *{p.symbol}*  {p.quantity} lot @ Rp{p.entry_price:,.0f}\n"
                        f"  _Menunggu data harga..._\n"
                    )

        if closed_positions:
            # Show last 3 closed
            out += "\n*📜 Recently Closed:*\n"
            closed_sorted = sorted(closed_positions, key=lambda p: p.exit_date, reverse=True)
            for p in closed_sorted[:3]:
                d = "🟢" if p.pnl >= 0 else "🔴"
                out += (
                    f"{d} *{p.symbol}*  "
                    f"Rp{p.entry_price:,.0f} → Rp{p.exit_price:,.0f}  "
                    f"P&L: Rp{p.pnl:,.0f}\n"
                )

        # Summary stats
        total_closed_pnl = sum(p.pnl for p in closed_positions)
        total_trades = len(closed_positions)
        wins = sum(1 for p in closed_positions if p.pnl > 0)

        if total_trades:
            wr = wins / total_trades * 100
            out += (
                f"\n━━━━━━━━━━━━━━━━━━━━\n"
                f"📈 All-Time: {total_trades} trades  |  Win: {wr:.0f}%  |  "
                f"P&L: Rp{total_closed_pnl:,.0f}\n"
            )

        out += (
            f"\nTambah posisi: `/portfolio add BBCA 4500 100`\n"
            f"Tutup posisi: `/portfolio close BBCA 4800`\n"
            f"Riwayat: `/portfolio history`"
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

        out = f"📜 *Trading History — {len(closed)} trades*\n"
        out += "━━━━━━━━━━━━━━━━━━━━\n\n"
        out += f"Win Rate: {wr:.0f}% | Total P&L: Rp{total_pnl:,.0f}\n\n"

        for p in closed_sorted[:15]:
            d = "🟢" if p.pnl >= 0 else "🔴"
            date = p.exit_date[:10] if p.exit_date else "?"
            out += (
                f"{d} *{p.symbol}* {date}\n"
                f"  Rp{p.entry_price:,.0f} → Rp{p.exit_price:,.0f} | "
                f"P&L: Rp{p.pnl:,.0f} ({p.pnl_pct:+.1f}%)\n"
            )

        if len(closed) > 15:
            out += f"\n... dan {len(closed) - 15} trades lainnya"

        return out
