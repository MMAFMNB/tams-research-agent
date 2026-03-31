# Task 26: Build Personalized Recommendation Engine

## Status: PENDING
## Priority: medium
## Dependencies: 24, 25

## Description
Create an ML-based recommendation system that learns from user behavior to provide smart suggestions: ticker affinity scoring, contextual prompts ('SABIC earnings in 3 days'), related tickers, and personalized dashboard ordering. Uses collaborative filtering on user_activity data.

## Details
Create ml/recommendation_engine.py. Ticker Affinity Model: weighted score per ticker per user based on research frequency (recency-weighted), watchlist inclusion, portfolio holdings, alert rules, report exports. Smart Suggestions: check upcoming events (earnings dates, dividend dates from yfinance), cross-reference with user's tracked tickers, generate contextual prompts. Related Tickers: cosine similarity between user behavior vectors (collaborative filtering). Dashboard integration: 'Suggested for you' glass card section showing top 3 recommendations with reasoning. Batch update affinity scores nightly.

## Test Strategy
1. Test affinity scoring produces reasonable rankings
2. Test suggestions appear for users with activity history
3. Test related tickers are from same/similar sectors
4. Test suggestions update when user behavior changes
5. Test cold start: new user with no history gets sector-based defaults
6. Test dashboard widget renders suggestions correctly

## Subtasks
No subtasks yet — run task-master expand to generate.
