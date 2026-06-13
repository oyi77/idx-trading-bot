"""AI Learning Loop — learns from past analysis accuracy & user feedback."""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = Path.home() / "idx-trading-bot" / "data" / "trading_bot.db"


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def get_recent_analyses(symbol: str, limit: int = 5) -> list[dict]:
    """Fetch past analyses for a symbol to detect patterns."""
    conn = _get_conn()
    cur = conn.cursor()
    # Get from journal (async table), read only via sync fallback
    try:
        cur.execute(
            """SELECT symbol, signal, score, accuracy_pct, bias, ai_insight,
                      key_indicators, resolved, user_rating
               FROM analysis_journal
               WHERE symbol = ? AND timestamp >= ?
               ORDER BY timestamp DESC LIMIT ?""",
            (symbol, (datetime.utcnow() - timedelta(days=30)).isoformat(), limit),
        )
        rows = [dict(r) for r in cur.fetchall()]
    except Exception:
        rows = []
    finally:
        conn.close()
    return rows


def format_learning_context(symbol: str, max_examples: int = 5) -> str:
    """Build an LLM prompt snippet from past analysis performance.

    Returns empty string if no tracked data yet.
    """
    rows = get_recent_analyses(symbol, limit=max_examples)
    if not rows:
        return ""

    resolved = [r for r in rows if r["resolved"]]
    total = len(resolved)
    correct = sum(1 for r in resolved if r.get("accuracy_pct", 0) or 0 > -0.02)
    # ^ we treat accuracy_pct > -2% as "close enough" for WATCH; BUY signals need positive accuracy

    # Determine which signals are valid
    buy_right = 0
    buy_wrong = 0
    watch_correct = 0
    wrong_patterns = []

    for r in resolved:
        sig = r.get("signal", "")
        acc = r.get("accuracy_pct", 0) or 0
        insight = r.get("ai_insight", "") or ""

        if sig == "BUY":
            if acc > 0.02:
                buy_right += 1
            elif acc < -0.02:
                buy_wrong += 1
                # Extract what went wrong
                wrong_patterns.append(insight[:80])
        elif sig == "PASS" and acc < -0.02:
            watch_correct += 1

    lines = []
    lines.append("📚 *HISTORI ANALISA — BELAJAR DARI MASA LALU*")
    lines.append(f"`{symbol}` — {total} analisa terverifikasi, {len(rows)} total")

    if buy_right + buy_wrong > 0:
        rate = buy_right / (buy_right + buy_wrong) * 100 if (buy_right + buy_wrong) > 0 else 0
        lines.append(f"  • Akurasi BUY: {rate:.0f}% ({buy_right} ✅ / {buy_wrong} ❌)")

    # Recent examples
    for r in rows[:3]:
        sig = r.get("signal", "?")
        score = r.get("score", "?")
        acc = r.get("accuracy_pct")
        rating = r.get("user_rating")
        acc_str = f" → {acc:+.1f}%" if acc is not None else " → belum di-resolve"
        star = "⭐" if rating and rating >= 4 else ""
        lines.append(f"  • {sig} (score {score}){acc_str} {star}")

    # Pattern warnings
    if wrong_patterns:
        lines.append(f"\n⚠️ *Pola kesalahan:* BUY terlalu agresif saat downtrend ({buy_wrong}x gagal)")
        if buy_wrong >= 2:
            lines.append("  ➡️ Saran: Verifikasi MA20 uptrend sebelum BUY")

    if buy_right >= 3:
        lines.append("\n✅ *Pola sukses:* Momentum + volume spike konsisten")

    return "\n".join(lines)


def get_symbol_accuracy_summary(symbol: str) -> dict:
    """Return accuracy stats for a symbol (used in weekly report)."""
    rows = get_recent_analyses(symbol, limit=50)
    resolved = [r for r in rows if r["resolved"]]
    if not resolved:
        return {"symbol": symbol, "total": 0, "accuracy": 0}

    total = len(resolved)
    # BUY correct if price went up >1%, WATCH correct if |change| < 2%
    correct = 0
    for r in resolved:
        sig = r.get("signal", "")
        acc = r.get("accuracy_pct", 0) or 0
        if sig == "BUY" and acc > 0.01:
            correct += 1
        elif sig == "PASS" and acc < -0.01:
            correct += 1
        elif sig == "WATCH" and -0.02 <= acc <= 0.02:
            correct += 1

    return {
        "symbol": symbol,
        "total": total,
        "accuracy": round(correct / total * 100, 1) if total > 0 else 0,
    }


def record_user_feedback(analysis_id: str, rating: int, feedback_text: str = "") -> bool:
    """Record user rating for an analysis."""
    conn = _get_conn()
    try:
        conn.execute(
            """UPDATE analysis_journal
               SET user_rating = ?, user_feedback_text = ?, feedback_at = ?
               WHERE analysis_id = ?""",
            (rating, feedback_text, datetime.utcnow().isoformat(), analysis_id),
        )
        conn.commit()
        return conn.total_changes > 0
    except Exception as e:
        logger.warning(f"Feedback record failed: {e}")
        return False
    finally:
        conn.close()
