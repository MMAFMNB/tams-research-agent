# PRD v5: Machine Learning Features for TAM Research Agent

## Overview

Add genuine machine learning capabilities to replace the rule-based systems currently in place. Four ML features: Arabic sentiment classification, prompt quality prediction, investment signal learning, and embeddings-based analysis retrieval.

## Problem Statement

The current "learning" system uses keyword matching and hardcoded thresholds:
- **Sentiment**: keyword lists (ارتفاع = bullish, هبوط = bearish) — misses sarcasm, context, mixed sentiment
- **Prompt quality**: stores corrections as text rules — no statistical model to predict what works
- **Recommendations**: hardcoded thresholds (PE < 12 = bullish) — doesn't learn from market reality
- **Analysis reuse**: no way to find past similar analyses or learn from them

Additionally, the **memory system has no user identification** — `_is_authed = True` is hardcoded at line 429 of app.py, so all interactions store under `user_id="default"`. This needs to be addressed: either implement lightweight session-based identification (device fingerprint / browser session) or accept single-analyst mode with a configurable analyst profile.

---

## Feature 1: Arabic Financial Sentiment Model

### Goal
Replace keyword-based sentiment scoring with a real NLP model that understands Arabic financial text, sarcasm, mixed sentiment, and context.

### Approach
Use Claude Haiku as the sentiment classification engine with structured output, combined with a local cache of classified examples that improves over time.

**Why not a local model?** A fine-tuned Arabic BERT (like CAMeLBERT or AraBERT) would be ideal but requires GPU, training data, and model hosting. Claude Haiku is cheaper to start with and produces high-quality Arabic sentiment analysis out of the box. Once we have enough labeled data from Claude classifications (1000+ examples), we can train a local model to replace it.

### Implementation

1. **`data/ml/sentiment_classifier.py`** — Sentiment classification engine
   - `classify_text(text, language="ar") -> SentimentResult`
   - Uses Claude Haiku with structured JSON output: `{"sentiment": float, "confidence": float, "reasoning": str, "topics": list}`
   - Batch mode: classify up to 20 comments in a single Claude call (cost efficient)
   - Results cached in `data/ml/sentiment_cache.json` (text hash → result)
   - After 1000+ cached examples: option to train a local sklearn/fasttext classifier

2. **`data/ml/sentiment_training_data.py`** — Training data collector
   - Every Claude classification gets stored as labeled training data
   - Format: `{"text": str, "sentiment": float, "confidence": float, "source": str, "classified_at": str}`
   - Export function for fine-tuning local models later

3. **Integration with SentimentAgent**
   - Replace `_score_text()` keyword method with `classify_text()` 
   - Batch-classify Argaam forum comments and news titles
   - Use Haiku (cost: ~$0.001 per 20 comments classified)

### Success Metrics
- Sentiment accuracy > 85% on manual review (vs ~50% for keyword matching)
- Cost < $0.01 per stock sentiment analysis

---

## Feature 2: Prompt Quality Prediction Model

### Goal
Predict which prompt variations will produce higher-quality analysis before sending to Claude, based on historical analyst scores and corrections.

### Approach
Build a lightweight regression model that predicts quality score (1-5) from prompt features. Use this to select the best prompt variation or add targeted instructions.

### Implementation

1. **`data/ml/prompt_quality_model.py`** — Quality prediction engine
   - Features extracted from each prompt:
     - `section_type` (one-hot encoded)
     - `prompt_length` (chars)
     - `market_data_completeness` (% of data fields present)
     - `news_count` (number of news items included)
     - `has_sentiment_data` (bool)
     - `model_used` (haiku vs sonnet)
     - `ticker_historical_avg_score` (from past analyses of this ticker)
     - `learned_rules_count` (how many rules were injected)
     - `time_of_day` (morning vs afternoon — analysts may score differently)
   - Model: `sklearn.ensemble.GradientBoostingRegressor` (works well with small datasets)
   - Training: triggered when 50+ scored interactions are available
   - Prediction: `predict_quality(features) -> float` (predicted 1-5 score)
   - Retrains automatically every 100 new scored interactions

