# Prompt Learning Skill

## Purpose
ML system that learns from analyst interactions to continuously improve analysis prompts.

## How It Works

### Data Collection
Every time `generate_section()` runs, the system automatically records:
- Section type, ticker, model used
- Prompt and response lengths (for cost tracking)
- Timestamp and user ID

### Analyst Feedback Loop
1. **Scoring**: Analysts rate each section 1-5 after reviewing
   - `record_score(section_type, ticker, score)`
2. **Corrections**: When analysts edit AI output, the diff is captured
   - `record_correction(section_type, ticker, original, corrected, correction_type)`
   - Types: "content" (factual), "format", "tone", "missing", "excess"

### Rule Extraction
The system extracts rules from corrections and scores:
- Factual corrections → "For {section}: prefer X over Y"
- Missing content → "For {section}: include X"
- Excess content → "For {section}: remove X"
- Quality trends → "Quality declining for {section}, pay extra attention"
- Ticker-specific → "For {section} on {ticker}: extra accuracy needed"

### Prompt Injection
Before each Claude call, `get_learned_additions(section_type)` appends relevant rules:
```
IMPORTANT - LEARNED FROM ANALYST FEEDBACK:
- For fundamental: the analyst corrected the peer group for SABIC...
- For fundamental: include oil price context for energy sector stocks
- For fundamental on 2222: extra accuracy needed (avg score 2.5/5)
```

### Model Recommendation
After enough data, the system recommends the best-performing model per section:
- `get_recommended_model(section_type)` returns the model with highest average score

## Key Functions
- `record_interaction()` — auto-called after each generate_section()
- `record_score()` — call from UI feedback widget
- `record_correction()` — call when analyst edits output
- `get_learned_additions()` — auto-called before each prompt
- `get_quality_report()` — admin dashboard metrics
- `get_improvement_suggestions()` — actionable recommendations

## Files
- `data/memory/prompt_learner.py` — Core ML logic
- `data/memory/prompt_learnings.json` — Learning database (auto-created)

## Integration Points
- `app.py:generate_section()` — Records interactions + injects learned rules
- Admin dashboard — Quality report + improvement suggestions
- Sidebar — Could show quality trend indicator
