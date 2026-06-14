#!/usr/bin/env python3
"""
AI Accuracy Resolver — Vilona Saham
====================================
Jalan tiap 60 menit via cron (atau manual).
Bandingin prediksi AI vs harga aktual untuk hitung akurasi.

Logic:
  - BUY signal + harga naik >1%  → BENAR
  - BUY signal + harga turun >1%  → SALAH
  - PASS signal + harga turun >1% → BENAR (avoided loss)
  - PASS signal + harga naik >1%  → SALAH (missed gain)
  - WATCH signal + harga flat      → BENAR (correctly cautious)
  - Dalam ±1%                      → netral (skip, bukan win/loss jelas)

Simpan hasil ke AnalysisJournal.resolved + accuracy_pct.
"""
import asyncio
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import yfinance as yf

# ── Setup ──────────────────────────────────────────────────
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("accuracy-tracker")

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from src.config import settings
from src.models import AnalysisJournal


def get_session():
    sync_url = settings.database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    engine = create_engine(sync_url)
    Session = sessionmaker(bind=engine)
    return Session(), engine


def fetch_current_price(symbol: str) -> float | None:
    """Fetch latest price for a symbol."""
    try:
        ticker = yf.Ticker(f"{symbol}.JK")
        price = ticker.fast_info.last_price
        if price and price > 0:
            return float(price)
        hist = ticker.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception as e:
        logger.warning(f"Price fetch failed for {symbol}: {e}")
    return None


def classify_accuracy(
    signal: str,
    bias: str,
    price_at_analysis: float,
    current_price: float,
) -> tuple[float, str]:
    """Classify prediction accuracy.

    Returns: (accuracy_pct, verdict)
      - accuracy_pct > 0: correct (magnitude = confidence)
      - accuracy_pct < 0: wrong
      - accuracy_pct = 0: neutral/unclear
    """
    if not price_at_analysis or price_at_analysis <= 0:
        return 0, "no_price"

    pct_change = (current_price - price_at_analysis) / price_at_analysis * 100

    # Neutral zone (±0.5%) — too close to call
    if abs(pct_change) < 0.5:
        return 0, "neutral"

    went_up = pct_change > 0

    # BUY signal: should go up
    if signal == "BUY" or bias == "BULLISH":
        if went_up:
            return min(pct_change, 10), "correct_up"
        else:
            return max(pct_change, -10), "wrong_down"

    # PASS signal: should go down (correctly avoided)
    if signal == "PASS" or bias == "BEARISH":
        if not went_up:
            return min(abs(pct_change), 10), "correct_avoided"
        else:
            return min(-pct_change, -10), "wrong_missed"

    # WATCH / NEUTRAL
    return 0, "neutral"


def resolve_analyses(session) -> dict:
    """Resolve all pending analyses older than 6 hours."""
    cutoff = datetime.utcnow() - timedelta(hours=6)

    pending = (
        session.query(AnalysisJournal)
        .filter(
            AnalysisJournal.resolved == False,
            AnalysisJournal.timestamp <= cutoff,
            AnalysisJournal.price_at_analysis > 0,
        )
        .all()
    )

    if not pending:
        return {"total": 0, "resolved": 0, "correct": 0, "wrong": 0}

    resolved = 0
    correct = 0
    wrong = 0

    # Group by symbol for batch fetch
    symbols = list(set(a.symbol for a in pending))
    prices = {}
    for sym in symbols:
        prices[sym] = fetch_current_price(sym)

    for analysis in pending:
        current_price = prices.get(analysis.symbol)
        if current_price is None:
            continue

        signal = analysis.signal or "WATCH"
        bias = analysis.bias or "NEUTRAL"
        entry_price = analysis.price_at_analysis

        accuracy, verdict = classify_accuracy(
            signal, bias, entry_price, current_price
        )

        analysis.resolved = True
        analysis.actual_price = current_price
        analysis.accuracy_pct = accuracy
        analysis.resolved_at = datetime.utcnow()

        resolved += 1
        if accuracy > 0:
            correct += 1
        elif accuracy < 0:
            wrong += 1

        logger.info(
            f"  {analysis.symbol}: {signal}/{bias} @ {entry_price:,.0f} → "
            f"{current_price:,.0f} ({accuracy:+.1f}%) [{verdict}]"
        )

    session.commit()

    return {
        "total": len(pending),
        "resolved": resolved,
        "correct": correct,
        "wrong": wrong,
        "accuracy_pct": round(correct / resolved * 100, 1) if resolved > 0 else 0,
    }


