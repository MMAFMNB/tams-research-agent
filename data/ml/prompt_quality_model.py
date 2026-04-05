"""
Prompt Quality Prediction Model

Predicts the quality score (1-5) of an analysis section before generating it,
based on features like prompt length, data completeness, model used, and
historical performance.

Uses sklearn GradientBoostingRegressor. Trains when 50+ scored interactions exist.
"""

import json
import logging
import pickle
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

MODEL_FILE = Path(__file__).parent / "models" / "prompt_quality.pkl"
FEATURE_NAMES = [
    "prompt_length", "market_data_completeness", "news_count",
    "has_sentiment", "is_haiku", "is_sonnet",
    "ticker_historical_avg", "learned_rules_count",
    "section_fundamental", "section_technical", "section_earnings",
    "section_dividend", "section_risk", "section_sector",
    "section_news_impact", "section_war_impact",
]

_model = None


def predict_quality(features: Dict) -> float:
    """
    Predict quality score for a prompt configuration.

    Args:
        features: Dict with keys matching FEATURE_NAMES

    Returns:
        Predicted score (1.0 - 5.0), or 3.0 if model not trained.
    """
    model = _load_model()
    if model is None:
        return 3.0  # Default prediction when no model

    try:
        X = _features_to_vector(features)
        prediction = model.predict([X])[0]
        return max(1.0, min(5.0, round(prediction, 2)))
    except Exception as e:
        logger.warning(f"Quality prediction failed: {e}")
        return 3.0


def extract_features(
    section_type: str,
    prompt_length: int,
    market_data_str: str = "",
    news_str: str = "",
    model_used: str = "",
    ticker: str = "",
    learned_rules_count: int = 0,
) -> Dict:
    """Extract feature dict from analysis parameters."""
    # Market data completeness: count how many sections are present
    data_sections = ["CURRENT PRICE", "VALUATION", "DIVIDENDS", "PROFITABILITY",
                     "BALANCE SHEET", "TECHNICAL", "FINANCIAL STATEMENTS"]
    completeness = sum(1 for s in data_sections if s in market_data_str.upper()) / len(data_sections)

    # News count
    news_count = news_str.count("\n- ") if news_str else 0

    # Historical average for this ticker
    ticker_avg = _get_ticker_avg(ticker, section_type)

    features = {
        "prompt_length": prompt_length,
        "market_data_completeness": completeness,
        "news_count": min(news_count, 20),
        "has_sentiment": 1 if "SENTIMENT" in market_data_str.upper() else 0,
        "is_haiku": 1 if "haiku" in model_used.lower() else 0,
        "is_sonnet": 1 if "sonnet" in model_used.lower() else 0,
        "ticker_historical_avg": ticker_avg,
        "learned_rules_count": min(learned_rules_count, 10),
    }

    # One-hot encode section type
    for st in ["fundamental", "technical", "earnings", "dividend",
               "risk", "sector", "news_impact", "war_impact"]:
        features[f"section_{st}"] = 1 if section_type == st else 0

    return features


def train_model() -> bool:
    """
    Train/retrain the quality prediction model from scored interactions.

    Returns True if training succeeded.
    """
    try:
        from sklearn.ensemble import GradientBoostingRegressor
    except ImportError:
        logger.error("scikit-learn not installed — cannot train quality model")
        return False

    # Load training data from prompt_learner
    training_data = _load_training_data()
    if len(training_data) < 50:
        logger.info(f"Need 50+ scored interactions, have {len(training_data)}. Skipping training.")
        return False

    X = []
    y = []

    for entry in training_data:
        features = extract_features(
            section_type=entry.get("section_type", ""),
            prompt_length=entry.get("prompt_chars", 0),
            model_used=entry.get("model", ""),
            ticker=entry.get("ticker", ""),
        )
        X.append(_features_to_vector(features))
        y.append(entry["score"])

    try:
        model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            random_state=42,
        )
        model.fit(X, y)

        # Save model
        MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(MODEL_FILE, "wb") as f:
            pickle.dump(model, f)

        global _model
        _model = model

        logger.info(f"Quality model trained on {len(X)} samples. Score: {model.score(X, y):.3f}")
        return True

    except Exception as e:
        logger.error(f"Model training failed: {e}")
        return False


def get_feature_importance() -> List[Tuple[str, float]]:
    """Get feature importance from the trained model."""
    model = _load_model()
    if model is None:
        return []

    try:
        importances = model.feature_importances_
        pairs = list(zip(FEATURE_NAMES, importances))
        pairs.sort(key=lambda x: x[1], reverse=True)
        return [(name, round(imp, 4)) for name, imp in pairs]
    except Exception:
        return []


def should_retrain() -> bool:
    """Check if the model should be retrained."""
    training_data = _load_training_data()
    count = len(training_data)
    if count < 50:
        return False
    if not MODEL_FILE.exists():
        return True
    # Retrain every 100 new scored interactions
    return count % 100 < 5


# ---- Internal ----

def _features_to_vector(features: Dict) -> List[float]:
    """Convert feature dict to a fixed-length vector."""
    return [float(features.get(name, 0)) for name in FEATURE_NAMES]


def _get_ticker_avg(ticker: str, section_type: str) -> float:
    """Get historical average score for a ticker + section combination."""
    try:
        from data.memory.prompt_learner import _load_learnings
        db = _load_learnings()
        scores = db.get("section_scores", {}).get(section_type, [])
        ticker_scores = [s["score"] for s in scores if s.get("ticker") == ticker]
        return sum(ticker_scores) / len(ticker_scores) if ticker_scores else 3.0
    except Exception:
        return 3.0


def _load_training_data() -> List[Dict]:
    """Load scored interactions from prompt_learner."""
    try:
        from data.memory.prompt_learner import _load_learnings
        db = _load_learnings()
        return [i for i in db.get("interactions", []) if i.get("score") is not None]
    except Exception:
        return []


def _load_model():
    """Load the trained model."""
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
