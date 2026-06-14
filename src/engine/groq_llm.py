"""Groq LLM provider — ultra-fast inference via LPU (OpenAI-compatible API)."""
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

GROQ_BASE = "https://api.groq.com/openai/v1"

# Model tier mapping — fastest first
GROQ_MODELS = {
    "primary": "llama-3.3-70b-versatile",    # Best quality (128k ctx)
    "balanced": "llama-3.1-70b-versatile",   # Fast + good quality
    "fast": "llama-3.1-8b-instant",           # Ultra-fast (cheapest)
}

GROQ_SYSTEM = (
    "Kamu adalah analis saham profesional yang fokus pada Bursa Efek Indonesia (IDX). "
    "Analisa saham berdasarkan data teknikal, fundamental, aliran dana asing, dan berita. "
    "Beri rekomendasi yang jelas: BUY, HOLD, atau SELL dengan alasan singkat. "
    "Gunakan Bahasa Indonesia. Jawab maksimal 3 paragraf."
)


def _get_key() -> str:
    """Get Groq API key from settings."""
    try:
        from src.config import settings
        return settings.groq_api_key or ""
    except Exception:
        return ""


async def chat(
    context: str,
    model: Optional[str] = None,
    system: Optional[str] = None,
    max_tokens: int = 300,
    temperature: float = 0.3,
    timeout: float = 25.0,
) -> Optional[str]:
    """Send a chat completion to Groq.

    Args:
        context: Analysis context (data about the stock)
        model: Model name override (defaults to primary)
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
        logger.warning("Groq API key not configured")
        return None

    model = model or GROQ_MODELS["primary"]
    system_prompt = system or GROQ_SYSTEM

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
                f"{GROQ_BASE}/chat/completions",
                headers=headers,
                json=payload,
            )

            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"].strip()
                logger.info(
                    f"Groq OK — model={model}, tokens={data.get('usage', {}).get('total_tokens', '?')}"
                )
                return content

            # Handle rate limits gracefully
            if resp.status_code == 429:
                logger.warning(f"Groq rate limited ({resp.status_code}) — try faster model")
                # Retry with ultra-fast model if not already using it
                if model != GROQ_MODELS["fast"]:
                    return await chat(
                        context=context,
                        model=GROQ_MODELS["fast"],
                        system=system,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        timeout=timeout,
                    )
                return None

            logger.warning(
                f"Groq returned {resp.status_code}: {resp.text[:200]}"
            )
            return None

    except httpx.TimeoutException:
        logger.warning(f"Groq timeout after {timeout}s")
        return None
    except Exception as e:
        logger.warning(f"Groq error: {e}")
        return None


async def chat_fast(
    context: str,
    max_tokens: int = 250,
    timeout: float = 15.0,
) -> Optional[str]:
    """Quick analysis using the fastest Groq model."""
    return await chat(
        context=context,
        model=GROQ_MODELS["fast"],
        max_tokens=max_tokens,
        temperature=0.2,
        timeout=timeout,
    )


async def list_models() -> list:
    """List available Groq models (for debugging)."""
    try:
        import httpx
        key = _get_key()
        if not key:
            return []
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{GROQ_BASE}/models",
                headers={"Authorization": f"Bearer {key}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                return sorted(
                    [m["id"] for m in data.get("data", []) if m.get("active")],
                    reverse=True,
                )
            return []
    except Exception:
        return []
