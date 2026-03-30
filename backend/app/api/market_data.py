"""Market data API endpoints."""

from datetime import datetime, timezone
from fastapi import APIRouter

from app.config import get_settings
from app.schemas.market_data import StockQuoteResponse

router = APIRouter()
settings = get_settings()


@router.get("/quote/{ticker}", response_model=StockQuoteResponse)
async def get_quote(ticker: str):
    """Get live stock quote."""
    resolved = settings.resolve_ticker(ticker)

    # Import here to avoid blocking event loop at module load
    from app.data.yahoo_finance import fetch_stock_data
    data = fetch_stock_data(resolved)

    is_saudi = resolved.endswith(".SR")

    return StockQuoteResponse(
        ticker=resolved,
        name=data.get("name", resolved),
        sector=data.get("sector", "N/A"),
        industry=data.get("industry", "N/A"),
        currency=data.get("currency", "SAR" if is_saudi else "USD"),
        current_price=data.get("current_price", 0),
        market_cap=data.get("market_cap", 0),
        pe_ratio=data.get("pe_ratio"),
        forward_pe=data.get("forward_pe"),
        dividend_yield=data.get("dividend_yield"),
        beta=data.get("beta"),
        fifty_two_week_high=data.get("fifty_two_week_high"),
        fifty_two_week_low=data.get("fifty_two_week_low"),
        is_realtime=False,
        delay_minutes=15,
        fetched_at=datetime.now(timezone.utc),
    )


@router.get("/search")
async def search_tickers(q: str):
    """Search for tickers by name or symbol."""
    results = []
    # Check Tadawul tickers
    for code, ticker in settings.TADAWUL_TICKERS.items():
        if q.upper() in code or q.upper() in ticker:
            results.append({"ticker": ticker, "name": f"Tadawul {code}", "exchange": "Saudi Exchange"})

    return results
