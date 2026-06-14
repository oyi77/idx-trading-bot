#!/usr/bin/env python3
"""Weekly Accuracy Report — generated every Sunday 19:00 WIB."""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path.home() / "idx-trading-bot" / "data" / "trading_bot.db"

def generate_weekly():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()

    # Total analyses this week
    total = cur.execute("SELECT COUNT(*) FROM analysis_journal WHERE timestamp >= ?", (week_ago,)).fetchone()[0]
    resolved = cur.execute("SELECT COUNT(*) FROM analysis_journal WHERE timestamp >= ? AND resolved = 1", (week_ago,)).fetchone()[0]

    # Segment by signal
    signals = cur.execute(
        """SELECT signal, COUNT(*) as cnt, 
                  SUM(CASE WHEN resolved=1 AND accuracy_pct > 0.01 THEN 1 ELSE 0 END) as good
           FROM analysis_journal
           WHERE timestamp >= ?
           GROUP BY signal""",
        (week_ago,),
    ).fetchall()

    # Best/worst symbols
    symbols = cur.execute(
        """SELECT symbol, COUNT(*) as cnt,
                  AVG(accuracy_pct) as avg_acc
           FROM analysis_journal
           WHERE timestamp >= ? AND resolved = 1
           GROUP BY symbol
           HAVING cnt >= 2
           ORDER BY avg_acc DESC
           LIMIT 10""",
        (week_ago,),
    ).fetchall()

    conn.close()

    # Build report
    lines = [
        "📈 *VILONA — WEEKLY ACCURACY REPORT*",
        f"`{datetime.utcnow().strftime('%d %b %Y, Week %W')}`",
        "━" * 40,
        f"Total Analisa: {total}",
        f"Terverifikasi: {resolved}",
        "",
    ]

    if signals:
        lines.append("📊 *Akurasi per Signal*:")
        for s in signals:
            sig = s["signal"]
            cnt = s["cnt"]
            good = s["good"] or 0
            pct = round(good / cnt * 100, 1) if cnt > 0 else 0
            lines.append(f"  • {sig}: {pct}% ({good}/{cnt})")

    if symbols:
        lines.append(f"\n🏆 *Top Symbols*:")
        for s in symbols[:5]:
            acc = round((s["avg_acc"] or 0) * 100, 1)
            lines.append(f"  • {s['symbol']}: {acc}% ({s['cnt']} analisa)")

    if resolved > 0:
        correct = cur.execute("SELECT COUNT(*) FROM analysis_journal WHERE timestamp >= ? AND resolved=1 AND accuracy_pct > 0.01", (week_ago,)).fetchone()[0]
        overall = round(correct / resolved * 100, 1) if resolved > 0 else 0
        lines.append(f"\n🎯 *Overall Accuracy: {overall}%*")

    return "\n".join(lines)

if __name__ == "__main__":
    print(generate_weekly())
