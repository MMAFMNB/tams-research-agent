"""
Predictive Signals System (Task 27)

Experimental AI signals with clear disclaimers. Provides momentum, risk, and earnings signals
using technical indicators and sentiment data. NOT investment advice.

Usage:
    from data.predictive_signals import (
        momentum_signal, risk_signal, earnings_signal, get_all_signals,
        generate_signal_badges_html
    )

    # Get individual signals
    momentum = momentum_signal("2010.SR")
    risk = risk_signal("2010.SR")
    earnings = earnings_signal("2010.SR")

    # Get all signals combined
    all_signals = get_all_signals("2010.SR")

    # Generate HTML badges
    badge_html = generate_signal_badges_html(all_signals)
"""

import logging
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import math

logger = logging.getLogger(__name__)

# TAM Colors
ACCENT = "#1A6DB6"
GREEN = "#22C55E"
RED = "#EF4444"
TEXT = "#E6EDF3"
BG = "#070B14"
ORANGE = "#F59E0B"
GRAY = "#6B7280"

# Disclaimer text
DISCLAIMER = (
    "AI-generated experimental signal. Not investment advice. "
    "TAM Capital is regulated by CMA."
)


def momentum_signal(ticker: str) -> Dict[str, Any]:
    """
    Generate momentum signal based on price and volume trends.

    Composites:
    - Price momentum: 50d MA vs 200d MA
    - Volume trend: 20d avg vs 50d avg
    - RSI signal (70=overbought, 30=oversold)

    Args:
        ticker: Stock ticker

    Returns:
        Dict with signal, confidence (0.0-1.0), factors, and description
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")

        if hist.empty or len(hist) < 200:
            return _neutral_signal("Insufficient data for momentum analysis")

        close = hist["Close"]
        volume = hist["Volume"]

        # Price momentum: 50d MA vs 200d MA
        ma50 = close.rolling(50).mean()
        ma200 = close.rolling(200).mean()
        latest_ma50 = ma50.iloc[-1]
        latest_ma200 = ma200.iloc[-1]

        if latest_ma50 > latest_ma200:
            price_momentum = 0.7  # Bullish
            price_factor = "50d MA above 200d MA"
        else:
            price_momentum = -0.7  # Bearish
            price_factor = "50d MA below 200d MA"

        # Volume trend: 20d avg vs 50d avg
        vol20 = volume.rolling(20).mean()
        vol50 = volume.rolling(50).mean()
        latest_vol20 = vol20.iloc[-1]
        latest_vol50 = vol50.iloc[-1]

        if latest_vol20 > latest_vol50:
            volume_trend = 0.5  # Bullish
            volume_factor = f"Volume increasing ({latest_vol20/latest_vol50:.1f}x)"
        else:
            volume_trend = -0.3  # Slightly bearish
            volume_factor = f"Volume declining ({latest_vol20/latest_vol50:.1f}x)"

        # RSI signal
        rsi = _calculate_rsi(close)
        if rsi > 70:
            rsi_signal = -0.4  # Overbought
            rsi_factor = f"RSI {rsi:.1f} (overbought)"
        elif rsi < 30:
            rsi_signal = 0.4  # Oversold
            rsi_factor = f"RSI {rsi:.1f} (oversold)"
        else:
            rsi_signal = 0.0
            rsi_factor = f"RSI {rsi:.1f} (neutral)"

        # Composite score
        composite = (price_momentum * 0.5 + volume_trend * 0.3 + rsi_signal * 0.2)
        composite = max(-1.0, min(1.0, composite))

        confidence = min(1.0, abs(composite) + 0.2)

        signal_type = "bullish" if composite > 0.3 else "bearish" if composite < -0.3 else "neutral"

        return {
            "signal": signal_type,
            "confidence": round(confidence, 3),
            "factors": [price_factor, volume_factor, rsi_factor],
            "description": f"Momentum: {price_factor}. {volume_factor}. {rsi_factor}.",
            "composite_score": round(composite, 3),
        }

    except Exception as e:
        logger.error(f"Error calculating momentum signal for {ticker}: {e}")
        return _neutral_signal(f"Error: {str(e)}")


def risk_signal(ticker: str) -> Dict[str, Any]:
    """
    Generate risk signal based on volatility, sentiment, and volume anomalies.

    Early warning signals:
    - Volatility spike (30d vs 200d volatility)
    - Sentiment decline (if available from sentiment_tracker)
    - Volume anomaly (unusual spike)

    Args:
        ticker: Stock ticker

    Returns:
        Dict with signal, confidence, factors, and description
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")

        if hist.empty or len(hist) < 30:
            return _neutral_signal("Insufficient data for risk analysis")

        close = hist["Close"]
        volume = hist["Volume"]

        # Volatility analysis
        vol_30d = close.pct_change().rolling(30).std() * 100
        vol_200d = close.pct_change().rolling(200).std() * 100

        latest_vol_30d = vol_30d.iloc[-1]
        latest_vol_200d = vol_200d.iloc[-1]

        if latest_vol_30d and latest_vol_200d > 0:
            volatility_ratio = latest_vol_30d / latest_vol_200d
        else:
            volatility_ratio = 1.0

        if volatility_ratio > 1.5:
            volatility_risk = 0.6  # High risk
            vol_factor = f"Volatility spike ({volatility_ratio:.1f}x)"
        elif volatility_ratio > 1.2:
            volatility_risk = 0.3
            vol_factor = f"Elevated volatility ({volatility_ratio:.1f}x)"
        else:
            volatility_risk = 0.0
            vol_factor = f"Normal volatility ({volatility_ratio:.1f}x)"

        # Volume anomaly
        vol_30d_avg = volume.rolling(30).mean()
        latest_vol = volume.iloc[-1]
        latest_vol_30d_avg = vol_30d_avg.iloc[-1]

        if latest_vol_30d_avg > 0:
            volume_ratio = latest_vol / latest_vol_30d_avg
        else:
            volume_ratio = 1.0

        if volume_ratio > 2.0:
            volume_risk = 0.4  # Anomalous volume
            vol_anom_factor = f"Unusual volume spike ({volume_ratio:.1f}x)"
        else:
            volume_risk = 0.0
            vol_anom_factor = f"Normal volume ({volume_ratio:.1f}x)"

        # Price decline check (simple momentum)
        recent_change = (close.iloc[-1] - close.iloc[-5]) / close.iloc[-5] * 100
        if recent_change < -5:
            momentum_risk = 0.3
            momentum_factor = f"5-day decline ({recent_change:.1f}%)"
        else:
            momentum_risk = 0.0
            momentum_factor = f"Stable price ({recent_change:.1f}%)"

        # Composite risk
        composite_risk = (volatility_risk * 0.5 + volume_risk * 0.3 + momentum_risk * 0.2)
        composite_risk = max(-1.0, min(1.0, composite_risk))

        confidence = min(1.0, abs(composite_risk) + 0.2)

        signal_type = "bearish" if composite_risk > 0.3 else "bullish" if composite_risk < -0.3 else "neutral"

        return {
            "signal": signal_type,
            "confidence": round(confidence, 3),
            "factors": [vol_factor, vol_anom_factor, momentum_factor],
            "description": f"Risk: {vol_factor}. {vol_anom_factor}. {momentum_factor}.",
            "composite_score": round(composite_risk, 3),
        }

    except Exception as e:
        logger.error(f"Error calculating risk signal for {ticker}: {e}")
        return _neutral_signal(f"Error: {str(e)}")


