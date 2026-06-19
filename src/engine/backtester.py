"""Backtester Engine — Validates signal accuracy against actual price movement.

How it works:
1. Take historical signals (from signal_engine or journal)
2. Compare entry/TP/SL against actual subsequent price data
3. Calculate win rate, avg return, max drawdown per strategy
4. Feed results back to learning engine for parameter tuning

Win rate target: 92%+ (progressive optimization)
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)

RESULTS_DIR = Path("data/backtest_results")


@dataclass
class BacktestTrade:
    """Single backtested trade result."""
    symbol: str
    signal_type: str          # "swing" | "scalp"
    direction: str            # "LONG"
    entry_price: float
    tp1: float
    tp2: float
    sl: float
    entry_date: str
    exit_date: Optional[str] = None
    exit_price: Optional[float] = None
    exit_reason: str = ""     # "tp1" | "tp2" | "sl" | "timeout"
    pnl_pct: float = 0.0
    is_win: bool = False
    bars_held: int = 0


@dataclass
class BacktestReport:
    """Aggregated backtest results."""
    strategy: str             # "swing" | "scalp"
    period: str               # "2026-06-01 to 2026-06-15"
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    avg_return_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    avg_rr_achieved: float = 0.0
    best_trade_pct: float = 0.0
    worst_trade_pct: float = 0.0
    trades: List[BacktestTrade] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now().strftime("%d %b %Y %H:%M"))


@dataclass
class OptimizationSuggestion:
    """Parameter adjustment suggestion based on backtest."""
    param: str
    current_value: float
    suggested_value: float
    reason: str
    expected_impact: str      # "win_rate +2%", "avg_return +0.5%"


def backtest_signal(
    symbol: str,
    signal_type: str,
    entry_price: float,
    tp1: float,
    tp2: float,
    sl: float,
    future_closes: List[float],
    future_highs: List[float],
    future_lows: List[float],
    max_bars: int = 20,
) -> BacktestTrade:
    """Backtest a single signal against actual future price data.

    Args:
        symbol: stock code
        signal_type: "swing" or "scalp"
        entry_price: signal entry price
        tp1, tp2, sl: signal levels
        future_closes: actual close prices after signal
        future_highs: actual high prices after signal
        future_lows: actual low prices after signal
        max_bars: max holding period before timeout

    Returns:
        BacktestTrade with result.
    """
    trade = BacktestTrade(
        symbol=symbol,
        signal_type=signal_type,
        direction="LONG",
        entry_price=entry_price,
        tp1=tp1,
        tp2=tp2,
        sl=sl,
        entry_date="",
    )

    bars = min(len(future_closes), max_bars)
    if bars == 0:
        trade.exit_reason = "no_data"
        return trade

    for i in range(bars):
        high = future_highs[i]
        low = future_lows[i]
        close = future_closes[i]

        # Check SL hit first (risk management priority)
        if low <= sl:
            trade.exit_price = sl
            trade.exit_reason = "sl"
            trade.bars_held = i + 1
            trade.pnl_pct = round((sl - entry_price) / entry_price * 100, 2)
            trade.is_win = False
            return trade

        # Check TP2 hit
        if high >= tp2:
            trade.exit_price = tp2
            trade.exit_reason = "tp2"
            trade.bars_held = i + 1
            trade.pnl_pct = round((tp2 - entry_price) / entry_price * 100, 2)
            trade.is_win = True
            return trade

        # Check TP1 hit
        if high >= tp1 and trade.exit_reason != "tp1":
            trade.exit_price = tp1
            trade.exit_reason = "tp1"
            trade.bars_held = i + 1
            trade.pnl_pct = round((tp1 - entry_price) / entry_price * 100, 2)
            trade.is_win = True
            # Don't return yet — might hit TP2 later

    # Timeout: exit at last close
    trade.exit_price = future_closes[bars - 1]
    trade.exit_reason = "timeout"
    trade.bars_held = bars
    trade.pnl_pct = round((trade.exit_price - entry_price) / entry_price * 100, 2)
    trade.is_win = trade.pnl_pct > 0
    return trade


def generate_report(trades: List[BacktestTrade], strategy: str, period: str) -> BacktestReport:
    """Generate aggregated report from backtest trades."""
    report = BacktestReport(strategy=strategy, period=period, trades=trades)

    if not trades:
        return report

    report.total_trades = len(trades)
    report.wins = sum(1 for t in trades if t.is_win)
    report.losses = report.total_trades - report.wins
    report.win_rate = round(report.wins / report.total_trades * 100, 2) if report.total_trades > 0 else 0

    returns = [t.pnl_pct for t in trades]
    report.avg_return_pct = round(sum(returns) / len(returns), 2) if returns else 0
    report.best_trade_pct = round(max(returns), 2) if returns else 0
    report.worst_trade_pct = round(min(returns), 2) if returns else 0

    # Max drawdown (cumulative)
    cumulative = 0
    peak = 0
    max_dd = 0
    for r in returns:
        cumulative += r
        peak = max(peak, cumulative)
        dd = peak - cumulative
        max_dd = max(max_dd, dd)
    report.max_drawdown_pct = round(max_dd, 2)

    # Avg R:R achieved
    rr_list = []
    for t in trades:
        risk = abs(t.entry_price - t.sl) if t.sl != t.entry_price else 1
        reward = abs(t.exit_price - t.entry_price) if t.exit_price else 0
        if risk > 0:
            rr_list.append(reward / risk)
    report.avg_rr_achieved = round(sum(rr_list) / len(rr_list), 2) if rr_list else 0

    return report


def suggest_optimizations(report: BacktestReport) -> List[OptimizationSuggestion]:
    """Suggest parameter adjustments to improve win rate toward 92% target.

    Analyzes loss patterns and suggests concrete adjustments.
    """
    suggestions = []
    TARGET_WIN_RATE = 92.0

    if report.win_rate >= TARGET_WIN_RATE:
        suggestions.append(OptimizationSuggestion(
            param="status",
            current_value=report.win_rate,
            suggested_value=report.win_rate,
            reason=f"Win rate {report.win_rate}% sudah di atas target {TARGET_WIN_RATE}%",
            expected_impact="Maintain current parameters",
        ))
        return suggestions

    gap = TARGET_WIN_RATE - report.win_rate

    # Analyze loss patterns
    losses = [t for t in report.trades if not t.is_win]
    sl_hits = [t for t in losses if t.exit_reason == "sl"]
    timeout_losses = [t for t in losses if t.exit_reason == "timeout" and t.pnl_pct < 0]

    # Too many SL hits → widen SL or tighten entry criteria
    if len(sl_hits) > len(losses) * 0.6:
        avg_loss = sum(abs(t.pnl_pct) for t in sl_hits) / len(sl_hits) if sl_hits else 0
        suggestions.append(OptimizationSuggestion(
            param="sl_atr_multiplier",
            current_value=1.5,
            suggested_value=1.8,
            reason=f"{len(sl_hits)}/{len(losses)} losses dari SL hit. Avg loss: {avg_loss:.1f}%",
            expected_impact=f"Kurangi SL hit ~15%, win rate +{min(gap, 3):.0f}%",
        ))

    # Too many timeout losses → reduce max holding period or tighten entry
    if len(timeout_losses) > len(losses) * 0.4:
        suggestions.append(OptimizationSuggestion(
            param="min_score_threshold",
            current_value=50,
            suggested_value=55,
            reason=f"{len(timeout_losses)} trades loss karena timeout (gerak lambat)",
            expected_impact="Filter sinyal lemah, win rate +2-4%",
        ))

    # Low avg return → adjust TP levels
    if report.avg_return_pct < 1.5:
        suggestions.append(OptimizationSuggestion(
            param="tp1_atr_multiplier",
            current_value=1.5,
            suggested_value=1.2,
            reason=f"Avg return hanya {report.avg_return_pct}%. TP terlalu jauh, sering timeout",
            expected_impact="TP lebih sering kena, win rate +2%",
        ))

    # R:R too low
    if report.avg_rr_achieved < 1.0:
        suggestions.append(OptimizationSuggestion(
            param="min_rr_ratio",
            current_value=1.0,
            suggested_value=1.3,
            reason=f"Avg R:R achieved hanya {report.avg_rr_achieved}. Risk tidak ter-reward",
            expected_impact="Filter low R:R setups, kualitas naik",
        ))

    # Entry too loose
    if report.win_rate < 70:
        suggestions.append(OptimizationSuggestion(
            param="min_confidence",
            current_value=50,
            suggested_value=60,
            reason=f"Win rate {report.win_rate}% — terlalu banyak sinyal lemah masuk",
            expected_impact="Filter ketat, win rate +5-8%",
        ))

    return suggestions


async def run_weekly_backtest(
    signal_type: str = "swing",
    lookback_days: int = 7,
) -> BacktestReport:
    """Run backtest on recent signals using actual price data.

    Fetches cached data, generates signals for past dates,
    then validates against subsequent price movement.
    """
    from src.engine.screener_cache import fetch_all_cached
    from src.engine.signal_engine import generate_swing_signals, generate_scalp_signals

    data = await fetch_all_cached()
    if not data:
        return BacktestReport(
            strategy=signal_type,
            period="No data available",
        )

    gen_func = generate_swing_signals if signal_type == "swing" else generate_scalp_signals
    max_bars = 20 if signal_type == "swing" else 5
    all_trades: List[BacktestTrade] = []

    for sym, bars in data.items():
        if not isinstance(bars, list) or len(bars) < 60:
            continue

        try:
            closes = [b["close"] for b in bars]
            highs = [b["high"] for b in bars]
            lows = [b["low"] for b in bars]
            volumes = [int(b["volume"]) for b in bars]

            # Use first 50 bars for signal, remaining for backtest
            sig_closes = closes[:50]
            sig_highs = highs[:50]
            sig_lows = lows[:50]
            sig_volumes = volumes[:50]

            signals = gen_func(sym, sig_closes, sig_highs, sig_lows, sig_volumes, max_signals=1)
            if not signals:
                continue

            sig = signals[0]
            future_closes = closes[50:]
            future_highs = highs[50:]
            future_lows = lows[50:]

            trade = backtest_signal(
                symbol=sym,
                signal_type=signal_type,
                entry_price=sig.entry_price,
                tp1=sig.tp1,
                tp2=sig.tp2,
                sl=sig.sl,
                future_closes=future_closes,
                future_highs=future_highs,
                future_lows=future_lows,
                max_bars=max_bars,
            )
            all_trades.append(trade)

        except Exception as e:
            logger.debug(f"Backtest skip {sym}: {e}")
            continue

    now = datetime.now().strftime("%d %b %Y")
    period = f"{now} (lookback {lookback_days}d)"
    report = generate_report(all_trades, signal_type, period)

    # Save report
    _save_report(report)

    return report


def _save_report(report: BacktestReport) -> None:
    """Save backtest report to disk for historical tracking."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{report.strategy}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"

    data = {
        "strategy": report.strategy,
        "period": report.period,
        "total_trades": report.total_trades,
        "wins": report.wins,
        "losses": report.losses,
        "win_rate": report.win_rate,
        "avg_return_pct": report.avg_return_pct,
        "max_drawdown_pct": report.max_drawdown_pct,
        "avg_rr_achieved": report.avg_rr_achieved,
        "best_trade_pct": report.best_trade_pct,
        "worst_trade_pct": report.worst_trade_pct,
        "generated_at": report.generated_at,
        "trades": [
            {
                "symbol": t.symbol,
                "entry": t.entry_price,
                "exit": t.exit_price,
                "exit_reason": t.exit_reason,
                "pnl_pct": t.pnl_pct,
                "is_win": t.is_win,
                "bars_held": t.bars_held,
            }
            for t in report.trades
        ],
    }

    with open(RESULTS_DIR / filename, "w") as f:
        json.dump(data, f, indent=2)

    logger.info(f"Backtest report saved: {RESULTS_DIR / filename}")


