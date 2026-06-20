"""Local IDX Data Feed — Alternative to RapidAPI using yfinance."""
import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Indonesian stock tickers for yfinance
IDX_TICKERS = {
    "BBCA": "BBCA.JK",
    "BBRI": "BBRI.JK",
    "BMRI": "BMRI.JK",
    "TLKM": "TLKM.JK",
    "ASII": "ASII.JK",
    "UNVR": "UNVR.JK",
    "BBNI": "BBNI.JK",
    "ICBP": "ICBP.JK",
    "INDF": "INDF.JK",
    "KLBF": "KLBF.JK",
    "ADRO": "ADRO.JK",
    "PGAS": "PGAS.JK",
    "PTBA": "PTBA.JK",
    "ITMG": "ITMG.JK",
    "MDKA": "MDKA.JK",
    "GOTO": "GOTO.JK",
    "BREN": "BREN.JK",
    "EMTK": "EMTK.JK",
    "BUKA": "BUKA.JK",
    "TOWR": "TOWR.JK",
}

class LocalIDXFeed:
    """Local IDX data feed using yfinance."""
    
    def __init__(self):
        self.cache = {}
        self.last_fetch = {}
    
    async def get_ohlcv(self, symbol: str, timeframe: str = "1d", limit: int = 100) -> Optional[List[Dict]]:
        """Get OHLCV data for a symbol."""
        try:
            import yfinance as yf
            
            ticker = IDX_TICKERS.get(symbol.upper(), f"{symbol}.JK")
            
            # Map timeframe
            tf_map = {"1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1h": "1h", "1d": "1d", "1w": "1wk"}
            yf_tf = tf_map.get(timeframe, "1d")
            
            # Download data
            data = yf.download(ticker, period="1y", interval=yf_tf, progress=False)
            
            if data.empty:
                logger.warning(f"No data for {ticker}")
                return None
            
            # Convert to list of dicts
            ohlcv = []
            for idx, row in data.tail(limit).iterrows():
                ohlcv.append({
                    "timestamp": idx.isoformat(),
                    "open": float(row.get("Open", 0)),
                    "high": float(row.get("High", 0)),
                    "low": float(row.get("Low", 0)),
                    "close": float(row.get("Close", 0)),
                    "volume": float(row.get("Volume", 0)),
                })
            
            return ohlcv
        except Exception as e:
            logger.error(f"Failed to fetch {symbol}: {e}")
            return None
    
    async def get_quote(self, symbol: str) -> Optional[Dict]:
        """Get latest quote for a symbol."""
        try:
            import yfinance as yf
            ticker = IDX_TICKERS.get(symbol.upper(), f"{symbol}.JK")
            data = yf.Ticker(ticker)
            info = data.fast_info
            
            return {
                "symbol": symbol,
                "price": float(info.last_price),
                "change": float(info.last_price - info.previous_close),
                "change_pct": float((info.last_price - info.previous_close) / info.previous_close * 100),
                "volume": int(info.last_volume) if hasattr(info, 'last_volume') else 0,
            }
        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            return None
    
    async def get_stock_list(self) -> List[str]:
        """Get list of available stocks."""
        return list(IDX_TICKERS.keys())


# Singleton instance
local_feed = LocalIDXFeed()
