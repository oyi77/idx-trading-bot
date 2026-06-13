"""Bandarmology Engine — Smart Money / Bandar Flow Detection.

Uses RapidAPI IDX broker flow data (89 brokers, foreign/domestic breakdown)
to detect accumulation (net buy) and distribution (net sell) patterns.

Tier: PREMIUM only (Rp149rb/bln). Requires RapidAPI PRO plan ($25/bln).
Locked behind upgrade gate — shows CTA for Free/Pro users.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class BandarSignal:
    """Single bandar activity signal."""
    broker_code: str
    broker_name: str
    net_value: float
    buy_value: float
    sell_value: float
    total_value: float
    group: str  # BROKER_GROUP_FOREIGN / BROKER_GROUP_LOCAL
    direction: str  # "ACCUMULATION" or "DISTRIBUTION"
    strength: str  # "Strong" / "Moderate" / "Weak"


@dataclass
class BandarmologyReport:
    """Full bandarmology analysis report."""
    timestamp: str
    market_foreign_net: float
    market_foreign_ratio: float  # 0-1
    total_market_value: float
    foreign_accumulation_signals: List[BandarSignal] = field(default_factory=list)
    foreign_distribution_signals: List[BandarSignal] = field(default_factory=list)
    local_accumulation_signals: List[BandarSignal] = field(default_factory=list)
    accumulation_score: int = 0  # 0-100
    summary: str = ""
    tier_locked: bool = True  # True = premium gate active


class BandarmologyEngine:
    """Analyze broker flow to detect smart money (bandar) activity.

    Detection logic:
      - Foreign broker net > 500B → Strong accumulation
      - Foreign broker net 100-500B → Moderate accumulation
      - Foreign broker net < -500B → Strong distribution
      - Combined score based on foreign ratio + net direction + top broker count
    """

    # Thresholds (in IDR)
    STRONG_THRESHOLD = 500_000_000_000  # 500B
    MODERATE_THRESHOLD = 100_000_000_000  # 100B

    def __init__(self):
        self._last_report: Optional[BandarmologyReport] = None
        self._history: List[BandarmologyReport] = []

    def analyze(self, broker_flow: dict) -> BandarmologyReport:
        """Generate bandarmology report from RapidAPI broker flow data.

        Args:
            broker_flow: dict from RapidAPIFeed.get_broker_flow_summary()
                         with keys: foreign_net_buy, foreign_buy, foreign_sell,
                         total_value, foreign_domestic_ratio, top_brokers, timestamp
        """
        if not broker_flow:
            return BandarmologyReport(
                timestamp=datetime.now().isoformat(),
                market_foreign_net=0,
                market_foreign_ratio=0,
                total_market_value=0,
                summary="Data broker flow tidak tersedia",
                tier_locked=True,
            )

        # Extract foreign flow
        foreign_net = broker_flow.get("foreign_net_buy", 0)
        foreign_ratio = broker_flow.get("foreign_domestic_ratio", 0)
        total_value = broker_flow.get("total_value", 0)
        top_brokers = broker_flow.get("top_brokers", [])
        all_brokers = broker_flow.get("_all_brokers", top_brokers)  # may be set by caller

        # Classify each broker
        foreign_acc = []
        foreign_dist = []
        local_acc = []

        for b in all_brokers or top_brokers:
            net = float(b.get("net_value", 0))
            buy = float(b.get("buy_value", 0))
            sell = float(b.get("sell_value", 0))
            total = float(b.get("total_value", 0))
            group = b.get("group", "BROKER_GROUP_LOCAL")
            code = b.get("code", "??")
            name = b.get("name", code)

            if abs(net) < self.MODERATE_THRESHOLD:
                continue  # skip noise

            direction = "ACCUMULATION" if net > 0 else "DISTRIBUTION"
            if abs(net) >= self.STRONG_THRESHOLD:
                strength = "Strong"
            else:
                strength = "Moderate"

            signal = BandarSignal(
                broker_code=code,
                broker_name=name,
                net_value=net,
                buy_value=buy,
                sell_value=sell,
                total_value=total,
                group=group,
                direction=direction,
                strength=strength,
            )

            if group == "BROKER_GROUP_FOREIGN":
                if direction == "ACCUMULATION":
                    foreign_acc.append(signal)
                else:
                    foreign_dist.append(signal)
            else:
                if direction == "ACCUMULATION":
                    local_acc.append(signal)

        # Calculate accumulation score (0-100)
        score = self._calculate_score(
            foreign_net, foreign_ratio, foreign_acc, foreign_dist
        )

        # Generate summary
        summary = self._generate_summary(
            foreign_net, foreign_acc, foreign_dist, score
        )

        report = BandarmologyReport(
            timestamp=broker_flow.get("timestamp", datetime.now().isoformat()),
            market_foreign_net=foreign_net,
            market_foreign_ratio=foreign_ratio,
            total_market_value=total_value,
            foreign_accumulation_signals=foreign_acc,
            foreign_distribution_signals=foreign_dist,
            local_accumulation_signals=local_acc,
            accumulation_score=score,
            summary=summary,
            tier_locked=False,  # unlocked — real data
        )

        self._last_report = report
        self._history.append(report)
        return report

    def _calculate_score(
        self,
        foreign_net: float,
        foreign_ratio: float,
        foreign_acc: list,
        foreign_dist: list,
    ) -> int:
        """Score 0-100 based on foreign flow signals."""
        score = 50  # neutral start

        # Foreign net direction (0-30 points)
        if foreign_net >= self.STRONG_THRESHOLD:
            score += 30
        elif foreign_net >= self.MODERATE_THRESHOLD:
            score += 15
        elif foreign_net <= -self.STRONG_THRESHOLD:
            score -= 30
        elif foreign_net <= -self.MODERATE_THRESHOLD:
            score -= 15

        # Foreign ratio bonus (0-15 points)
        if foreign_ratio > 0.30:
            score += 15
        elif foreign_ratio > 0.20:
            score += 8
        elif foreign_ratio < 0.10:
            score -= 8

        # Accumulation vs Distribution count (0-15 points)
        acc_count = len(foreign_acc)
        dist_count = len(foreign_dist)
        if acc_count > dist_count:
            score += min(acc_count * 3, 15)
        elif dist_count > acc_count:
            score -= min(dist_count * 3, 15)

        return max(0, min(100, score))

    def _generate_summary(
        self,
        foreign_net: float,
        foreign_acc: list,
        foreign_dist: list,
        score: int,
    ) -> str:
        """Human-readable summary."""
        net_str = f"Rp{abs(foreign_net):,.0f}"

        if score >= 70:
            direction = "🟢 AKUMULASI KUAT"
            action = "Bandar asing sedang mengakumulasi. Peluang entry bagus."
        elif score >= 55:
            direction = "🟡 AKUMULASI MODERAT"
            action = "Ada akumulasi tapi belum dominan. Pantau dulu."
        elif score <= 30:
            direction = "🔴 DISTRIBUSI KUAT"
            action = "Bandar asing sedang mendistribusi. Hati-hati entry."
        elif score <= 45:
            direction = "🟠 DISTRIBUSI MODERAT"
            action = "Mulai ada distribusi. Pertimbangkan take profit."
        else:
            direction = "⚪ NETRAL"
            action = "Tidak ada sinyal bandar signifikan."

        lines = [
            f"{direction} — Score: {score}/100",
            f"Foreign Net: {net_str}",
            f"Broker Akumulasi: {len(foreign_acc)} | Distribusi: {len(foreign_dist)}",
            f"\n{action}",
        ]
        return "\n".join(lines)

    def get_last_report(self) -> Optional[BandarmologyReport]:
        return self._last_report

    def get_streak(self) -> dict:
        """Get accumulation/distribution streak from history."""
        if len(self._history) < 2:
            return {"direction": "neutral", "days": 0}

        streak = 0
        direction = None
        for report in reversed(self._history):
            if report.accumulation_score >= 55:
                if direction is None:
                    direction = "accumulation"
                if direction == "accumulation":
                    streak += 1
                else:
                    break
            elif report.accumulation_score <= 45:
                if direction is None:
                    direction = "distribution"
                if direction == "distribution":
                    streak -= 1
                else:
                    break
            else:
                break

        return {
            "direction": direction or "neutral",
            "days": abs(streak),
        }


# ── Tier-gated CTA messages ──────────────────────────────────────

BANDARMOLOGY_CTA_FREE = """
🔒 *Bandarmology Terkunci*

