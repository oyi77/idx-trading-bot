"""
Sector Forecast Engine — predicts 7-day volatility for 11 Indonesian market sectors.

Uses pre-trained NeuralForecast models from Faaris21/forecast-sektor-saham-indonesia.
Models: TFT, NHITS, NBEATSx, LSTM — each trained on specific sector + exogenous features.

All models loaded from data/models/sector_forecast/ (HF Hub snapshot).
"""
import pickle
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
import numpy as np

import pandas as pd
from neuralforecast import NeuralForecast

PROJECT_ROOT = Path(__file__).parent.parent.parent
MODEL_DIR = PROJECT_ROOT / "data" / "models" / "sector_forecast"

# Sector mapping: folder_name → display_name → model_type → exogenous
SECTOR_CONFIG = {
    "Basic_Materials": {
        "name": "Basic Materials",
        "model": "NHITS",
        "exog": "GPR Threat",
        "icon": "🏗️",
    },
    "Consumer_Cyclicals": {
        "name": "Consumer Cyclicals",
        "model": "NBEATSx",
        "exog": "Articles Count",
        "icon": "🛍️",
    },
    "Consumer_Non-Cyclicals": {
        "name": "Consumer Non-Cyclicals",
        "model": "TFT",
        "exog": "GPR Threat",
        "icon": "🧴",
    },
    "Energy": {
        "name": "Energy",
        "model": "LSTM",
        "exog": "GPR Threat",
        "icon": "⚡",
    },
    "Financials": {
        "name": "Financials",
        "model": "TFT",
        "exog": "GPR Threat",
        "icon": "🏦",
    },
    "Industrials": {
        "name": "Industrials",
        "model": "NBEATSx",
        "exog": "Articles Count",
        "icon": "🏭",
    },
    "Infrastuctures": {
        "name": "Infrastructures",
        "model": "TFT",
        "exog": "GPR",
        "icon": "🏗️",
    },
    "Kesehatan": {
        "name": "Healthcare",
        "model": "LSTM",
        "exog": "-",
        "icon": "🏥",
    },
    "Properties_and_Real_Estate": {
        "name": "Property & Real Estate",
        "model": "NHITS",
        "exog": "GPR Threat",
        "icon": "🏘️",
    },
    "Technology": {
        "name": "Technology",
        "model": "TFT",
        "exog": "GPR Action",
        "icon": "💻",
    },
    "Transportation_and_Logistic": {
        "name": "Transportation & Logistic",
        "model": "LSTM",
        "exog": "GPR Action",
        "icon": "🚛",
    },
}

# Model evaluation metrics from README
SECTOR_METRICS = {
    "Basic_Materials": {"MAE": 0.0064, "RMSE": 0.0079, "sMAPE": 15.47},
    "Consumer_Cyclicals": {"MAE": 0.0073, "RMSE": 0.0084, "sMAPE": 25.77},
    "Consumer_Non-Cyclicals": {"MAE": 0.0072, "RMSE": 0.0076, "sMAPE": 35.23},
    "Energy": {"MAE": 0.0022, "RMSE": 0.0028, "sMAPE": 9.36},
    "Financials": {"MAE": 0.0040, "RMSE": 0.0045, "sMAPE": 31.30},
    "Industrials": {"MAE": 0.0018, "RMSE": 0.0023, "sMAPE": 10.38},
    "Infrastuctures": {"MAE": 0.0031, "RMSE": 0.0041, "sMAPE": 19.84},
    "Kesehatan": {"MAE": 0.0025, "RMSE": 0.0031, "sMAPE": 12.65},
    "Properties_and_Real_Estate": {"MAE": 0.0014, "RMSE": 0.0016, "sMAPE": 11.28},
    "Technology": {"MAE": 0.0048, "RMSE": 0.0061, "sMAPE": 21.22},
    "Transportation_and_Logistic": {"MAE": 0.0042, "RMSE": 0.0057, "sMAPE": 14.12},
}

_cache = {}  # Model cache: {sector_key: NeuralForecast}


