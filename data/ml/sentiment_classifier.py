"""
Arabic Financial Sentiment Classifier

Uses Claude Haiku for accurate sentiment classification of Arabic/English financial text.
Results are cached to build a training dataset for future local model.

Replaces the keyword-based _score_text() method in SentimentAgent.
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

CACHE_FILE = Path(__file__).parent / "sentiment_cache.json"
TRAINING_FILE = Path(__file__).parent / "sentiment_training.json"

# Batch classification prompt
BATCH_CLASSIFY_PROMPT = """Classify the sentiment of each financial comment below.
For each, return a JSON object with:
- "sentiment": float from -1.0 (very bearish) to 1.0 (very bullish), 0.0 = neutral
- "confidence": float from 0.0 to 1.0
- "topics": list of max 3 topic tags (e.g., "dividend", "earnings", "oil", "growth")

Return ONLY a JSON array of objects, one per comment. No explanation.

Comments:
{comments}"""

SINGLE_CLASSIFY_PROMPT = """Classify this financial text's sentiment.
Return ONLY a JSON object: {{"sentiment": float (-1 to 1), "confidence": float (0 to 1), "topics": ["tag1", "tag2"]}}

Text: {text}"""


def classify_text(text: str, language: str = "auto") -> Dict:
    """
    Classify sentiment of a single text.

    Returns: {"sentiment": float, "confidence": float, "topics": list}
    """
    if not text or len(text.strip()) < 5:
        return {"sentiment": 0.0, "confidence": 0.0, "topics": []}

    # Check cache first
    cached = _get_cached(text)
    if cached is not None:
        return cached

    # Call Claude Haiku
    result = _call_classifier(text)

    if result:
        _cache_result(text, result)
        _store_training_example(text, result, language)

    return result or {"sentiment": 0.0, "confidence": 0.0, "topics": []}


def classify_batch(texts: List[str], language: str = "auto") -> List[Dict]:
    """
    Classify sentiment of multiple texts in a single Claude call.
    Much more cost-efficient than individual calls.

    Max 20 texts per batch.
    """
    if not texts:
        return []

    # Check cache for each
    results = []
    uncached_indices = []
    uncached_texts = []

    for i, text in enumerate(texts):
        cached = _get_cached(text)
        if cached is not None:
            results.append((i, cached))
        else:
            uncached_indices.append(i)
            uncached_texts.append(text)

    # Batch-classify uncached texts
    if uncached_texts:
        batch_results = _call_batch_classifier(uncached_texts[:20])
        for idx, result in zip(uncached_indices, batch_results):
            results.append((idx, result))
            _cache_result(texts[idx], result)
            _store_training_example(texts[idx], result, language)

    # Sort by original index
    results.sort(key=lambda x: x[0])
    return [r[1] for r in results]


def get_training_data_count() -> int:
    """Get the number of labeled training examples collected."""
    if not TRAINING_FILE.exists():
        return 0
    try:
        with open(TRAINING_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return len(data)
    except Exception:
        return 0


def can_train_local_model() -> bool:
    """Check if we have enough data to train a local classifier."""
    return get_training_data_count() >= 500


def export_training_data() -> List[Dict]:
    """Export training data for external model training."""
    if not TRAINING_FILE.exists():
        return []
    try:
        with open(TRAINING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


# ---- Claude Classification ----

def _call_classifier(text: str) -> Optional[Dict]:
    """Classify a single text using Claude Haiku."""
    prompt = SINGLE_CLASSIFY_PROMPT.format(text=text[:1000])
    response = _call_haiku(prompt)
    if not response:
        return None
    return _parse_single_result(response)


def _call_batch_classifier(texts: List[str]) -> List[Dict]:
    """Classify multiple texts in one Claude call."""
    numbered = "\n".join(f"[{i+1}] {t[:300]}" for i, t in enumerate(texts))
    prompt = BATCH_CLASSIFY_PROMPT.format(comments=numbered)
    response = _call_haiku(prompt)
    if not response:
        return [{"sentiment": 0.0, "confidence": 0.0, "topics": []} for _ in texts]

    results = _parse_batch_result(response, len(texts))
    return results


def _call_haiku(prompt: str) -> Optional[str]:
    """Call Claude Haiku for cost-efficient classification."""
    try:
        import anthropic
        from config import ANTHROPIC_API_KEY
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-haiku-3-5-20241022",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except Exception as e:
        logger.warning(f"Haiku classification failed: {e}")
        return None


def _parse_single_result(response: str) -> Optional[Dict]:
    """Parse a single classification response."""
    try:
        # Find JSON in response
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        data = json.loads(response)
        return {
            "sentiment": float(data.get("sentiment", 0)),
            "confidence": float(data.get("confidence", 0.5)),
            "topics": data.get("topics", [])[:3],
        }
    except (json.JSONDecodeError, ValueError, TypeError):
        logger.debug(f"Failed to parse classification: {response[:100]}")
        return None


def _parse_batch_result(response: str, expected_count: int) -> List[Dict]:
    """Parse a batch classification response."""
    default = {"sentiment": 0.0, "confidence": 0.0, "topics": []}
    try:
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        data = json.loads(response)
        if isinstance(data, list):
            results = []
            for item in data:
                results.append({
                    "sentiment": float(item.get("sentiment", 0)),
                    "confidence": float(item.get("confidence", 0.5)),
                    "topics": item.get("topics", [])[:3],
                })
            # Pad if fewer results than expected
            while len(results) < expected_count:
                results.append(default.copy())
            return results[:expected_count]
    except (json.JSONDecodeError, ValueError, TypeError):
        logger.debug(f"Failed to parse batch: {response[:200]}")

    return [default.copy() for _ in range(expected_count)]


# ---- Cache ----

def _get_cached(text: str) -> Optional[Dict]:
    """Look up a cached sentiment result."""
    key = _text_hash(text)
    cache = _load_cache()
    return cache.get(key)


def _cache_result(text: str, result: Dict):
    """Cache a sentiment result."""
    key = _text_hash(text)
    cache = _load_cache()
    cache[key] = result
    # Keep cache under 10,000 entries
    if len(cache) > 10000:
        keys = list(cache.keys())
        for k in keys[:2000]:
            del cache[k]
    _save_cache(cache)


def _text_hash(text: str) -> str:
    """Hash text for cache lookup."""
    return hashlib.md5(text.strip().lower().encode("utf-8")).hexdigest()[:16]


def _load_cache() -> Dict:
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_cache(cache: Dict):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)


# ---- Training Data ----

def _store_training_example(text: str, result: Dict, language: str):
    """Store a classified example for future local model training."""
    if result.get("confidence", 0) < 0.5:
        return  # Don't store low-confidence examples

    data = _load_training_data()
    data.append({
        "text": text[:500],
        "sentiment": result["sentiment"],
        "confidence": result["confidence"],
        "topics": result.get("topics", []),
        "language": language,
        "classified_at": datetime.now().isoformat(),
    })

    # Keep last 10,000 examples
    if len(data) > 10000:
        data = data[-10000:]

    TRAINING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRAINING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def _load_training_data() -> List[Dict]:
    if TRAINING_FILE.exists():
        try:
            with open(TRAINING_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []
