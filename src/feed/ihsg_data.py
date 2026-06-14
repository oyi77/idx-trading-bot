"""
IHSG Data Loader — historical CSV from HuggingFace + live yfinance bridge.
Auto-fetches recent data when stale (>2 days behind).
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

LOG = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "ihsg" / "ihsg_daily.csv"

_ihsg_df: Optional[pd.DataFrame] = None


def _fetch_yahoo(start_date: str) -> pd.DataFrame:
    """Fetch IHSG (^JKSE) daily data from yfinance since start_date."""
    import yfinance as yf

    ticker = yf.Ticker("^JKSE")
    df = ticker.history(start=start_date)
    if df.empty:
        return pd.DataFrame()

    # Strip timezone — yfinance returns tz-aware timestamps
    df = df.reset_index()
    df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
    df = df.rename(columns={
        "Open": "Open", "High": "High",
        "Low": "Low", "Close": "Close", "Volume": "Volume",
    })
    df = df[["Date", "Open", "High", "Low", "Close", "Volume"]]
    df = df.drop_duplicates(subset=["Date"])
    return df


def _update_csv(existing: pd.DataFrame, fresh: pd.DataFrame) -> pd.DataFrame:
    """Merge fresh yfinance data into existing CSV, deduplicating by date."""
    existing_idx = existing.set_index("Date")
    fresh_idx = fresh.set_index("Date")

    # Only add dates newer than our last entry
    last_date = existing_idx.index[-1]
    new_data = fresh_idx[fresh_idx.index > last_date]

    if new_data.empty:
        return existing

    LOG.info(f"Fetched {len(new_data)} new IHSG days ({new_data.index[0]} – {new_data.index[-1]})")
    merged = pd.concat([existing_idx, new_data])
    merged = merged.reset_index()
    merged["Date"] = pd.to_datetime(merged["Date"], utc=False)
    merged = merged.drop_duplicates(subset=["Date"])
    merged = merged.sort_values("Date")

    # Save
    merged.to_csv(DATA_PATH, index=False)
    LOG.info(f"Updated IHSG CSV: {len(merged)} rows")
    return merged


def load_ihsg(force_reload: bool = False) -> pd.DataFrame:
    """
    Load IHSG daily data — auto-fetches from Yahoo Finance when stale.

    Returns DataFrame indexed by Date with columns: Open, High, Low, Close, Volume.
    """
    global _ihsg_df

    if _ihsg_df is not None and not force_reload:
        return _ihsg_df

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"IHSG data not found at {DATA_PATH}. "
            f"Download from: https://huggingface.co/datasets/theonegareth/daily-IHSG"
        )

    df = pd.read_csv(DATA_PATH)

    # Check if data is stale (>2 market days behind)
    last_csv_date = pd.to_datetime(df["Date"].iloc[-1]).date()
    today = date.today()
    # Allow for weekends — stale if last date is more than 3 calendar days ago
    is_stale = (today - last_csv_date).days > 3

    if is_stale:
        try:
            fresh = _fetch_yahoo(start_date=(last_csv_date - timedelta(days=7)).isoformat())
            if not fresh.empty:
                df = _update_csv(df, fresh)
        except Exception as e:
            LOG.warning(f"Yahoo fetch failed, using cached data: {e}")

    df["Date"] = pd.to_datetime(df["Date"], utc=False)
    df.set_index("Date", inplace=True)
    df.sort_index(inplace=True)

    _ihsg_df = df
    LOG.info(f"IHSG data: {len(df)} days ({pd.Timestamp(df.index[0]).date()} – {pd.Timestamp(df.index[-1]).date()})")
    return df


def get_ihsg_summary() -> dict:
    """Get IHSG market summary — always uses latest available data."""
    df = load_ihsg()

    latest = df.iloc[-1]
    latest_date = df.index[-1].date()

    # YTD return
    ytd_start_date = date(latest_date.year, 1, 1)
    ytd_rows = df[df.index >= pd.Timestamp(ytd_start_date)]
    if not ytd_rows.empty:
        ytd_return = (latest["Close"] - ytd_rows.iloc[0]["Close"]) / ytd_rows.iloc[0]["Close"] * 100
    else:
        ytd_return = 0.0

    # 1-year return
    one_year_ago = latest_date - timedelta(days=365)
    year_rows = df[df.index <= pd.Timestamp(one_year_ago)]
    if not year_rows.empty:
        year_price = year_rows.iloc[-1]["Close"]
        year_return = (latest["Close"] - year_price) / year_price * 100
    else:
        year_return = 0.0

    # ATH
    ath = float(df["High"].max())
    ath_idx = df["High"].idxmax()
    ath_date = ath_idx.date() if hasattr(ath_idx, "date") else str(ath_idx)
    pct_from_ath = (latest["Close"] - ath) / ath * 100

    # 30-day stats
    recent = df.tail(30)
    avg_volume = int(recent["Volume"].mean()) if not recent.empty else 0
    returns = recent["Close"].pct_change().dropna()
    volatility = returns.std() * (252 ** 0.5) * 100 if len(returns) > 1 else 0.0

    return {
        "latest_price": float(latest["Close"]),
        "latest_date": str(latest_date),
        "ytd_return": round(ytd_return, 2),
        "year_return": round(year_return, 2),
        "ath": ath,
        "ath_date": str(ath_date),
        "pct_from_ath": round(pct_from_ath, 2),
        "avg_volume_30d": avg_volume,
        "volatility_30d": round(volatility, 2),
        "total_days": len(df),
        "first_date": str(df.index[0].date()),
        "last_date": str(df.index[-1].date()),
    }


def format_ihsg_card(summary: dict) -> str:
    """Format IHSG summary into a Telegram-friendly card."""
    emoji = "🟢" if summary["ytd_return"] > 0 else "🔴"
    ath_emoji = "📈" if summary["pct_from_ath"] < -5 else "⚡"

    card = (
        f"📊 *IHSG Market Summary*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Harga: *{summary['latest_price']:,.0f}*\n"
        f"Tanggal: {summary['latest_date']}\n\n"
        f"{emoji} YTD Return: *{summary['ytd_return']:+.1f}%*\n"
        f"📅 1-Year Return: {summary['year_return']:+.1f}%\n\n"
        f"{ath_emoji} ATH: {summary['ath']:,.0f} ({summary['ath_date']})\n"
        f"   Dari ATH: {summary['pct_from_ath']:.1f}%\n\n"
        f"📈 Vol 30-hari: {summary['avg_volume_30d']:,}\n"
        f"📊 Volatilitas: {summary['volatility_30d']:.1f}%\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Data: {summary['first_date']} – {summary['last_date']}\n"
        f"({summary['total_days']} hari trading)\n"
        f"💡 `analisa <kode>` untuk detail saham"
    )
    return card


if __name__ == "__main__":
    try:
        summary = get_ihsg_summary()
        print(format_ihsg_card(summary))
    except FileNotFoundError as e:
        print(f"Error: {e}")
