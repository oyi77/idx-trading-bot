"""
IHSG Data Loader — loads IHSG historical data from HuggingFace dataset.
Provides local cache for faster IHSG queries without yfinance API calls.

Source: theonegareth/daily-IHSG (7530 days, 1995-2025)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

LOG = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "ihsg" / "ihsg_daily.csv"

_ihsg_df: Optional[pd.DataFrame] = None


def load_ihsg(force_reload: bool = False) -> pd.DataFrame:
    """
    Load IHSG daily historical data.
    
    Returns DataFrame with columns: Date, Open, High, Low, Close, Volume
    
    Data range: 1995-01-02 to 2025-12-05 (7530 trading days)
    Updated daily on HuggingFace.
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
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    df.sort_index(inplace=True)
    
    _ihsg_df = df
    LOG.info(f"Loaded IHSG data: {len(df)} days ({df.index[0].date()} – {df.index[-1].date()})")
    return df


def get_ihsg_summary() -> dict:
    """Get IHSG market summary statistics."""
    df = load_ihsg()
    
    latest = df.iloc[-1]
    
    # Calculate key metrics
    ytd_start = df.index[df.index >= f"{df.index[-1].year}-01-01"][0]
    ytd_return = (latest['Close'] - df.loc[ytd_start, 'Close']) / df.loc[ytd_start, 'Close'] * 100
    
    # 1-year return
    one_year_ago = df.index[-1] - pd.DateOffset(years=1)
    if one_year_ago in df.index:
        year_return = (latest['Close'] - df.loc[one_year_ago, 'Close']) / df.loc[one_year_ago, 'Close'] * 100
    else:
        # Find closest
        closest = df.index[df.index <= one_year_ago]
        if len(closest) > 0:
            year_return = (latest['Close'] - df.loc[closest[-1], 'Close']) / df.loc[closest[-1], 'Close'] * 100
        else:
            year_return = 0
    
    # All-time high
    ath = df['High'].max()
    ath_date = df[df['High'] == ath].index[0]
    pct_from_ath = (latest['Close'] - ath) / ath * 100
    
    # Avg volume (last 30 days)
    recent = df.tail(30)
    avg_volume = recent['Volume'].mean()
    
    # Volatility (annualized, 30-day)
    returns = recent['Close'].pct_change().dropna()
    volatility = returns.std() * (252 ** 0.5) * 100
    
    return {
        "latest_price": float(latest['Close']),
        "latest_date": str(df.index[-1].date()),
        "ytd_return": round(ytd_return, 2),
        "year_return": round(year_return, 2),
        "ath": float(ath),
        "ath_date": str(ath_date.date()),
        "pct_from_ath": round(pct_from_ath, 2),
        "avg_volume_30d": int(avg_volume),
        "volatility_30d": round(volatility, 2),
        "total_days": len(df),
        "first_date": str(df.index[0].date()),
        "last_date": str(df.index[-1].date()),
    }


def format_ihsg_card(summary: dict) -> str:
    """Format IHSG summary into a Telegram-friendly card."""
    emoji = "🟢" if summary["ytd_return"] > 0 else "🔴"
    ath_emoji = "📈" if summary["pct_from_ath"] < -5 else "⚡"
    
    return (
        f"📊 *IHSG Market Summary*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Harga: *Rp{summary['latest_price']:,.0f}*\n"
        f"Tanggal: {summary['latest_date']}\n\n"
        f"{emoji} YTD Return: *{summary['ytd_return']:+.1f}%*\n"
        f"📅 1-Year Return: {summary['year_return']:+.1f}%\n\n"
        f"{ath_emoji} ATH: Rp{summary['ath']:,.0f} ({summary['ath_date']})\n"
        f"   Dari ATH: {summary['pct_from_ath']:.1f}%\n\n"
        f"📈 Vol 30-hari: {summary['avg_volume_30d']:,}\n"
        f"📊 Volatilitas: {summary['volatility_30d']:.1f}%\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Data: {summary['first_date']} – {summary['last_date']}\n"
        f"({summary['total_days']} hari trading)\n"
        f"💡 `analisa <kode>` untuk detail saham"
    )


if __name__ == "__main__":
    # Quick test
    try:
        summary = get_ihsg_summary()
        print(format_ihsg_card(summary))
    except FileNotFoundError as e:
        print(f"Error: {e}")
