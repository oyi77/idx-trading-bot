#!/usr/bin/env python3
"""Generate weekly market report. Called by cron every Monday 07:00 WIB."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


async def main():
    from src.engine.weekly_report import generate_weekly_report

    report = await generate_weekly_report()
    print(report)


if __name__ == "__main__":
    asyncio.run(main())
