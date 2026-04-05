# Sentiment Collection Skill

## Purpose
Gather and analyze community sentiment around Saudi stocks from forums and social media.

## Data Sources
1. **Argaam Forums** — User discussions and comments on stock pages
2. **X/Twitter** — Arabic hashtags: #تاسي, #تداول, #السوق_السعودي, plus stock-specific tags
3. **StockTwits** — If available for Saudi stocks

## Steps
1. Scrape Argaam forum/community pages for stock discussions
2. Scrape X/Twitter for relevant Arabic hashtags (use `httpx`)
3. Collect last 24h / 7d of mentions
4. Use Claude (Haiku) to analyze sentiment of Arabic text
5. Aggregate: bullish %, bearish %, neutral %, top themes
6. Score overall sentiment: -1 (bearish) to +1 (bullish)

## Arabic Sentiment Analysis
- Feed Arabic text directly to Claude — it handles Arabic well
- Key bullish Arabic terms: ارتفاع, صعود, شراء, إيجابي
- Key bearish Arabic terms: انخفاض, هبوط, بيع, سلبي
- Always classify with confidence score

## Rate Limiting
- Argaam forums: max 10 requests/minute
- X/Twitter: aggressive rate limiting — max 5 requests/minute
- Cache sentiment results for 1 hour

## Output Schema
```python
{
    "ticker": "2222",
    "period": "24h",
    "overall_sentiment": 0.3,
    "volume_mentions": 45,
    "bullish_pct": 65, "bearish_pct": 25, "neutral_pct": 10,
    "top_themes": ["dividend", "oil_prices"],
    "source_breakdown": {
        "argaam_forums": {"count": 20, "avg_sentiment": 0.4},
        "twitter": {"count": 25, "avg_sentiment": 0.2}
    }
}
```

## Model Selection
- Sentiment classification: claude-haiku-3.5 (simple classification task)