2. **`data/ml/prompt_optimizer_ml.py`** — ML-enhanced prompt optimization
   - Before each `generate_section()`, predict quality for multiple prompt variations:
     - Full data vs truncated data
     - With vs without learned rules
     - Haiku vs Sonnet
   - Select the variation with highest predicted quality within budget
   - Log actual score for model retraining

3. **Integration with `generate_section()`**
   - After the existing prompt optimization, run quality prediction
   - If predicted quality < 3.0, automatically add more context or switch models
   - Record prediction vs actual score for model improvement

### Training Data Source
- `data/memory/prompt_learnings.json` (already collecting interactions + scores)
- Minimum 50 scored interactions to train first model
- Retrains every 100 new scores

### Success Metrics
- Prediction correlation > 0.6 with actual scores after 200+ training samples
- Average quality improvement of 0.3+ points per section

---

## Feature 3: Investment Signal Learning Model

### Goal
Learn from historical price movements which fundamental/technical/sentiment signals actually predict returns, replacing hardcoded thresholds (PE < 12 = bullish).

### Approach
Build a classification model that learns signal weights from actual stock performance data. Predict next-period return direction (up/down/flat) from current signals.

### Implementation

1. **`data/ml/signal_model.py`** — Signal learning engine
   - **Training data collection**: After each analysis, record:
     - All signals at time of analysis (PE, yield, sentiment, RSI, MA positions, etc.)
     - Actual price change 30 days later (fetched retroactively via cron)
     - Analyst recommendation (BUY/HOLD/SELL)
   - **Features**: ~20 numerical signals normalized to 0-1 range
     - Valuation: PE, PB, EPS growth, dividend yield
     - Technical: RSI, MACD signal, price vs 200MA, 52-week position
     - Sentiment: overall score, mention volume, bullish/bearish ratio
     - Momentum: 5-day change, 20-day change
   - **Model**: `sklearn.ensemble.RandomForestClassifier` 
     - 3 classes: UP (>5%), FLAT (-5% to +5%), DOWN (<-5%)
     - Probabilistic output → confidence score
   - **Training**: requires 100+ samples with outcome labels
   - **Prediction**: `predict_direction(signals) -> {"direction": str, "confidence": float, "top_factors": list}`

2. **`data/ml/outcome_tracker.py`** — Retroactive outcome collection
   - Runs on a schedule (weekly)
   - For each past analysis, fetch the actual price 30 days later
   - Label: UP if > +5%, DOWN if < -5%, FLAT otherwise
   - Store in `data/ml/signal_outcomes.json`

3. **Integration with AdvisorAgent**
   - Replace `_extract_signals()` hardcoded thresholds with model predictions
   - Fall back to rule-based if model not yet trained (< 100 samples)
   - Show model confidence alongside recommendation
   - Display "top factors" that drove the recommendation

### Cold Start Problem
- First 100 analyses: use hardcoded rules (current system)
- After 100: train initial model, blend with rules (50/50 weight)
- After 500: model takes over (90/10 weight)

### Success Metrics
- Directional accuracy > 55% (better than coin flip)
- Feature importance analysis shows which signals matter for Saudi stocks specifically

---

## Feature 4: Embeddings-Based Analysis Retrieval

### Goal
Use vector embeddings to find similar past analyses, enabling "what did we say about Aramco last time?" queries and reusing insights that worked.

### Approach
Embed each completed analysis section, store vectors locally, and use cosine similarity for retrieval. Enables RAG (Retrieval-Augmented Generation) for future analyses.

### Implementation

1. **`data/ml/embeddings_store.py`** — Vector storage engine
   - Generate embeddings using Claude's embeddings API or a local model (sentence-transformers)
   - Store: `{"id": str, "ticker": str, "section_type": str, "text": str, "embedding": list[float], "score": float, "timestamp": str}`
   - Storage: local JSON + numpy arrays in `data/ml/embeddings/`
   - Index: brute-force cosine similarity (fast enough for < 10,000 vectors)
   - For scale: optional FAISS index