def earnings_signal(ticker: str) -> Dict[str, Any]:
    """
    Generate earnings signal based on historical beat/miss patterns.

    Factors:
    - Historical earnings beats
    - Current sentiment trend
    - Analyst estimate trends (if available)

    Args:
        ticker: Stock ticker

    Returns:
        Dict with signal, confidence, factors, and description
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Get earnings date
        earnings_date = info.get("earningsDate")
        if earnings_date:
            if isinstance(earnings_date, (list, tuple)):
                earnings_date = earnings_date[0]
            if isinstance(earnings_date, str):
                earnings_date = datetime.fromisoformat(earnings_date)

            days_until = (earnings_date - datetime.utcnow()).days
            earnings_factor = f"Earnings in {days_until} days"
        else:
            earnings_factor = "No earnings date available"
            days_until = None

        # Historical earnings performance (simplified)
        # In real scenario, would use actual earnings history
        earnings_history_factor = "No historical data"
        earnings_history_score = 0.0

        # Analyst estimates (if available)
        target_price = info.get("targetMeanPrice", 0)
        current_price = info.get("currentPrice", 0)

        if target_price and current_price and current_price > 0:
            upside = ((target_price - current_price) / current_price) * 100
            analyst_factor = f"Analysts see {upside:+.1f}% upside"
            analyst_score = min(0.5, upside / 20)  # 20% upside = 0.5 score
        else:
            analyst_factor = "No analyst targets available"
            analyst_score = 0.0

        # Revenue growth expectation (if available)
        revenue_growth = info.get("revenueGrowth", 0)
        if revenue_growth:
            growth_factor = f"{revenue_growth*100:+.1f}% revenue growth expected"
            growth_score = min(0.5, revenue_growth / 0.3)  # 30% growth = 0.5 score
        else:
            growth_factor = "No growth expectations"
            growth_score = 0.0

        # Composite earnings signal
        composite = (analyst_score * 0.4 + growth_score * 0.4 + earnings_history_score * 0.2)
        composite = max(-1.0, min(1.0, composite))

        confidence = 0.4 + (abs(analyst_score) * 0.6)  # More confident with analyst data

        signal_type = "bullish" if composite > 0.2 else "bearish" if composite < -0.2 else "neutral"

        factors = [earnings_factor]
        if analyst_factor != "No analyst targets available":
            factors.append(analyst_factor)
        if growth_factor != "No growth expectations":
            factors.append(growth_factor)

        return {
            "signal": signal_type,
            "confidence": round(min(1.0, confidence), 3),
            "factors": factors,
            "description": f"Earnings: {earnings_factor}. {analyst_factor}. {growth_factor}.",
            "composite_score": round(composite, 3),
        }

    except Exception as e:
        logger.error(f"Error calculating earnings signal for {ticker}: {e}")
        return _neutral_signal(f"Error: {str(e)}")


def get_all_signals(ticker: str) -> Dict[str, Dict[str, Any]]:
    """
    Run all signal types and return combined view.

    Args:
        ticker: Stock ticker

    Returns:
        Dict mapping signal type -> signal dict
    """
    return {
        "momentum": momentum_signal(ticker),
        "risk": risk_signal(ticker),
        "earnings": earnings_signal(ticker),
    }


def generate_signal_badges_html(signals: Dict[str, Dict[str, Any]]) -> str:
    """
    Generate HTML badges with glass styling for signals.

    Includes mandatory disclaimer about AI signals.

    Args:
        signals: Dict from get_all_signals()

    Returns:
        HTML string with styled badges and disclaimer
    """
    html = '<div style="display: grid; gap: 16px;">'

    for signal_name, signal_data in signals.items():
        signal_type = signal_data.get("signal", "neutral")
        confidence = signal_data.get("confidence", 0.0)
        factors = signal_data.get("factors", [])

        # Color mapping
        if signal_type == "bullish":
            color = GREEN
            label = "Bullish"
        elif signal_type == "bearish":
            color = RED
            label = "Bearish"
        else:
            color = GRAY
            label = "Neutral"

        # Build factor list
        factors_html = "".join([f"<li style='margin: 4px 0;'>{factor}</li>" for factor in factors])

        html += f"""
        <div style="
            padding: 16px;
            background: rgba(26, 109, 182, 0.08);
            border: 1px solid rgba(26, 109, 182, 0.3);
            border-left: 4px solid {color};
            border-radius: 8px;
            color: {TEXT};
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <h3 style="margin: 0; font-size: 14px; text-transform: capitalize;">{signal_name} Signal</h3>
                <div style="
                    display: flex;
                    align-items: center;
                    gap: 8px;
                ">
                    <span style="color: {color}; font-weight: bold; font-size: 13px;">{label}</span>
                    <div style="
                        width: 60px;
                        height: 6px;
                        background: rgba(255, 255, 255, 0.1);
                        border-radius: 3px;
                        overflow: hidden;
                    ">
                        <div style="
                            width: {confidence * 100}%;
                            height: 100%;
                            background: {color};
                            transition: width 0.3s ease;
                        "></div>
                    </div>
                    <span style="font-size: 12px; color: {GRAY};">{confidence:.0%}</span>
                </div>
            </div>

            <ul style="
                list-style: none;
                padding: 0;
                margin: 0;
                font-size: 12px;
                color: {GRAY};
            ">
                {factors_html}
            </ul>
        </div>
        """

    html += """
    </div>

    <div style="
        padding: 12px;
        margin-top: 16px;
        background: rgba(239, 68, 68, 0.05);
        border: 1px solid rgba(239, 68, 68, 0.2);
        border-radius: 6px;
        font-size: 11px;
        color: {GRAY};
        line-height: 1.5;
    ">
        <strong style="display: block; margin-bottom: 4px;">Disclaimer:</strong>
        """ + DISCLAIMER + """
    </div>
    """

    return html


def _neutral_signal(reason: str = "Insufficient data") -> Dict[str, Any]:
    """Return a neutral signal when analysis cannot be performed."""
    return {
        "signal": "neutral",
        "confidence": 0.0,
        "factors": [reason],
        "description": reason,
        "composite_score": 0.0,
    }


def _calculate_rsi(prices, period: int = 14) -> float:
    """
    Calculate Relative Strength Index (RSI).

    Args:
        prices: Series of closing prices
        period: RSI period (default 14)

    Returns:
        RSI value (0-100)
    """
    try:
        deltas = prices.diff()
        seed = deltas[:period+1]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        rs = up / down if down != 0 else 0
        rsi = 100 - (100 / (1 + rs)) if rs > 0 else 50

        for i in range(period + 1, len(deltas)):
            delta = deltas.iloc[i]
            if delta > 0:
                up = (up * (period - 1) + delta) / period
                down = down * (period - 1) / period
            else:
                up = up * (period - 1) / period
                down = (-delta * 1 + down * (period - 1)) / period

            rs = up / down if down != 0 else 0
            rsi = 100 - (100 / (1 + rs)) if rs > 0 else 50

        return rsi
    except Exception as e:
        logger.debug(f"Error calculating RSI: {e}")
        return 50.0  # Neutral RSI
