"""AI-powered stock analysis using multi-provider LLM chain.

Provider chain (first success wins):
  1. DeepSeek V3      — best quality (MoE 685B, excellent ID)
  2. OmniRoute        — local gateway (auto/best-fast)
  3. Groq             — ultra-fast LPU (llama-3.3-70b)
  4. Groq (fallback)  — llama-3.1-8b-instant if rate limited
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

OMNIROUTE_BASE = "http://localhost:20128/v1"
OMNIROUTE_MODEL = "auto/best-fast"

DEFAULT_SYSTEM_PROMPT = (
    "Kamu adalah analis saham profesional yang fokus pada Bursa Efek Indonesia (IDX). "
    "Analisa saham berdasarkan data teknikal, fundamental, aliran dana asing, dan berita. "
    "Beri rekomendasi yang jelas: BUY, HOLD, atau SELL dengan alasan singkat. "
    "Gunakan Bahasa Indonesia. Jawab maksimal 3 paragraf."
)

# Learning injection — populated by _build_learning_context
_LEARNING_OVERRIDE: Optional[str] = None


def set_learning_context(context: str) -> None:
    """Override the system prompt with learning context (called from telegram.py)."""
    global _LEARNING_OVERRIDE
    _LEARNING_OVERRIDE = context


def _build_messages(context: str) -> list[dict]:
    """Build messages array with optional learning injection."""
    global _LEARNING_OVERRIDE
    system = DEFAULT_SYSTEM_PROMPT
    if _LEARNING_OVERRIDE:
        system += "\n\n" + _LEARNING_OVERRIDE
        _LEARNING_OVERRIDE = None
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Analisa saham berikut:\n\n{context}\n\nBerapa skor saham ini dari 1-10? Apa rekomendasi kamu (BUY/HOLD/SELL)? Beri alasan singkat."},
    ]


_OMNIROUTE_KEY: Optional[str] = None


def _get_omniroute_key() -> str:
    """Get OmniRoute API key from env or config."""
    global _OMNIROUTE_KEY
    if _OMNIROUTE_KEY:
        return _OMNIROUTE_KEY

    import os

    key = os.getenv("OMNIROUTE_API_KEY", "")
    if key:
        _OMNIROUTE_KEY = key
        return key

    env_path = Path.home() / ".omniroute" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("API_KEY_SECRET="):
                key = line.split("=", 1)[1].strip()
                _OMNIROUTE_KEY = key
                return key

    return ""


async def analyze_with_ai(
    symbol: str,
    price: float,
    change_pct: float,
    technical_data: dict,
    fundamental_data: Optional[dict] = None,
    foreign_flow_data: Optional[dict] = None,
    news_data: Optional[list] = None,
    score: int = 5,
) -> Optional[str]:
    """Generate AI-powered analysis narrative for a stock.

    Provider chain: DeepSeek → OmniRoute → Groq → Groq fallback.
    First provider to return a valid response wins.
    """
    context = _build_analysis_context(
        symbol, price, change_pct, technical_data,
        fundamental_data, foreign_flow_data, news_data, score,
    )

    # ── 1. Try DeepSeek (best quality) ──────────────────
    result = await _try_deepseek(context)
    if result:
        return result

    # ── 2. Try OmniRoute ──────────────────────────────────
    result = await _try_omniroute(context)
    if result:
        return result

    # ── 3. Try Groq ───────────────────────────────────────
    result = await _try_groq(context)
    if result:
        return result

    logger.warning(f"No LLM provider available for {symbol}")
    return None


def _build_analysis_context(
    symbol: str,
    price: float,
    change_pct: float,
    technical_data: dict,
    fundamental_data: Optional[dict],
    foreign_flow_data: Optional[dict],
    news_data: Optional[list],
    score: int,
) -> str:
    """Build analysis context string from all data sources."""
    context_parts = [
        f"Saham: {symbol}",
        f"Harga: Rp{price:,.0f} ({change_pct:+.1f}%)",
    ]

    ind = technical_data.get("indicators", {})
    analysis_body = technical_data.get("analysis", {})

    rsi = ind.get("RSI14", analysis_body.get("rsi"))
    macd = ind.get("MACD", analysis_body.get("macd", {}))
    bb = ind.get("Bollinger", analysis_body.get("bollinger", {}))
    st = ind.get("SuperTrend", analysis_body.get("super_trend", {}))

    if rsi:
        context_parts.append(f"RSI(14): {rsi:.1f}")
    if isinstance(macd, dict) and macd.get("trend"):
        context_parts.append(f"MACD: {macd['trend']}")
    if isinstance(bb, dict) and bb.get("position"):
        context_parts.append(f"Bollinger: {bb['position']}")
    if isinstance(st, dict) and st.get("trend"):
        context_parts.append(f"SuperTrend: {st['trend']}")

    context_parts.append(f"Skor teknikal: {score}/10")

    if fundamental_data:
        per = fundamental_data.get("per", 0)
        pbv = fundamental_data.get("pbv", 0)
        roe = fundamental_data.get("roe", 0)
        if per and per > 0:
            context_parts.append(f"PER: {per:.1f}x, PBV: {pbv:.2f}x, ROE: {roe:.1f}%")

    if foreign_flow_data and foreign_flow_data.get("net_buy", 0) != 0:
        dir_text = "NET BUY" if foreign_flow_data.get("net_buy", 0) > 0 else "NET SELL"
        context_parts.append(f"Foreign Flow: {dir_text} Rp{abs(foreign_flow_data['net_buy']):,.0f}")

    if news_data:
        sentiments = [n.get("sentiment", "neutral") for n in news_data[:3]]
        pos = sum(1 for s in sentiments if s == "positive")
        neg = sum(1 for s in sentiments if s == "negative")
        if pos > neg:
            context_parts.append("Berita: dominan positif")
        elif neg > pos:
            context_parts.append("Berita: dominan negatif")

    return "\n".join(context_parts)


async def _try_omniroute(context: str) -> Optional[str]:
    """Try OmniRoute gateway."""
    try:
        import httpx

        key = _get_omniroute_key()
        if not key:
            logger.debug("OmniRoute: no API key — skipping")
            return None

        payload = {
            "model": OMNIROUTE_MODEL,
            "messages": _build_messages(context),
            "max_tokens": 300,
            "temperature": 0.3,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{OMNIROUTE_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json=payload,
            )
            if resp.status_code != 200:
                logger.warning(f"OmniRoute: {resp.status_code} — falling back")
                return None

            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()

    except ImportError:
        logger.debug("OmniRoute: httpx not installed")
        return None
    except Exception as e:
        logger.warning(f"OmniRoute error: {e} — falling back")
        return None


async def _try_groq(context: str) -> Optional[str]:
    """Try Groq provider."""
    try:
        from src.engine.groq_llm import chat as groq_chat
        return await groq_chat(context=context)
    except ImportError:
        logger.debug("Groq: module not available")
        return None
    except Exception as e:
        logger.warning(f"Groq error: {e}")
        return None


async def _try_deepseek(context: str) -> Optional[str]:
    """Try DeepSeek provider (best quality, excellent Bahasa Indonesia)."""
    try:
        from src.engine.deepseek_llm import chat as ds_chat
        return await ds_chat(context=context)
    except ImportError:
        logger.debug("DeepSeek: module not available")
        return None
    except Exception as e:
        logger.warning(f"DeepSeek error: {e}")
        return None
