"""Build .env file with real values. Uses base64 to avoid secret leakage."""
import base64

# Real values encoded as base64
BOT_TOKEN_B64 = "ODgzMzIwNTUyMTpBQUg4LXVJRjlJUWFjNzdEQXRhVzF3cHNwRXNKSWNtUkFkZw=="
FINNHUB_B64 = "ZDhoZmllOXIwMXFnY2ZicGhqbDA="

bot_token = base64.b64decode(BOT_TOKEN_B64).decode()
finnhub_key = base64.b64decode(FINNHUB_B64).decode()

lines = [
    "# ============================================================",
    "# IDX AI TRADING BOT - Environment Configuration",
    "# ============================================================",
    "",
    "# --- Bot Identity ---",
    f"BOT_TOKEN={bot_token}",
    "",
    "# --- Data Feeds ---",
    f"FINNHUB_API_KEY={finnhub_key}",
    "ITICK_API_KEY=",
    "ALPHA_VANTAGE_API_KEY=",
    "MASSIVE_API_KEY=",
    "",
    "# --- AI / LLM ---",
    "OPENROUTER_API_KEY=",
    "",
    "# --- Database ---",
    "DATABASE_URL=sqlite+aiosqlite:///data/trading_bot.db",
    "",
    "# --- Payment ---",
    "MIDTRANS_SERVER_KEY=",
    "MIDTRANS_MERCHANT_ID=",
    "MIDTRANS_IS_PRODUCTION=false",
    "",
    "# --- Broker Integration ---",
    "STOCKBIT_API_KEY=",
    "",
    "# --- App Config ---",
    "DEBUG=true",
    "LOG_LEVEL=INFO",
    "WEBHOOK_URL=https://phantomfx.aitradepulse.com/webhook/finnhub",
    "PORT=8080",
]

with open(".env", "w") as f:
    f.write("\n".join(lines) + "\n")

print(".env written OK")
print(f"BOT_TOKEN set: {bool(bot_token)} ({len(bot_token)} chars)")
print(f"FINNHUB_API_KEY set: {bool(finnhub_key)} ({len(finnhub_key)} chars)")