def get_overall_stats(session) -> dict:
    """Get cumulative accuracy stats."""
    total_resolved = (
        session.query(func.count(AnalysisJournal.id))
        .filter(AnalysisJournal.resolved == True, AnalysisJournal.accuracy_pct.isnot(None))
        .scalar() or 0
    )
    correct_count = (
        session.query(func.count(AnalysisJournal.id))
        .filter(
            AnalysisJournal.resolved == True,
            AnalysisJournal.accuracy_pct > 0,
        )
        .scalar() or 0
    )

    # By experiment tag
    experiments = (
        session.query(
            AnalysisJournal.experiment_tag,
            func.count(AnalysisJournal.id),
        )
        .filter(AnalysisJournal.resolved == True)
        .group_by(AnalysisJournal.experiment_tag)
        .all()
    )

    # Weekly accuracy
    week_start = datetime.utcnow() - timedelta(days=7)
    week_resolved = (
        session.query(func.count(AnalysisJournal.id))
        .filter(
            AnalysisJournal.resolved == True,
            AnalysisJournal.resolved_at >= week_start,
            AnalysisJournal.accuracy_pct.isnot(None),
        )
        .scalar() or 0
    )
    week_correct = (
        session.query(func.count(AnalysisJournal.id))
        .filter(
            AnalysisJournal.resolved == True,
            AnalysisJournal.resolved_at >= week_start,
            AnalysisJournal.accuracy_pct > 0,
        )
        .scalar() or 0
    )

    # By signal type
    by_signal = dict(
        session.query(
            AnalysisJournal.signal,
            func.count(AnalysisJournal.id),
        )
        .filter(AnalysisJournal.resolved == True)
        .group_by(AnalysisJournal.signal)
        .all()
    )

    return {
        "total_resolved": total_resolved,
        "total_correct": correct_count,
        "overall_accuracy": round(correct_count / total_resolved * 100, 1) if total_resolved > 0 else 0,
        "weekly_resolved": week_resolved,
        "weekly_correct": week_correct,
        "weekly_accuracy": round(week_correct / week_resolved * 100, 1) if week_resolved > 0 else 0,
        "experiments": [{"tag": t, "count": c} for t, c in experiments],
        "by_signal": by_signal,
    }


# ═══════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════

def main():
    logger.info("=" * 50)
    logger.info("AI Accuracy Resolver — starting")

    session, engine = get_session()

    try:
        result = resolve_analyses(session)

        if result["total"] == 0:
            logger.info("No pending analyses to resolve")
        else:
            logger.info(
                f"Resolved: {result['resolved']}/{result['total']} | "
                f"Correct: {result['correct']} | Wrong: {result['wrong']} | "
                f"Accuracy: {result['accuracy_pct']}%"
            )

        # Print overall stats
        stats = get_overall_stats(session)
        logger.info(
            f"Cumulative: {stats['total_resolved']} resolved | "
            f"{stats['overall_accuracy']}% accuracy overall"
        )
        logger.info(
            f"This week: {stats['weekly_resolved']} resolved | "
            f"{stats['weekly_accuracy']}% accuracy"
        )

        logger.info("AI Accuracy Resolver — done")

    except Exception as e:
        logger.error(f"Resolver error: {e}", exc_info=True)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