def format_report_telegram(report: BacktestReport) -> str:
    """Format backtest report for Telegram display."""
    emoji = "✅" if report.win_rate >= 92 else "⚠️" if report.win_rate >= 80 else "❌"

    lines = [
        f"📊 *Backtest Report — {report.strategy.upper()}*",
        f"📅 {report.period}",
        f"━━━━━━━━━━━━━━━━━━━━",
        "",
        f"{emoji} *Win Rate: {report.win_rate}%* (target: 92%)",
        f"📈 Total Trades: {report.total_trades}",
        f"✅ Wins: {report.wins} | ❌ Losses: {report.losses}",
        "",
        f"💰 Avg Return: {report.avg_return_pct}%",
        f"🏆 Best: +{report.best_trade_pct}%",
        f"💀 Worst: {report.worst_trade_pct}%",
        f"📉 Max Drawdown: {report.max_drawdown_pct}%",
        f"📐 Avg R:R: {report.avg_rr_achieved}",
        "",
    ]

    # Top winners
    winners = sorted([t for t in report.trades if t.is_win], key=lambda t: t.pnl_pct, reverse=True)[:3]
    if winners:
        lines.append("*Top Winners:*")
        for t in winners:
            lines.append(f"  🟢 {t.symbol}: +{t.pnl_pct}% ({t.exit_reason}, {t.bars_held} bar)")
        lines.append("")

    # Worst losers
    losers = sorted([t for t in report.trades if not t.is_win], key=lambda t: t.pnl_pct)[:3]
    if losers:
        lines.append("*Worst Losers:*")
        for t in losers:
            lines.append(f"  🔴 {t.symbol}: {t.pnl_pct}% ({t.exit_reason}, {t.bars_held} bar)")

    return "\n".join(lines)
