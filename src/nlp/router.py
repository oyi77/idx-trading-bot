"""NLP router — maps natural language to bot commands and vice versa."""
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class Intent(Enum):
    ANALYZE = "analyze"
    SCREEN = "screen"
    PLAN = "plan"
    ALERT = "alert"
    STATS = "stats"
    CHART = "chart"
    HELP = "help"
    PRICING = "pricing"
    UNKNOWN = "unknown"


@dataclass
class ParsedCommand:
    intent: Intent
    symbol: str = ""
    params: dict = field(default_factory=dict)


class NLPRouter:
    """Map natural language + legacy commands to structured commands.
    
    Handles:
    - Natural: "analisa TLKM", "analisis TLKM", "cek TLKM"
    - Legacy: "/C TLKM i40"
    - Screener: "screener akumulasi asing"
    """

    # ── Analyse aliases ──
    _ANALYZE_PREFIXES = (
        # Multi-word prefixes first (longest match)
        "cek saham", "lihat saham", "analisa saham",
        # Single-word
        "analisa", "analisis", "/analisa", "/analisis",
        "cek", "liat", "lihat", "check",
        "analysis", "/analysis", "analisa kan",
    )

    # ── Screener aliases ──
    _SCREEN_TRIGGERS = ("screener", "screen", "/screener", "/scr", "filter")

    # ── Plan aliases ──
    _PLAN_PREFIXES = ("plan", "/plan", "rencana", "buat plan", "trading plan")

    # ── Alert aliases ──
    _ALERT_TRIGGERS = ("alert", "/alert", "notifikasi", "notif", "pasang alert")

    # ── Stats aliases ──
    _STATS_PREFIXES = ("stats", "/stats", "statistik", "statistic")

    _HELP_TRIGGERS = ("/help", "help", "bantuan", "tolong", "h")
    _PRICING_TRIGGERS = ("/pricing", "pricing", "harga", "subscription",
                         "/subscription", "langganan", "beli", "upgrade",
                         "/subscribe")

    def parse(self, text: str) -> ParsedCommand:
        """Parse incoming message text to structured command."""
        text = text.strip()
        if not text:
            return ParsedCommand(Intent.UNKNOWN)

        lower = text.lower()

        # ── ANALYZE ──
        for prefix in self._ANALYZE_PREFIXES:
            if lower.startswith(prefix):
                # Extract symbol: remove prefix, take first word
                rest = text[len(prefix):].strip()
                parts = rest.split()
                symbol = parts[0].upper() if parts else ""
                logger.info(f"NLPRouter: ANALYZE symbol={symbol} from '{text}'")
                return ParsedCommand(Intent.ANALYZE, symbol, {"depth": "day"})

        # ── SCREEN ──
        for trigger in self._SCREEN_TRIGGERS:
            if trigger in lower:
                rules = self._parse_screener_rules(text)
                logger.info(f"NLPRouter: SCREEN rules={rules} from '{text}'")
                return ParsedCommand(Intent.SCREEN, "", {"rules": rules})

        # ── PLAN ──
        for prefix in self._PLAN_PREFIXES:
            if lower.startswith(prefix):
                result = self._parse_plan(text)
                logger.info(f"NLPRouter: PLAN symbol={result.symbol} from '{text}'")
                return result

        # ── ALERT ──
        for trigger in self._ALERT_TRIGGERS:
            if trigger in lower:
                result = self._parse_alert(text)
                logger.info(f"NLPRouter: ALERT symbol={result.symbol} from '{text}'")
                return result

        # ── STATS ──
        for prefix in self._STATS_PREFIXES:
            if lower.startswith(prefix):
                parts = text.split()
                symbol = parts[1].upper() if len(parts) > 1 else ""
                logger.info(f"NLPRouter: STATS symbol={symbol} from '{text}'")
                return ParsedCommand(Intent.STATS, symbol)

        # ── HELP ──
        if lower in self._HELP_TRIGGERS or lower.split()[0] in self._HELP_TRIGGERS:
            return ParsedCommand(Intent.HELP)

        # ── PRICING ──
        if lower in self._PRICING_TRIGGERS or lower.split()[0] in self._PRICING_TRIGGERS:
            return ParsedCommand(Intent.PRICING)

        # ── Legacy: /C <symbol> <indicators> ──
        if lower.startswith("/c "):
            parts = text.split()
            symbol = parts[1].upper() if len(parts) > 1 else ""
            indicators = parts[2] if len(parts) > 2 else ""
            return ParsedCommand(
                Intent.CHART, symbol, {"indicators": indicators.split(",")}
            )

        # ── Fallback: check if first word looks like a stock symbol ──
        first_word = text.split()[0] if text.split() else ""
        # Match: 3-4 uppercase letters, optionally .JK suffix
        if re.match(r'^[A-Z]{3,4}(\.JK)?$', first_word.upper()):
            # Strip .JK if present
            sym = first_word.upper().replace('.JK', '')
            logger.info(f"NLPRouter: bare symbol → ANALYZE symbol={sym}")
            return ParsedCommand(Intent.ANALYZE, sym, {"depth": "day"})

        logger.info(f"NLPRouter: UNKNOWN from '{text}'")
        return ParsedCommand(Intent.UNKNOWN)

    def _parse_screener_rules(self, text: str) -> list:
        """Parse natural language to screener rules."""
        text_lower = text.lower()
        rules = []

        if "asing" in text_lower or "foreign" in text_lower:
            if "3" in text:
                rules.append("NF3D")
            elif "5" in text:
                rules.append("NF5D")
            elif "10" in text:
                rules.append("NF10D")
            else:
                rules.append("NF3D")

        if "volume" in text_lower or "spike" in text_lower or "ramai" in text_lower:
            rules.append("VOL")

        if "akumulasi" in text_lower or "accumulation" in text_lower:
            rules.append("AC1")

        if "value" in text_lower or " nilai" in text_lower:
            match = re.search(r'(\d+\.?\d*)\s*[mM]', text)
            if match:
                value = float(match.group(1))
                rules.append(f"VAL>{int(value * 1_000_000_000)}")

        if "all" in text_lower or not rules:
            if not rules:
                rules.append("ALL")

        return rules

    def _parse_plan(self, text: str) -> ParsedCommand:
        """Parse trading plan command."""
        parts = text.split()
        symbol = parts[1].upper() if len(parts) > 1 else ""
        params = {}

        entry_match = re.search(r'entry\s+(\d+)', text, re.IGNORECASE)
        sl_match = re.search(r'sl\s+(\d+)', text, re.IGNORECASE)
        tp_match = re.search(r'tp\s+(\d+)', text, re.IGNORECASE)

        if entry_match:
            params["entry"] = int(entry_match.group(1))
        if sl_match:
            params["sl"] = int(sl_match.group(1))
        if tp_match:
            params["tp"] = int(tp_match.group(1))

        return ParsedCommand(Intent.PLAN, symbol, params)

    def _parse_alert(self, text: str) -> ParsedCommand:
        """Parse alert command."""
        parts = text.split()
        symbol = parts[1].upper() if len(parts) > 1 else ""
        params = {}

        condition_match = re.search(r'(>|<|=|>=|<=)\s*(\d+)', text)
        if condition_match:
            params["operator"] = condition_match.group(1)
            params["value"] = float(condition_match.group(2))

        if "naik" in text.lower() or "up" in text.lower():
            params["direction"] = "up"
        elif "turun" in text.lower() or "down" in text.lower():
            params["direction"] = "down"

        return ParsedCommand(Intent.ALERT, symbol, params)
