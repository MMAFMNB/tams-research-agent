"""
Embeddings Store — vector storage for past analyses.

Stores analysis sections as vectors for similarity search.
Uses TF-IDF as default (no model download needed), with optional
sentence-transformers upgrade.
"""

import hashlib
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

STORE_DIR = Path(__file__).parent / "embeddings"
INDEX_FILE = STORE_DIR / "index.json"

# Vectorizer (lazy-loaded)
_vectorizer = None
_vectors = None


def store_analysis(
    ticker: str,
    section_type: str,
    text: str,
    score: Optional[float] = None,
    metadata: Optional[Dict] = None,
):
    """
    Store an analysis section for future retrieval.

    Only stores sections with enough content to be useful.
    """
    if not text or len(text) < 100:
        return

    entry = {
        "id": _make_id(ticker, section_type),
        "ticker": ticker,
        "section_type": section_type,
        "text": text[:5000],  # Limit stored text
        "score": score,
        "metadata": metadata or {},
        "stored_at": datetime.now().isoformat(),
    }

    index = _load_index()

    # Update existing or append
    existing_idx = None
    for i, e in enumerate(index):
        if e["id"] == entry["id"]:
            existing_idx = i
            break

    if existing_idx is not None:
        # Keep the higher-scored version
        if score and (index[existing_idx].get("score") or 0) < score:
            index[existing_idx] = entry
    else:
        index.append(entry)

    # Keep under 5000 entries
    if len(index) > 5000:
        # Remove lowest-scored and oldest entries
        index.sort(key=lambda x: (x.get("score") or 0, x.get("stored_at", "")))
        index = index[-5000:]

    _save_index(index)
    _invalidate_vectorizer()


def find_similar(query_text: str, top_k: int = 5, min_score: float = 0.0) -> List[Dict]:
    """
    Find analyses most similar to the query text.

    Returns list of entries sorted by similarity.
    """
    index = _load_index()
    if not index:
        return []

    # Filter by minimum quality score
    candidates = [e for e in index if (e.get("score") or 0) >= min_score]
    if not candidates:
        candidates = index

    # Compute similarities using TF-IDF
    similarities = _compute_similarities(query_text, candidates)

    # Sort by similarity (descending)
    ranked = sorted(zip(candidates, similarities), key=lambda x: x[1], reverse=True)

    results = []
    for entry, sim in ranked[:top_k]:
        result = entry.copy()
        result["similarity"] = round(sim, 4)
        results.append(result)

    return results


def find_by_ticker(ticker: str, section_type: Optional[str] = None, top_k: int = 5) -> List[Dict]:
    """Find past analyses for a specific ticker."""
    index = _load_index()
    matches = [e for e in index if e["ticker"] == ticker]
    if section_type:
        matches = [e for e in matches if e["section_type"] == section_type]

    # Sort by score (highest first), then by date
    matches.sort(key=lambda x: (x.get("score") or 0, x.get("stored_at", "")), reverse=True)
    return matches[:top_k]


def find_high_quality(section_type: str, min_score: float = 4.0, top_k: int = 3) -> List[Dict]:
    """Find highest-quality past analyses of a given type."""
    index = _load_index()
    matches = [
        e for e in index
        if e["section_type"] == section_type and (e.get("score") or 0) >= min_score
    ]
    matches.sort(key=lambda x: x.get("score", 0), reverse=True)
    return matches[:top_k]


def get_store_stats() -> Dict:
    """Get statistics about the embeddings store."""
    index = _load_index()
    if not index:
        return {"total": 0, "by_section": {}, "by_ticker": {}, "avg_score": 0}

    by_section = {}
    by_ticker = {}
    scores = []

    for e in index:
        st = e.get("section_type", "unknown")
        tk = e.get("ticker", "unknown")
        by_section[st] = by_section.get(st, 0) + 1
        by_ticker[tk] = by_ticker.get(tk, 0) + 1
        if e.get("score"):
            scores.append(e["score"])

    return {
        "total": len(index),
        "by_section": by_section,
        "by_ticker": by_ticker,
        "avg_score": round(sum(scores) / len(scores), 2) if scores else 0,
        "scored_count": len(scores),
    }


# ---- TF-IDF Similarity ----

def _compute_similarities(query: str, candidates: List[Dict]) -> List[float]:
    """Compute cosine similarity between query and candidates using TF-IDF."""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        logger.warning("scikit-learn not installed — using simple overlap similarity")
        return _simple_similarities(query, candidates)

    texts = [query] + [c.get("text", "") for c in candidates]

    try:
        vectorizer = TfidfVectorizer(max_features=5000, stop_words="english")
        tfidf_matrix = vectorizer.fit_transform(texts)
        similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
        return similarities.tolist()
    except Exception as e:
        logger.warning(f"TF-IDF failed: {e}")
        return _simple_similarities(query, candidates)


def _simple_similarities(query: str, candidates: List[Dict]) -> List[float]:
    """Fallback: simple word overlap similarity."""
    query_words = set(re.findall(r'\w+', query.lower()))
    if not query_words:
        return [0.0] * len(candidates)

    sims = []
    for c in candidates:
        text_words = set(re.findall(r'\w+', c.get("text", "").lower()))
        overlap = len(query_words & text_words)
        union = len(query_words | text_words)
        sims.append(overlap / union if union > 0 else 0.0)

    return sims


# ---- Storage ----

def _make_id(ticker: str, section_type: str) -> str:
    date = datetime.now().strftime("%Y%m%d")
    return f"{ticker}_{section_type}_{date}"


def _load_index() -> List[Dict]:
    if INDEX_FILE.exists():
        try:
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_index(index: List[Dict]):
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)


def _invalidate_vectorizer():
    global _vectorizer, _vectors
    _vectorizer = None
    _vectors = None
