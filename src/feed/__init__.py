"""Abstract base for data feed providers."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class Quote:
    symbol: str
    price: float
    open: float
    high: float
    low: float
    volume: int
    value: float  # turnover
    timestamp: datetime


@dataclass
class Kline:
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: datetime
    interval: str  # 1m, 5m, 15m, 30m, 1h, 1d, 1w, 1M


@dataclass
class OrderBookLevel:
    price: float
    volume: float
    side: str  # bid / ask


class DataFeed(ABC):
    """Interface for a stock market data provider."""

    @abstractmethod
    async def get_quote(self, symbol: str) -> Optional[Quote]:
        ...

    @abstractmethod
    async def get_klines(
        self, symbol: str, interval: str, limit: int = 100
    ) -> List[Kline]:
        ...

    @abstractmethod
    async def health(self) -> bool:
        ...
