"""Master API router."""

from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.reports import router as reports_router
from app.api.analysis import router as analysis_router
from app.api.market_data import router as market_data_router
from app.api.exports import router as exports_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(reports_router, prefix="/reports", tags=["reports"])
api_router.include_router(analysis_router, prefix="/analysis", tags=["analysis"])
api_router.include_router(market_data_router, prefix="/market", tags=["market"])
api_router.include_router(exports_router, prefix="/exports", tags=["exports"])
