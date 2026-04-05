"""
Investment Signal Learning Model

Learns which fundamental/technical/sentiment signals actually predict
stock returns for Saudi Tadawul stocks. Replaces hardcoded thresholds
in AdvisorAgent._extract_signals().

Uses RandomForestClassifier to predict 30-day return direction:
UP (>5%), FLAT (-5% to +5%), DOWN (<-5%).
"""

import json
import logging
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

MODEL_FILE = Path(__file__).parent / "models" / "signal_model.pkl"
OUTCOMES_FILE = Path(__file__).parent / "signal_outcomes.json"

SIGNAL_FEATURES = [
    "pe_ratio", "pb_ratio", "dividend_yield", "eps",
    "debt_to_equity", "current_ratio", "roe", "roa",
    "profit_margins", "revenue_growth",
    "sentiment_score", "mention_volume", "bullish_pct",
    "news_count", "news_sentiment_avg",
    "price_vs_52w_high",  # current / 52w_high
    "price_change_5d", "price_change_20d",
]

_model = None


def record_signals(ticker: str, signals: Dict, agent_data: Dict):
    """
    Record current signals at time of analysis for later outcome labeling.

    Called by AdvisorAgent after generating a recommendation.
    """
    entry = {
        "ticker": ticker,
        "signals": _extract_signal_features(signals, agent_data),
        "recommendation": signals.get("recommendation", "HOLD"),
        "analysis_date": datetime.now().isoformat(),
        "outcome_date": (datetime.now() + timedelta(days=30)).isoformat(),
        "outcome": None,  # Filled by collect_outcomes()
    }

    outcomes = _load_outcomes()
    outcomes.append(entry)

    # Keep last 2000 entries
    if len(outcomes) > 2000:
        outcomes = outcomes[-2000:]

    _save_outcomes(outcomes)
    logger.info(f"Recorded signals for {ticker} — outcome check on {entry['outcome_date'][:10]}")


def collect_outcomes():
    """
    Retroactively collect price outcomes for past signal records.

    Run weekly via scheduled task. For each unlabeled record where
    outcome_date has passed, fetch the actual price and label the outcome.
    """
    outcomes = _load_outcomes()
    now = datetime.now()
    updated = 0

    for entry in outcomes:
        if entry.get("outcome") is not None:
            continue
        outcome_date = datetime.fromisoformat(entry["outcome_date"])
        if now < outcome_date:
            continue

        # Fetch actual price at outcome date
        ticker = entry["ticker"]
        try:
            import yfinance as yf
            from data.agents.scraper_utils import tadawul_ticker_to_yfinance
            stock = yf.Ticker(tadawul_ticker_to_yfinance(ticker))
            hist = stock.history(
                start=entry["analysis_date"][:10],
                end=entry["outcome_date"][:10],
            )
            if hist.empty or len(hist) < 2:
                continue

            start_price = hist.iloc[0]["Close"]
            end_price = hist.iloc[-1]["Close"]
            pct_change = (end_price - start_price) / start_price * 100

            if pct_change > 5:
                entry["outcome"] = "UP"
            elif pct_change < -5:
                entry["outcome"] = "DOWN"
            else:
                entry["outcome"] = "FLAT"

            entry["actual_return_pct"] = round(pct_change, 2)
            updated += 1

        except Exception as e:
            logger.debug(f"Could not fetch outcome for {ticker}: {e}")

    if updated > 0:
        _save_outcomes(outcomes)
        logger.info(f"Collected {updated} new outcomes")

        # Check if we should retrain
        labeled = [o for o in outcomes if o.get("outcome")]
        if len(labeled) >= 100 and len(labeled) % 50 < 5:
            train_model()


def predict_direction(signals: Dict, agent_data: Dict) -> Dict:
    """
    Predict stock direction from current signals.

    Returns:
        {"direction": "UP"/"FLAT"/"DOWN", "confidence": float, "top_factors": list}
    """
    model = _load_model()
    if model is None:
        return {"direction": "FLAT", "confidence": 0.0, "top_factors": [], "model_available": False}

    features = _extract_signal_features(signals, agent_data)
    X = [_features_to_vector(features)]

    try:
        prediction = model.predict(X)[0]
        probabilities = model.predict_proba(X)[0]
        confidence = max(probabilities)

        # Get top contributing features
        importances = model.feature_importances_
        top_factors = sorted(
            zip(SIGNAL_FEATURES, importances),
            key=lambda x: x[1], reverse=True
        )[:5]

        return {
            "direction": prediction,
            "confidence": round(float(confidence), 3),
            "top_factors": [(name, round(float(imp), 3)) for name, imp in top_factors],
            "model_available": True,
        }
    except Exception as e:
        logger.warning(f"Signal prediction failed: {e}")
        return {"direction": "FLAT", "confidence": 0.0, "top_factors": [], "model_available": False}


