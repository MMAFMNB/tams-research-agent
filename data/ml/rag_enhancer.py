"""
RAG Enhancer — Retrieval-Augmented Generation for analysis prompts.

Before generating a section, retrieves high-quality similar past analyses
and injects them as reference context into the prompt.
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def get_rag_context(section_type: str, ticker: str, market_data_snippet: str = "") -> str:
    """
    Retrieve past high-quality analyses as context for the current generation.

    Returns a formatted string to append to the prompt, or empty string if
    no relevant past analyses exist.
    """
    try:
        from data.ml.embeddings_store import find_high_quality, find_by_ticker
    except ImportError:
        return ""

    references = []

    # Strategy 1: Find high-quality analyses of the same section type
    high_quality = find_high_quality(section_type, min_score=4.0, top_k=2)
    for entry in high_quality:
        if entry.get("ticker") != ticker:  # Avoid self-reference
            references.append(entry)

    # Strategy 2: Find past analyses of the same ticker
    same_ticker = find_by_ticker(ticker, section_type=section_type, top_k=1)
    for entry in same_ticker:
        if entry not in references:
            references.append(entry)

    # Strategy 3: If we have market data, find similar analyses by content
    if market_data_snippet and len(references) < 2:
        try:
            from data.ml.embeddings_store import find_similar
            similar = find_similar(market_data_snippet[:500], top_k=2, min_score=3.5)
            for entry in similar:
                if entry not in references and entry.get("section_type") == section_type:
                    references.append(entry)
        except Exception:
            pass

    if not references:
        return ""

    # Format as prompt context (max 3 references, max 800 chars each)
    lines = ["\n\nREFERENCE — High-quality past analyses for context (match style and depth):"]
    for i, ref in enumerate(references[:3]):
        score = ref.get("score", "?")
        ticker_ref = ref.get("ticker", "?")
        text = ref.get("text", "")[:800]
        lines.append(f"\n[Ref {i+1}] {ticker_ref} {section_type} (quality score: {score}/5):")
        lines.append(text)

    context = "\n".join(lines)
    logger.info(f"RAG: injecting {len(references)} reference(s) for {section_type} on {ticker}")
    return context


def store_completed_analysis(
    ticker: str,
    section_type: str,
    text: str,
    score: Optional[float] = None,
):
    """
    Store a completed analysis section for future RAG retrieval.

    Called after generate_section() when the section is scored >= 3.0.
    """
    try:
        from data.ml.embeddings_store import store_analysis
        store_analysis(
            ticker=ticker,
            section_type=section_type,
            text=text,
            score=score,
        )
        logger.info(f"Stored analysis for RAG: {ticker}/{section_type} (score: {score})")
    except ImportError:
        pass
