"""IDX AI Trading Bot — Main Entry Point."""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Ensure src is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import settings

WIB = timezone(timedelta(hours=7))


async def run_autopilot(app):
    """Background autopilot loop — runs daily/weekly tasks.

    Daily (07:00 WIB): market map + signals + follow-up sweep
    Weekly (Sunday 08:00 WIB): backtest + marketing post
    """
    from src.engine.autopilot import (
        post_daily_to_channel, post_weekly_report,
        run_followup_sweep, load_status,
    )

    # Wait 60s after bot start before first run
    await asyncio.sleep(60)
    print("🤖 Autopilot started", flush=True)

    while True:
        try:
            now = datetime.now(WIB)
            hour = now.hour
            minute = now.minute
            weekday = now.weekday()  # 0=Mon, 6=Sun

            # Daily tasks at 07:00 WIB (within 5-min window)
            if hour == 7 and minute < 5:
                print("📋 Running daily autopilot...", flush=True)
                await post_daily_to_channel(app)
                sweep_result = await run_followup_sweep(app)
                print(f"📋 Daily done. Follow-ups sent: {sweep_result}", flush=True)

            # Weekly tasks on Sunday at 08:00 WIB
            if weekday == 6 and hour == 8 and minute < 5:
                print("📊 Running weekly backtest...", flush=True)
                await post_weekly_report(app)
                print("📊 Weekly report posted", flush=True)

            # Sleep 4 minutes (check every 4 min for the 5-min window)
            await asyncio.sleep(240)

        except Exception as e:
            print(f"⚠️ Autopilot error: {e}", flush=True)
            await asyncio.sleep(300)  # Wait 5 min on error


async def run_telegram():
    """Start Telegram bot."""
    from src.bot.telegram import create_app, COMMANDS
    app = create_app()
    await app.initialize()

    # Register bot command list (Telegram menu)
    await app.bot.set_my_commands(COMMANDS)
    print(f"✅ {len(COMMANDS)} commands synced to Telegram", flush=True)

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
    except Exception as e:
        print(f"API server error: {e}", flush=True)


async def main():
    """Entry point — run Telegram bot + API server + autopilot concurrently."""
    # Ensure DB tables exist BEFORE starting API or Telegram bot
    try:
        from src.models import get_engine, Base
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("   DB: ✅ tables ready", flush=True)
        await engine.dispose()
    except Exception as e:
        print(f"   DB: ⚠️ table init failed: {e}", flush=True)

    # Start background screener cache refresh
    try:
        from src.engine.screener_cache import start_background_refresh
        start_background_refresh()
        print("   Cache: ✅ background refresh started", flush=True)
    except Exception as e:
        print(f"   Cache: ⚠️ refresh init failed: {e}", flush=True)

    # Run bot + API + autopilot concurrently
    tasks = [
        asyncio.create_task(run_telegram()),
        asyncio.create_task(run_api()),
    ]

    # Start autopilot after a short delay
    async def _start_autopilot():
        await asyncio.sleep(10)
        try:
            from src.bot.telegram import create_app
            app = create_app()
            await app.initialize()
            await run_autopilot(app)
        except Exception as e:
            print(f"⚠️ Autopilot init failed: {e}", flush=True)

    tasks.append(asyncio.create_task(_start_autopilot()))
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped.", flush=True)
    except Exception as e:
        print(f"Fatal: {e}", flush=True)
        sys.exit(1)
