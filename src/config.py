from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Force-load .env before pydantic reads it (handles empty env vars)
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path, override=True)


class Settings(BaseSettings):
    """App configuration loaded from .env"""

    # --- Bot ---
    bot_token: str
    webhook_url: str = ""
    port: int = 8083
    debug: bool = True
    log_level: str = "INFO"

    # --- Data Feeds ---
    itick_api_key: str = ""
    rapidapi_key: str = ""
    finnhub_api_key: str = ""
    alpha_vantage_api_key: str = ""
    massive_api_key: str = ""

    # --- AI / LLM ---
    openrouter_api_key: str = ""
    default_llm_model: str = "openai/gpt-4o-mini"
    omniroute_api_key: str = ""
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"  # fast + capable
    groq_fallback_model: str = "llama-3.1-8b-instant"  # ultra-fast fallback
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"  # V3
    deepseek_reasoner_model: str = "deepseek-reasoner"  # R1

    # --- Database ---
    database_url: str = "sqlite+aiosqlite:///data/trading_bot.db"

    # --- Payment ---
    midtrans_server_key: str = ""
    midtrans_merchant_id: str = ""
    midtrans_is_production: bool = False

    # --- Broker ---
    stockbit_api_key: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
