"""IDX AI Trading Bot — Main Entry Point."""
import asyncio
import sys
from pathlib import Path

# Ensure src is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import settings


async def run_telegram():
    """Start Telegram bot."""
    from src.bot.telegram import create_app
    app = create_app()
    await app.initialize()

    if settings.webhook_url:
        await app.start()
        await app.bot.set_webhook(url=settings.webhook_url)
        print(f"Bot running with webhook: {settings.webhook_url}", flush=True)
        # Keep running
        while True:
            await asyncio.sleep(3600)
    else:
        print("Bot running in polling mode...", flush=True)
        # Hapus webhook lama sebelum polling (biar gak konflik)
        await app.bot.delete_webhook(drop_pending_updates=True)
        await asyncio.sleep(2)  # Tunggu koneksi lama mati
        await app.updater.start_polling(allowed_updates=["message", "callback_query"])
        await app.start()
        # Keep running
        while True:
            await asyncio.sleep(3600)


async def run_api():
    """Run FastAPI web server."""
    try:
        import uvicorn  # noqa: F401
    except ImportError:
        print("⚠️ uvicorn not installed — skipping API server.", flush=True)
        return
    print(f"API server starting on port {settings.port}...", flush=True)
    try:
        config = uvicorn.Config(
            "src.web.app:app",
            host="0.0.0.0",
            port=settings.port,
            reload=False,  # auto-reload conflict dengan polling bot
            log_level=settings.log_level.lower(),
        )
        server = uvicorn.Server(config)
        await server.serve()
    except (SystemExit, OSError) as e:
        print(f"⚠️ API server failed to start on port {settings.port}: {e}", flush=True)
        print("   Bot continues running in polling mode without API server.", flush=True)


async def main():
    """Run both Telegram bot and API server."""
    print(f"🚀 IDX AI Trading Bot v0.1.0", flush=True)
    print(f"   Debug: {settings.debug}", flush=True)
    print(f"   Bot Token: {'✅' if settings.bot_token else '❌'}", flush=True)
    print(f"   iTick Key: {'✅' if settings.itick_api_key else '❌'}", flush=True)
    print(f"   OpenRouter: {'✅' if settings.openrouter_api_key else '❌'}", flush=True)

    await asyncio.gather(
        run_telegram(),
        run_api(),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
