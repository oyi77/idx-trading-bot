#!/usr/bin/env python3
"""Accuracy Checker — resolves analysis_journal entries by comparing price now vs price at analysis.

Run: python3 cron/resolve_accuracy.py
Schedule: daily at 16:30 WIB (after market close)
"""
import json
import sys
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "trading_bot.db"

def resolve_pending(timeframe_hours: int = 24):
    """Resolve analyses older than timeframe_hours that haven't been resolved yet."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    count = cur.execute("SELECT COUNT(*) FROM analysis_journal WHERE resolved = 0").fetchone()[0]
    print(f"Pending unresolved: {count}")

    rows = cur.execute(
        """SELECT id, analysis_id, symbol, price_at_analysis, signal, timestamp
           FROM analysis_journal
           WHERE resolved = 0
             AND timestamp <= ?
           ORDER BY timestamp ASC""",
        ((datetime.utcnow() - timedelta(hours=timeframe_hours)).isoformat(),),
    ).fetchall()

    if not rows:
        print("No entries to resolve.")
        conn.close()
        return []

    resolved = []
    for r in rows:
        old_price = r["price_at_analysis"]
        if not old_price or old_price <= 0:
            continue

        # Fetch latest price — try yfinance first
        try:
            import yfinance as yf
            ticker = yf.Ticker(f"{r['symbol']}.JK")
            data = ticker.history(period="1d")
            if data.empty:
                print(f"  ⚠️ {r['symbol']}: No yfinance data")
                continue
            latest = float(data["Close"].iloc[-1])
        except Exception:
            print(f"  ⚠️ {r['symbol']}: yfinance failed")
            continue

        sig = r["signal"]
        diff_pct = (latest - old_price) / old_price

        # Determine accuracy
        if sig == "BUY":
            correct = diff_pct > 0.01  # >1% up
        elif sig == "PASS":
            correct = diff_pct < -0.01  # >1% down
        else:  # WATCH
            correct = abs(diff_pct) <= 0.02  # within ±2%

        cur.execute(
            """UPDATE analysis_journal
               SET resolved = 1, actual_price = ?, accuracy_pct = ?, resolved_at = ?
               WHERE id = ?""",
            (latest, diff_pct, datetime.utcnow().isoformat(), r["id"]),
        )

        icon = "✅" if correct else "❌"
        print(f"  {icon} {r['symbol']}: {r['signal']} @ {old_price:,} → {latest:,} ({diff_pct:+.2%})")
        resolved.append({"symbol": r["symbol"], "signal": sig, "correct": correct, "diff_pct": diff_pct})

    conn.commit()
    conn.close()
    print(f"\nResolved {len(resolved)}/{len(rows)} entries.")
    return resolved


if __name__ == "__main__":
    print(f"🏛️  Accuracy Checker — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("━" * 50)
    results = resolve_pending(timeframe_hours=24)  # resolve after 24h (next market day)
    if results:
        correct = sum(1 for r in results if r["correct"])
        print(f"Accuracy: {correct}/{len(results)} ({correct/len(results)*100:.1f}%)")
