# Task 25: Build Sentiment Scoring and Trend Database

## Status: PENDING
## Priority: medium
## Dependencies: 12, 14

## Description
Extract sentiment scores from every AI-generated report across 5 categories (overall, management tone, financial health, growth outlook, risk level). Store in ai_sentiment_scores table. Build sentiment trend charts showing score evolution over time per ticker.

## Details
Add sentiment extraction step to report generation pipeline. After Claude generates each section, run a secondary prompt to extract a -1.0 to 1.0 sentiment score per category. Store in Supabase with ticker, report_id, category, score, timestamp. Build Plotly time-series chart: x=date, y=score, color=category. Add to ticker detail view. Build cross-ticker comparison: sentiment comparison across sector peers. Add sentiment alerts: notify when score shifts >0.3 between consecutive reports.

## Test Strategy
1. Test sentiment extraction produces valid scores (-1 to 1)
2. Test all 5 categories scored for a sample report
3. Test scores stored correctly in Supabase
4. Test trend chart displays historical scores
5. Test cross-ticker comparison view
6. Test sentiment alert triggers on significant shift

## Subtasks
No subtasks yet — run task-master expand to generate.