Deteksi akumulasi/distribusi bandar asing real-time.
Cocok buat swing trader yang mau ikuti smart money.

💎 *Upgrade ke Pro (Rp49rb/bln)* untuk unlock:
  • Foreign flow per broker
  • Akumulasi score basic
  • Sektor momentum

Ketik /pricing
"""

BANDARMOLOGY_CTA_PRO = """
🔒 *Bandarmology Premium*

Fitur ini butuh Premium (Rp149rb/bln):
  • Deteksi bandar full: akumulasi + distribusi + streak
  • 89 broker real-time + foreign/domestic breakdown
  • Accumulation Score 0-100 + sinyal entry/exit

💎 *Upgrade ke Premium:* /pricing
"""


def get_bandarmology_response(tier: str, broker_flow: Optional[dict] = None) -> str:
    """Return tier-appropriate bandarmology output.

    Args:
        tier: 'free', 'pro', or 'premium'
        broker_flow: RapidAPI broker flow data (for premium users)
    """
    if tier == "premium" and broker_flow:
        engine = BandarmologyEngine()
        report = engine.analyze(broker_flow)

        out = f"🎰 *Bandarmology Report*\n"
        out += f"━━━━━━━━━━━━━━━━━━━━\n\n"
        out += f"{report.summary}\n\n"

        # Top foreign accumulator
        if report.foreign_accumulation_signals:
            out += "🟢 *Foreign Accumulation:*\n"
            for s in report.foreign_accumulation_signals[:3]:
                out += f"  {s.broker_code} {s.broker_name}\n"
                out += f"  Net: Rp{s.net_value:,.0f} ({s.strength})\n"

        # Top foreign distributor
        if report.foreign_distribution_signals:
            out += "\n🔴 *Foreign Distribution:*\n"
            for s in report.foreign_distribution_signals[:3]:
                out += f"  {s.broker_code} {s.broker_name}\n"
                out += f"  Net: Rp{s.net_value:,.0f} ({s.strength})\n"

        return out

    elif tier == "pro":
        return BANDARMOLOGY_CTA_PRO
    else:
        return BANDARMOLOGY_CTA_FREE
