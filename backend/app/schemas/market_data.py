"""Market data request/response schemas."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class StockQuoteResponse(BaseModel):
    ticker: str
    name: str
    sector: str
    industry: str
    currency: str
    current_price: float
    market_cap: int
    pe_ratio: float | None = None
    forward_pe: float | None = None
    dividend_yield: float | None = None
    beta: float | None = None
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None
    is_realtime: bool = False
    delay_minutes: int = 15
    fetched_at: datetime


class TickerSearchResult(BaseModel):
    ticker: str
    name: str
    exchange: str
    sector: str | None = None