def _get_model(sector_key: str) -> NeuralForecast:
    """Load (cached) model for a sector."""
    if sector_key in _cache:
        return _cache[sector_key]
    
    model_path = MODEL_DIR / sector_key
    if not model_path.exists():
        available = [d.name for d in MODEL_DIR.iterdir() if d.is_dir() and not d.name.startswith('.')]
        raise FileNotFoundError(
            f"Model for '{sector_key}' not found. Available: {available}"
        )
    
    nf = NeuralForecast.load(path=str(model_path))
    _cache[sector_key] = nf
    return nf


def predict_sector(sector_key: str) -> dict:
    """
    Predict 7-day volatility for a single sector.
    
    Returns:
        {
            "sector": "Technology",
            "sector_name": "Technology",
            "icon": "💻",
            "model_type": "TFT",
            "exog_feature": "GPR Action",
            "metrics": {"MAE": 0.0048, "RMSE": 0.0061, "sMAPE": 21.22},
            "forecast_7d": [0.023, 0.024, ...],  # 7 values
            "current_vol": 0.025,
            "trend": "sideways",  # "rising", "falling", "sideways"
            "avg_forecast": 0.024,
            "min_forecast": 0.023,
            "max_forecast": 0.025,
            "prediction_date": "2026-06-13",
            "horizon_days": 7,
        }
    """
    import pandas as pd
    from datetime import datetime, timedelta
    
    config = SECTOR_CONFIG[sector_key]
    metrics = SECTOR_METRICS[sector_key]
    nf = _get_model(sector_key)
    
    # Load config to get training dates
    cfg_path = MODEL_DIR / sector_key / "configuration.pkl"
    with open(cfg_path, 'rb') as f:
        cfg = pickle.load(f)
    
    # Load historical data
    dspath = MODEL_DIR / sector_key / "dataset.pkl"
    with open(dspath, 'rb') as f:
        ds = pickle.load(f)
    
    temporal = ds.temporal.numpy()
    y = temporal[:, 0]
    x = temporal[:, 1]
    
    model = nf.models[0]
    input_size = getattr(model, 'input_size', 30)
    
    # Use training date range
    train_dates = pd.to_datetime(cfg['ds'])
    last_date = pd.Timestamp(cfg['last_dates'][0])
    
    # Take last input_size values and their dates
    last_y = y[-input_size:]
    last_x = x[-input_size:]
    input_dates = train_dates[-input_size:]
    
    df = pd.DataFrame({
        'unique_id': sector_key,
        'ds': input_dates,
        'y': last_y,
        'x': last_x,
    })
    
    # Generate future dates (7 days after training end)
    futr_df = nf.make_future_dataframe(df)
    
    # Predict
    forecast_df = nf.predict(futr_df=futr_df)
    
    # Extract forecasts
    fc_cols = [c for c in forecast_df.columns if c not in ('unique_id', 'ds')]
    if fc_cols:
        forecasts = forecast_df[fc_cols[0]].values[:7].tolist()
    else:
        forecasts = forecast_df.iloc[0, 2:].values.tolist()[:7]
    
    current = float(last_y[-1])
    avg_fc = float(np.mean(forecasts))
    
    if avg_fc > current * 1.02:
        trend = "rising"
    elif avg_fc < current * 0.98:
        trend = "falling"
    else:
        trend = "sideways"
    
    return {
        "sector": sector_key,
        "sector_name": config["name"],
        "icon": config["icon"],
        "model_type": config["model"],
        "exog_feature": config["exog"],
        "metrics": metrics,
        "forecast_7d": [round(float(f), 6) for f in forecasts],
        "current_vol": round(current, 6),
        "trend": trend,
        "avg_forecast": round(avg_fc, 6),
        "min_forecast": round(float(min(forecasts)), 6),
        "max_forecast": round(float(max(forecasts)), 6),
        "prediction_date": datetime.now().strftime("%Y-%m-%d"),
        "horizon_days": 7,
        "model_last_date": str(last_date.date()),
    }


def predict_all_sectors() -> list[dict]:
    """Predict 7-day volatility for all 11 sectors."""
    results = []
    for sector_key in SECTOR_CONFIG:
        try:
            result = predict_sector(sector_key)
            results.append(result)
        except Exception as e:
            results.append({
                "sector": sector_key,
                "error": str(e),
            })
    
    # Sort: rising first, then falling, then sideways
    priority = {"rising": 0, "sideways": 1, "falling": 2}
    results.sort(key=lambda r: priority.get(r.get("trend", "sideways"), 2))
    
    return results


