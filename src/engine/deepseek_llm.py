"""DeepSeek LLM provider — V3 (MoE) + R1 (chain-of-thought reasoning).

DeepSeek API is OpenAI-compatible:
  Base: https://api.deepseek.com/v1
  Models: deepseek-chat (V3), deepseek-reasoner (R1)
  R1 returns `reasoning_content` + `content` for chain-of-thought
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

DEEPSEEK_BASE = "https://api.deepseek.com/v1"

# Model mapping
DEEPSEEK_MODELS = {
    "v3": "deepseek-chat",         # Fast general-purpose (MoE 685B)
    "r1": "deepseek-reasoner",     # Chain-of-thought reasoning
}

DEEPSEEK_SYSTEM = (
    "Kamu adalah analis saham profesional yang fokus pada Bursa Efek Indonesia (IDX). "
    "Analisa saham berdasarkan data teknikal, fundamental, aliran dana asing, dan berita. "
    "Beri rekomendasi yang jelas: BUY, HOLD, atau SELL dengan alasan singkat. "
    "Gunakan Bahasa Indonesia. Jawab maksimal 3 paragraf."
)


def _get_key() -> str:
    """Get DeepSeek API key from settings."""
    try:
        from src.config import settings
        return settings.deepseek_api_key or ""
    except Exception:
        return ""


async def chat(
    context: str,
    model: Optional[str] = None,
    system: Optional[str] = None,
    max_tokens: int = 400,
    temperature: float = 0.3,
    timeout: float = 45.0,
) -> Optional[str]:
    """Send a chat completion to DeepSeek.

    Args:
        context: Analysis context (data about the stock)
        model: Model name override (defaults to deepseek-chat / V3)
        system: System prompt override
        max_tokens: Max response tokens
        temperature: Creativity (0-2)
        timeout: Request timeout in seconds

    Returns:
        AI analysis text or None on failure
    """
    try:
        import httpx
    except ImportError:
        logger.warning("httpx not installed — pip install httpx")
        return None

    key = _get_key()
    if not key:
        logger.warning("DeepSeek API key not configured")
        return None

    model = model or DEEPSEEK_MODELS["v3"]
    system_prompt = system or DEEPSEEK_SYSTEM

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Analisa saham berikut:\n\n{context}\n\nBerapa skor saham ini dari 1-10? Apa rekomendasi kamu (BUY/HOLD/SELL)? Beri alasan singkat."},
    ]

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{DEEPSEEK_BASE}/chat/completions",
                headers=headers,
                json=payload,
            )

            if resp.status_code == 200:
                data = resp.json()
                choice = data["choices"][0]
                msg = choice.get("message", {})

                # R1 returns reasoning_content separately
                reasoning = msg.get("reasoning_content", "")
                content = msg.get("content", "").strip()

                if reasoning and content:
                    logger.info(
                        f"DeepSeek R1 OK — reasoning={len(reasoning)} chars, "
                        f"content={len(content)} chars, "
                        f"tokens={data.get('usage', {}).get('total_tokens', '?')}"
                    )
                else:
                    logger.info(
                        f"DeepSeek OK — model={model}, "
                        f"tokens={data.get('usage', {}).get('total_tokens', '?')}"
                    )
                return content

            logger.warning(
                f"DeepSeek returned {resp.status_code}: {resp.text[:200]}"
            )
            return None

    except httpx.TimeoutException:
        logger.warning(f"DeepSeek timeout after {timeout}s")
        return None
    except Exception as e:
        logger.warning(f"DeepSeek error: {e}")
        return None


async def chat_reasoning(
    context: str,
    max_tokens: int = 800,
    timeout: float = 60.0,
) -> Optional[str]:
    """Deep analysis using R1 chain-of-thought reasoning.

    Returns only the final answer (reasoning chain is logged but discarded).
    Use for complex multi-factor analysis.
    """
    system = (
        "Kamu adalah analis saham senior Bursa Efek Indonesia dengan 15 tahun pengalaman. "
        "Lakukan analisa mendalam: evaluasi data teknikal (RSI, MACD, Bollinger, SuperTrend), "
        "fundamental (PER, PBV, ROE), aliran dana asing, dan sentimen berita. "
        "Pertimbangkan interaksi antar faktor. Beri skor 1-10 dan rekomendasi BUY/HOLD/SELL "
        "dengan justifikasi kuat. Gunakan Bahasa Indonesia. Maksimal 4 paragraf."
    )
    return await chat(
        context=context,
        model=DEEPSEEK_MODELS["r1"],
        system=system,
        max_tokens=max_tokens,
        temperature=0.1,
        timeout=timeout,
    )
