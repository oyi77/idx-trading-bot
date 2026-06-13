# IDX AI Trading Bot

**Superior AI-powered trading assistant for Indonesia Stock Exchange (IDX).**

Natural language → Real-time analysis → AI trade setups → Broker execution.

## Features

- ✅ Natural language commands: "analisa TLKM hari ini" or "screener akumulasi asing 3 hari value > 1M"
- ✅ Real-time IDX data via iTick WebSocket + REST
- ✅ Technical screening (RSI, MACD, EMA, Bollinger, SuperTrend, Pixels, Minervini, Turtle, etc.)
- ✅ Fundamental data (PER, PBV, ROE, DER, EPS growth, book value, etc.)
- ✅ Broker flow tracking (top 5 net buy/sell, foreign accumulation N-day streaks)
- ✅ AI trade setup generation with entry zone, SL, TP, risk assessment
- ✅ Multi-platform: Telegram + WhatsApp + Web Dashboard
- ✅ Subscription tiers (Free / Pro / Premium / Lifetime)
- ✅ Broker integration (Stockbit / Ajaib)
- ✅ White-label support for mentor communities

## Quick Start

### Prerequisites

- Python 3.11+
- OpenAI / OpenRouter API key (for AI narrative)
- At least one data feed key (see below)

### Installation

```bash
# Clone & setup
git clone <repo-url> && cd idx-trading-bot
cp .env.example .env
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Configure your keys in .env
# Edit .env with your API keys (see below)

# Run database setup
python scripts/setup_db.py

# Start bot + API
python src/main.py
```

### API Keys Required

| Provider | Purpose | Get at |
|----------|---------|--------|
| iTick | Real-time IDX quotes + WebSocket | https://itick.org |
| OpenRouter | AI / NLP model access | https://openrouter.ai |
| Midtrans | Payment gateway (QRIS, CC) | https://midtrans.com |

**Optional providers:**

| Provider | Purpose | Get at |
|----------|---------|--------|
| Finnhub | Alternative data feed | https://finnhub.io |
| Alpha Vantage | Fundamental data | https://alphavantage.co |
| Stockbit | Broker order execution | https://stockbit.com |

### Configure Keys Securely

```bash
# Edit .env with your keys
nano .env
```

**NEVER commit .env to git. NEVER share keys in chat or files.**

## Architecture

```
User (Telegram/WhatsApp/Web)
    │
    ▼
NLP Router (LLM: intent parsing)
    │
    ├── Feed Handler (iTick REST/WS, Finnhub, AV)
    ├── Analysis Engine (technical, fundamental, flow)
    ├── Trade Setup Generator (AI)
    └── User Services (tiers, payments, alerts)
    │
    ▼
Telegram Bot / Web Dashboard / Broker Order
```

## Commands

### Natural Language (Recommended)
- "analisa TLKM"
- "screener akumulasi asing 3 hari value > 1M"
- "plan TLKM entry 4600 sl 4500 tp 4800"
- "alert TLKM >4600"
- "stats TLKM"

### Legacy Commands (Power Users)
- `/C TLKM i36,i40,o5` — chart with indicators
- `/SCR NF5D` — screener: net foreign 5 days
- `/SCORE PIX7,NF5D,AC1` — combined scoring

## Pricing

| Tier | Price | Key Features |
|------|-------|-------------|
| Free | Rp0 | 5 screens/day, delayed 15m, 5 alerts |
| Pro | Rp49k/mo | Realtime, unlimited alerts, AI setups |
| Premium | Rp149k/mo | Community, weekly mentor, priority AI |
| Lifetime | Rp1.999k | Forever access (1000 seats) |
| White-label | Rp5jt set + Rp500k/mo | Own branding, admin panel |

## Tech Stack

- Python 3.11, FastAPI, python-telegram-bot 21.x
- SQLite (dev) / PostgreSQL (prod)
- Redis (caching + WebSocket pub/sub)
- Docker + docker-compose
- Tailwind CSS (dashboard)

## Legal Disclaimer

Bot ini adalah alat analisis dan edukasi, BUKAN saran investasi. Semua keputusan trading adalah tanggung jawab pengguna. Tidak ada jaminan profit.

## License

MIT