2. **`data/ml/retrieval.py`** — Similarity search
   - `find_similar(query_text, top_k=5) -> list[AnalysisResult]`
   - `find_by_ticker(ticker, section_type=None, top_k=5) -> list[AnalysisResult]`
   - `find_high_quality(section_type, min_score=4.0, top_k=3) -> list[AnalysisResult]`
   - Returns past analyses ranked by similarity + quality score

3. **`data/ml/rag_enhancer.py`** — RAG for analysis generation
   - Before generating a section, retrieve top 3 similar past analyses that scored well
   - Inject as "Reference analyses" into the prompt:
     ```
     REFERENCE — Here are high-quality past analyses for similar stocks:
     [1] SABIC fundamental analysis (scored 4.5/5): "SABIC's petrochemical..."
     [2] Aramco fundamental analysis (scored 4.0/5): "Aramco's dominant..."
     ```
   - This teaches Claude the style and depth that analysts approve of
   - Automatically improves quality as the corpus grows

4. **Embedding model selection**
   - Start with: `sentence-transformers/all-MiniLM-L6-v2` (local, free, 384-dim)
   - Upgrade to: Claude embeddings API or Arabic-specific model when needed
   - Fallback: TF-IDF vectors with sklearn (no model download needed)

### Integration Points
- After each `generate_section()` that gets scored ≥ 3.0: embed and store
- Before each `generate_section()`: retrieve similar past analyses as context
- Chat queries like "what did we say about 2222 last time?" use `find_by_ticker()`

### Success Metrics
- Retrieval relevance: > 80% of top-3 results are genuinely similar
- Quality improvement: +0.2 average score after RAG injection
- Query response: < 100ms for similarity search on 5000 vectors

---

## Shared Infrastructure

### `data/ml/` directory structure
```
data/ml/
├── __init__.py
├── sentiment_classifier.py      # Feature 1
├── sentiment_training_data.py   # Feature 1
├── sentiment_cache.json         # Feature 1 (auto-created)
├── prompt_quality_model.py      # Feature 2
├── prompt_optimizer_ml.py       # Feature 2
├── signal_model.py              # Feature 3
├── outcome_tracker.py           # Feature 3
├── signal_outcomes.json         # Feature 3 (auto-created)
├── embeddings_store.py          # Feature 4
├── retrieval.py                 # Feature 4
├── rag_enhancer.py              # Feature 4
├── embeddings/                  # Feature 4 (vector storage)
│   └── .gitkeep
└── models/                      # Trained model artifacts
    └── .gitkeep
```

### New Dependencies
- `scikit-learn>=1.4` — ML models (GBR, RF, TF-IDF)
- `sentence-transformers>=2.7` — Local embeddings (optional, can use TF-IDF fallback)
- `numpy>=1.24` — Already installed

### User Identification Fix
Since auth is currently disabled (`_is_authed = True` hardcoded), implement lightweight session identification:
- Use `st.session_state` to generate a persistent session UUID on first visit
- Store in browser via `st.query_params` or a cookie
- All memory/ML operations use this session ID as `user_id`
- Single-analyst mode: all sessions share the same learning corpus (which is fine for TAM Capital's use case)

---

## Implementation Priority

1. **Feature 1: Sentiment Classifier** (highest immediate impact, replaces weakest current system)
2. **Feature 4: Embeddings + RAG** (improves every analysis once corpus exists)
3. **Feature 2: Prompt Quality Prediction** (needs 50+ scored interactions first)
4. **Feature 3: Signal Learning** (needs 100+ analyses with outcomes — longest data collection)

## Success Criteria

- All 4 models operational with graceful fallback to rule-based when insufficient training data
- Total additional cost < $5/month for ML features (sentiment classification is the main cost)
- Models retrain automatically as data accumulates
- No degradation of existing analysis pipeline if ML features are disabled
