"""Test data feed connectivity."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.feed.manager import FeedManager


async def test_feed():
    print("🔍 Testing data feed...")
    try:
        feed = FeedManager()
        print(f"   Feeds available: {len(feed.feeds)}")

        # Test quote
        for symbol in ["TLKM", "BBCA", "BBRI"]:
            quote = await feed.get_quote(symbol)
            if quote:
                print(f"   ✅ {symbol}: Rp{quote.price:,.0f} (vol: {quote.volume:,})")
            else:
                print(f"   ❌ {symbol}: No data")

        # Test klines
        klines = await feed.get_klines("TLKM", "1d", 5)
        if klines:
            print(f"   ✅ TLKM klines: {len(klines)} candles")
            for k in klines[:3]:
                print(f"      {k.timestamp.date()}: O={k.open:.0f} H={k.high:.0f} L={k.low:.0f} C={k.close:.0f} V={k.volume:,}")
        else:
            print(f"   ❌ No klines")

    except Exception as e:
        print(f"   ❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_feed())
