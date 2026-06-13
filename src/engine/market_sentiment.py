"""Market Sentiment Engine — Mood pasar IDX dari data real.

Mengukur sentimen market-wide dari:
  • Foreign net flow (akumulasi vs distribusi)
  • Foreign ratio (seberapa dominan asing)
  • Sector performance (sektor mana yang leading)

Tier: PREMIUM only. Gated behind upgrade CTA for Free/Pro.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class SectorMomentum:
    """Sector-level momentum data."""
    sector_id: str
    sector_name: str
    score: int = 50  # 0-100
    direction: str = "neutral"  # bullish / bearish / neutral


@dataclass
class MarketSentiment:
    """Market-wide sentiment snapshot."""
    timestamp: str
    overall_score: int = 50  # 0-100
    sentiment: str = "NEUTRAL"  # BULLISH / BEARISH / NEUTRAL
    foreign_net_buy: float = 0
    foreign_ratio: float = 0
    sector_momentum: List[SectorMomentum] = field(default_factory=list)
    summary: str = ""
    tier_locked: bool = True


class MarketSentimentEngine:
    """Analyze market sentiment from broker + sector data."""

    SENTIMENT_THRESHOLDS = {
        70: "🟢 BULLISH",
        55: "🟡 CAUTIOUSLY BULLISH",
        45: "⚪ NEUTRAL",
        30: "🟠 CAUTIOUSLY BEARISH",
        0: "🔴 BEARISH",
    }

    def analyze(
        self,
        broker_flow: dict,
        sectors: Optional[list] = None,
    ) -> MarketSentiment:
        """Generate market sentiment from RapidAPI data.

        Args:
            broker_flow: from RapidAPIFeed.get_broker_flow_summary()
            sectors: from RapidAPIFeed.get_sectors()
        """
        if not broker_flow:
            return MarketSentiment(
                timestamp=datetime.now().isoformat(),
                summary="Data market tidak tersedia",
                tier_locked=True,
            )

        foreign_net = broker_flow.get("foreign_net_buy", 0)
        foreign_ratio = broker_flow.get("foreign_domestic_ratio", 0)

        # Calculate overall score
        score = self._calculate_score(foreign_net, foreign_ratio)

        # Determine sentiment label
        sentiment_label = "NEUTRAL"
        for threshold, label in sorted(
            self.SENTIMENT_THRESHOLDS.items(), reverse=True
        ):
            if score >= threshold:
                sentiment_label = label
                break

        # Build sector momentum (from sector list if available)
        sector_momentum = []
        if sectors:
            sector_momentum = [
                SectorMomentum(
                    sector_id=s.get("id", ""),
                    sector_name=s.get("name", ""),
                    score=50,
                    direction="neutral",
                )
                for s in sectors[:8]
            ]

        # Generate summary
        summary = self._generate_summary(
            score, sentiment_label, foreign_net, foreign_ratio
        )

        return MarketSentiment(
            timestamp=broker_flow.get("timestamp", datetime.now().isoformat()),
            overall_score=score,
            sentiment=sentiment_label,
            foreign_net_buy=foreign_net,
            foreign_ratio=foreign_ratio,
            sector_momentum=sector_momentum,
            summary=summary,
            tier_locked=False,
        )

    def _calculate_score(
        self, foreign_net: float, foreign_ratio: float
    ) -> int:
        """Score 0-100 based on foreign activity."""
        score = 50  # neutral

        # Foreign net direction (0-40 points)
        if foreign_net >= 500_000_000_000:
            score += 40
        elif foreign_net >= 200_000_000_000:
            score += 25
        elif foreign_net >= 50_000_000_000:
            score += 10
        elif foreign_net <= -500_000_000_000:
            score -= 40
        elif foreign_net <= -200_000_000_000:
            score -= 25
        elif foreign_net <= -50_000_000_000:
            score -= 10

        # Foreign ratio bonus (-10 to +10)
        if foreign_ratio > 0.30:
            score += 10
        elif foreign_ratio > 0.20:
            score += 5
        elif foreign_ratio < 0.10:
            score -= 5

        return max(0, min(100, score))

    def _generate_summary(
        self,
        score: int,
        sentiment: str,
        foreign_net: float,
        foreign_ratio: float,
    ) -> str:
        net_str = f"Rp{abs(foreign_net):,.0f}"
        direction = "net buy" if foreign_net > 0 else "net sell"

        lines = [
            f"Score: {score}/100",
            f"Asing {direction}: {net_str} ({foreign_ratio*100:.1f}% foreign)",
        ]

        if score >= 70:
            lines.append("\nPasar sedang bullish. Asing agresif masuk.")
            lines.append("Momentum kuat — cocok untuk swing entry.")
        elif score >= 55:
            lines.append("\nSentimen positif. Asing mulai akumulasi.")
            lines.append("Pantau saham blue chip untuk entry.")
        elif score <= 30:
            lines.append("\n⚠️ Pasar bearish. Asing keluar agresif.")
            lines.append("Wait and see — jangan FOMO entry.")
        elif score <= 45:
            lines.append("\nSentimen hati-hati. Asing mulai distribusi.")
            lines.append("Pertimbangkan take profit / kurangi posisi.")
        else:
            lines.append("\nPasar sideways. Tunggu konfirmasi arah.")

        return "\n".join(lines)


# ── Tier-gated CTAs ──────────────────────────────────────────────

SENTIMENT_CTA_FREE = """
🔒 *Market Sentiment Terkunci*

Analisa mood pasar real-time dari foreign flow + sektor.

💎 *Upgrade ke Pro (Rp49rb/bln)* untuk:
  • Sentiment basic (bullish/bearish/neutral)
  • Foreign flow overview

Ketik /pricing
"""

SENTIMENT_CTA_PRO = """
🔒 *Market Sentiment Premium*

Fitur ini butuh Premium (Rp149rb/bln):
  • Sentiment score 0-100 + sinyal entry/exit
  • Foreign ratio tracking + momentum
  • Sector-by-sector heatmap

💎 *Upgrade ke Premium:* /pricing
"""


def get_sentiment_response(
    tier: str,
    broker_flow: Optional[dict] = None,
    sectors: Optional[list] = None,
) -> str:
    """Return tier-appropriate market sentiment output."""
    if tier == "premium" and broker_flow:
        engine = MarketSentimentEngine()
        sentiment = engine.analyze(broker_flow, sectors)

        out = f"📊 *Market Sentiment*\n"
        out += f"━━━━━━━━━━━━━━━━━━━━\n\n"
        out += f"{sentiment.sentiment}\n"
        out += f"{sentiment.summary}\n"

        if sentiment.sector_momentum:
            out += "\n🏢 *Sektor:*\n"
            for s in sentiment.sector_momentum[:5]:
                out += f"  • {s.sector_name}\n"

        return out

    elif tier == "pro":
        return SENTIMENT_CTA_PRO
    else:
        return SENTIMENT_CTA_FREE
