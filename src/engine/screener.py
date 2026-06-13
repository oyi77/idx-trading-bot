"""Screener engine — combines all analysis modules for stock screening.
Mimics HQSahamIDX scoring system (/SCORE command).

Uses real data from:
  - TechnicalEngine (yfinance fallback when iTick unavailable)
  - FundamentalEngine (yfinance) ✅
  - BrokerFlowEngine (Infovesta API) ✅
"""
from typing import Dict, List, Optional, Tuple

from src.engine.technical import TechnicalEngine
from src.engine.fundamental import FundamentalEngine, FundamentalData
from src.engine.broker_flow import BrokerFlowEngine


def _fetch_ohlcv_yfinance(symbol: str):
    """Fetch OHLCV data from Yahoo Finance as fallback."""
    import yfinance as yf
    import pandas as pd
    
    try:
        ticker = yf.Ticker(f"{symbol}.JK")
        hist = ticker.history(period="6mo")
        if hist.empty:
            return None, None, None, None
        
        closes = hist["Close"].tolist()
        highs = hist["High"].tolist()
        lows = hist["Low"].tolist()
        volumes = hist["Volume"].tolist()
        return closes, highs, lows, volumes
    except Exception:
        return None, None, None, None


class ScreenerEngine:
    """Combinatorial screener — run multiple rules, output combined score.

    Rules available:
    - Technical: RSI, MACD, Bollinger, SuperTrend, Volume
    - Fundamental: PER, PBV, ROE, DER, growth
    - Foreign Flow: net buy/sell, accumulation streak
    """

    def __init__(self):
        self.tech = TechnicalEngine()
        self.fundamental = FundamentalEngine()
        self.flow = BrokerFlowEngine()

    async def screen(
        self,
        symbols: list,
        rules: list = None,
        min_score: int = 5,
        max_score: int = 10,
    ) -> list:
        """Screen multiple symbols with rules, return those above min_score.

        Args:
            symbols: list of stock codes (e.g. ['BBCA', 'BBRI'])
            rules: list of rule categories.
                   Default: ['technical', 'fundamental', 'foreign_flow']
            min_score: minimum combined score (0-10)
        """
        results = []
        for symbol in symbols:
            score, reasons = await self._score_symbol(
                symbol, rules or ["technical", "fundamental", "foreign_flow"]
            )
            if score >= min_score:
                results.append({
                    "symbol": symbol,
                    "score": score,
                    "max_score": max_score,
                    "reasons": reasons,
                    "signal": (
                        "BUY" if score >= 7
                        else "WATCH" if score >= 5
                        else "PASS"
                    ),
                })
        return sorted(results, key=lambda x: x["score"], reverse=True)

    async def _score_symbol(self, symbol: str, rules: list) -> Tuple[int, list]:
        """Score a single symbol based on active rule categories."""
        total_score = 0
        available_score = 0
        reasons = []

        # ─── Technical ─────────────────────────────────────
        if "technical" in rules:
            available_score += 4
            try:
                import asyncio
                closes, highs, lows, volumes = await asyncio.to_thread(
                    _fetch_ohlcv_yfinance, symbol
                )
                
                if closes and len(closes) > 20:
                    analysis = self.tech.analyze(
                        symbol, closes, highs, lows, volumes
                    )
                    
                    tech_analysis = analysis.get("analysis", {})
                    combined = analysis.get("combined", {})
                    ts = combined.get("score", tech_analysis.get("score", 0))
                    tech_score = round(ts / 10 * 4)
                    total_score += tech_score

                    trend = tech_analysis.get("trend", "neutral")
                    price = analysis.get("price", "N/A")
                    
                    if ts >= 7:
                        reasons.append(f"📈 Bullish ({trend}), Price: {price}")
                    elif ts >= 5:
                        reasons.append(f"📊 Mixed ({trend}), Price: {price}")
                    else:
                        reasons.append(f"📉 Bearish ({trend}), Price: {price}")
                else:
                    reasons.append("⚠️ Data teknikal tidak cukup")

            except Exception as e:
                reasons.append(f"⚠️ Teknikal: {str(e)[:50]}")

        # ─── Fundamental ────────────────────────────────────
        if "fundamental" in rules:
            available_score += 3
            try:
                fd = await self.fundamental.fetch(symbol)
                if fd and fd.per > 0:
                    funda_score = 0

                    if 5 <= fd.per <= 15:
                        funda_score += 1
                        reasons.append(f"✅ PER wajar ({fd.per:.1f}x)")
                    elif fd.per > 0:
                        reasons.append(f"➖ PER {fd.per:.1f}x")

                    if fd.roe >= 15:
                        funda_score += 1
                        reasons.append(f"✅ ROE kuat ({fd.roe:.1f}%)")
                    elif fd.roe > 0:
                        reasons.append(f"➖ ROE {fd.roe:.1f}%")

                    if fd.pbv < 2 and fd.der < 1:
                        funda_score += 1
                        reasons.append(f"✅ Valuasi murah (PBV={fd.pbv:.1f}, DER={fd.der:.1f})")
                    else:
                        reasons.append(f"➖ Valuasi standar")

                    total_score += min(funda_score, 3)
                else:
                    reasons.append("⚠️ Fundamental: N/A")

            except Exception as e:
                reasons.append(f"⚠️ Fundamental error")

        # ─── Foreign Flow ───────────────────────────────────
        if "foreign_flow" in rules:
            available_score += 3
            try:
                flow = await self.flow.get_foreign_flow(symbol)
                if flow and flow.net_buy != 0:
                    flow_score = 0

                    if flow.is_net_buy():
                        flow_score += 1
                        reasons.append(f"🟢 Net Buy Rp{flow.net_buy:,.0f}")
                    else:
                        reasons.append(f"🔴 Net Sell Rp{abs(flow.net_buy):,.0f}")

                    if flow.streak_days >= 3:
                        flow_score += 1
                        reasons.append(f"🔥 Streak {flow.streak_days} hari")
                    elif flow.streak_days >= 1:
                        flow_score += 1

                    if abs(flow.net_buy) >= 100_000_000_000:
                        flow_score += 1
                        reasons.append(f"💪 Volume Rp{abs(flow.net_buy):,.0f}")

                    total_score += min(flow_score, 3)
                else:
                    reasons.append("➖ Foreign: netral hari ini")

            except Exception:
                reasons.append("⚠️ Foreign: error")

        # ─── Volume Spike ───────────────────────────────────
        if "volume" in rules:
            available_score += 2
            try:
                if volumes and len(volumes) > 20:
                    avg_vol = sum(volumes[-20:]) / 20
                    latest_vol = volumes[-1] if volumes else 0
                    if avg_vol > 0:
                        ratio = latest_vol / avg_vol
                        if ratio > 2.0:
                            total_score += 2
                            reasons.append(f"🚀 Volume {ratio:.1f}x normal")
                        elif ratio > 1.5:
                            total_score += 1
                            reasons.append(f"📈 Volume {ratio:.1f}x normal")
                        else:
                            reasons.append(f"➖ Volume normal ({ratio:.1f}x)")
                else:
                    reasons.append("➖ Volume: N/A")
            except Exception:
                reasons.append("⚠️ Volume: error")

        # ─── Accumulation ───────────────────────────────────
        if "accumulation" in rules:
            available_score += 2
            try:
                if closes and len(closes) > 5:
                    # Accumulation: price closing near high + up days
                    close_loc = sum(
                        1 for i in range(-5, 0) if i + len(closes) > 0 and highs[i] != lows[i]
                        and (closes[i] - lows[i]) / (highs[i] - lows[i] + 0.01) > 0.6
                    )
                    up_days = sum(
                        1 for i in range(-5, -1) if closes[i] > closes[i - 1]
                    )
                    if close_loc >= 3 and up_days >= 3:
                        total_score += 2
                        reasons.append(f"🐳 Akumulasi terdeteksi ({close_loc}/5 close high)")
                    elif close_loc >= 2:
                        total_score += 1
                        reasons.append(f"📊 Possible akumulasi ({close_loc}/5)")
                    else:
                        reasons.append("➖ No clear accumulation")
                else:
                    reasons.append("➖ Accumulation: N/A")
            except Exception:
                reasons.append("⚠️ Accumulation: error")

        # Normalize
        if available_score > 0:
            normalized = round(total_score / available_score * 10)
        else:
            normalized = 0

        return min(normalized, 10), reasons