def train_model() -> bool:
    """Train the signal prediction model from labeled outcomes."""
    try:
        from sklearn.ensemble import RandomForestClassifier
    except ImportError:
        logger.error("scikit-learn not installed")
        return False

    outcomes = _load_outcomes()
    labeled = [o for o in outcomes if o.get("outcome")]

    if len(labeled) < 100:
        logger.info(f"Need 100+ labeled outcomes, have {len(labeled)}")
        return False

    X = []
    y = []

    for entry in labeled:
        X.append(_features_to_vector(entry["signals"]))
        y.append(entry["outcome"])

    try:
        model = RandomForestClassifier(
            n_estimators=200,
            max_depth=6,
            min_samples_leaf=5,
            random_state=42,
            class_weight="balanced",
        )
        model.fit(X, y)

        MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(MODEL_FILE, "wb") as f:
            pickle.dump(model, f)

        global _model
        _model = model

        accuracy = model.score(X, y)
        logger.info(f"Signal model trained: {len(X)} samples, accuracy: {accuracy:.3f}")
        return True

    except Exception as e:
        logger.error(f"Signal model training failed: {e}")
        return False


def get_model_stats() -> Dict:
    """Get statistics about the signal model."""
    outcomes = _load_outcomes()
    labeled = [o for o in outcomes if o.get("outcome")]
    unlabeled = [o for o in outcomes if o.get("outcome") is None]

    # Outcome distribution
    distribution = {}
    for o in labeled:
        d = o["outcome"]
        distribution[d] = distribution.get(d, 0) + 1

    # Recommendation accuracy
    correct = 0
    total_checked = 0
    for o in labeled:
        rec = o.get("recommendation", "HOLD")
        outcome = o["outcome"]
        if rec in ("BUY", "STRONG BUY") and outcome == "UP":
            correct += 1
        elif rec in ("SELL", "STRONG SELL") and outcome == "DOWN":
            correct += 1
        elif rec == "HOLD" and outcome == "FLAT":
            correct += 1
        total_checked += 1

    return {
        "total_records": len(outcomes),
        "labeled": len(labeled),
        "unlabeled": len(unlabeled),
        "distribution": distribution,
        "recommendation_accuracy": round(correct / total_checked, 3) if total_checked else 0,
        "model_trained": MODEL_FILE.exists(),
    }


# ---- Internal ----

def _extract_signal_features(signals: Dict, agent_data: Dict) -> Dict:
    """Extract numerical features from signals and agent data."""
    sentiment = agent_data.get("sentiment", {}) if isinstance(agent_data.get("sentiment"), dict) else {}

    # Price position vs 52-week high
    price = agent_data.get("close", 0)
    high_52w = agent_data.get("52w_high", 0)
    price_vs_high = price / high_52w if high_52w and high_52w > 0 else 0.5

    return {
        "pe_ratio": _safe_float(agent_data.get("pe_ratio"), 15),
        "pb_ratio": _safe_float(agent_data.get("pb_ratio"), 1.5),
        "dividend_yield": _safe_float(agent_data.get("dividend_yield"), 0.02),
        "eps": _safe_float(agent_data.get("eps"), 1.0),
        "debt_to_equity": _safe_float(agent_data.get("debt_to_equity"), 50),
        "current_ratio": _safe_float(agent_data.get("current_ratio"), 1.5),
        "roe": _safe_float(agent_data.get("roe"), 0.1),
        "roa": _safe_float(agent_data.get("roa"), 0.05),
        "profit_margins": _safe_float(agent_data.get("profit_margins"), 0.1),
        "revenue_growth": 0.0,  # Would need historical data
        "sentiment_score": _safe_float(sentiment.get("overall_sentiment"), 0),
        "mention_volume": _safe_float(sentiment.get("volume_mentions"), 0),
        "bullish_pct": _safe_float(sentiment.get("bullish_pct"), 50),
        "news_count": len(agent_data.get("news_items", [])),
        "news_sentiment_avg": 0.0,  # Would need per-news sentiment
        "price_vs_52w_high": round(price_vs_high, 3),
        "price_change_5d": _safe_float(agent_data.get("change_pct"), 0),
        "price_change_20d": 0.0,
    }


def _safe_float(val, default: float) -> float:
    """Safely convert to float with default."""
    if val is None:
        return default
    try:
        f = float(val)
        if f != f:  # NaN check
            return default
        return f
    except (ValueError, TypeError):
        return default


def _features_to_vector(features: Dict) -> List[float]:
    return [float(features.get(name, 0)) for name in SIGNAL_FEATURES]


def _load_outcomes() -> List[Dict]:
    if OUTCOMES_FILE.exists():
        try:
            with open(OUTCOMES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_outcomes(data: List[Dict]):
    OUTCOMES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTCOMES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, default=str)


def _load_model():
    global _model
    if _model is not None:
        return _model
    if MODEL_FILE.exists():
        try:
            with open(MODEL_FILE, "rb") as f:
                _model = pickle.load(f)
            return _model
        except Exception:
            pass
    return None