def format_sector_card(result: dict) -> str:
    """Format single sector prediction into a Telegram-friendly card."""
    if "error" in result:
        return f"⚠️ {result['sector']}: Error — {result['error']}"
    
    icon = result["icon"]
    name = result["sector_name"]
    trend = result["trend"]
    current = result["current_vol"]
    avg_fc = result["avg_forecast"]
    forecasts = result["forecast_7d"]
    
    if trend == "rising":
        emoji = "🔴"  # volatility rising = risk increasing
        trend_text = "Volatility Rising ⚠️"
    elif trend == "falling":
        emoji = "🟢"  # volatility falling = risk decreasing
        trend_text = "Volatility Falling ✅"
    else:
        emoji = "🟡"
        trend_text = "Volatility Stable"
    
    # Format forecast as small bar chart
    max_val = max(max(forecasts), current)
    min_val = min(min(forecasts), current)
    range_val = max(max_val - min_val, 0.0001)
    
    def bar(val):
        width = int((val - min_val) / range_val * 8) + 1
        return "█" * width
    
    fc_bars = " → ".join(bar(f) for f in forecasts)
    
    lines = [
        f"{emoji} {icon} **{name}**",
        f"├ Model: {result['model_type']} | Horizon: 7 Hari",
        f"├ Accuracy: sMAPE {result['metrics']['sMAPE']:.1f}% | MAE {result['metrics']['MAE']:.4f}",
        f"├ Current Vol: {current:.4f} → Avg Forecast: {avg_fc:.4f}",
        f"├ Signal: {trend_text}",
        f"├ 7-Day Forecast: {fc_bars}",
        f"└ Range: {result['min_forecast']:.4f} – {result['max_forecast']:.4f}",
    ]
    
    return "\n".join(lines)


def format_market_outlook(results: list[dict]) -> str:
    """Format all sector forecasts into a market outlook report."""
    lines = [
        "📊 **SECTOR VOLATILITY OUTLOOK — 7 Hari ke Depan**", 
        f"Prediksi: {datetime.now().strftime('%d %b %Y')}",
        "",
    ]
    
    # Count trends
    rising = [r for r in results if r.get("trend") == "rising"]
    falling = [r for r in results if r.get("trend") == "falling"]
    sideways = [r for r in results if r.get("trend") == "sideways"]
    
    lines.append(f"🔴 Rising Risk: {len(rising)} sektor")
    lines.append(f"🟢 Falling Risk: {len(falling)} sektor")
    lines.append(f"🟡 Stable: {len(sideways)} sektor")
    lines.append("")
    
    # If more sectors rising = market caution
    if len(rising) > len(falling):
        lines.append("⚠️ **Overall: Market Caution** — more sectors showing rising volatility")
    elif len(falling) > len(rising):
        lines.append("✅ **Overall: Market Confidence** — more sectors showing declining volatility")
    else:
        lines.append("🟡 **Overall: Mixed** — balanced risk across sectors")
    
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━")
    lines.append("")
    
    for r in results:
        if "error" in r:
            continue
        icon = r["icon"]
        name = r["sector_name"]
        avg_fc = r["avg_forecast"]
        current = r["current_vol"]
        trend = r["trend"]
        
        if trend == "rising":
            arrow = "🔺"
        elif trend == "falling":
            arrow = "🔻"
        else:
            arrow = "➖"
        
        pct_change = ((avg_fc - current) / current * 100) if current != 0 else 0
        change_str = f"+{pct_change:.1f}%" if pct_change > 0 else f"{pct_change:.1f}%"
        
        lines.append(f"{arrow} {icon} {name}: {current:.4f} → {avg_fc:.4f} ({change_str})")
    
    lines.append("")
    lines.append("━" * 30)
    lines.append("🔄 Update: Setiap Senin pagi (Auto-Report)")
    lines.append("💎 *Premium Feature* — AI Sector Forecast")
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Quick test
    print("Testing Sector Forecast Engine\n")
    
    # Test single sector
    result = predict_sector("Technology")
    print(format_sector_card(result))
    print()
    
    # Test all sectors
    print("\n" + "=" * 60)
    all_results = predict_all_sectors()
    print(format_market_outlook(all_results))
