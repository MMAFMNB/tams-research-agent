# Task 21: Build Morning Brief System

## Status: PENDING
## Priority: high
## Dependencies: 12, 14

## Description
Implement an AI-generated daily digest that scans all user watchlist/portfolio tickers, checks overnight price movements and news, and generates a concise 'Good morning' brief. Delivered as a dashboard widget and optionally via email. Uses APScheduler for scheduling.

## Details
Create prompts/morning_brief.py with a concise, actionable prompt template. Sections: Market Pulse (TASI summary), Watchlist Movers (top 3 up/down), News Highlights (key headlines), Upcoming Events (earnings/dividends in next 7 days), AI Insights (pattern observations). Use APScheduler to run at configurable time (default 7am AST). Store briefs in Supabase (morning_briefs table). Dashboard widget: 'Good morning, [Name]' glass card with expandable brief. Optional email delivery via SendGrid or Supabase Edge Functions.

## Test Strategy
1. Test brief generation for a sample watchlist
2. Test scheduler fires at configured time
3. Test brief content includes all sections
4. Test dashboard widget renders correctly
5. Test brief storage and retrieval from Supabase
6. Test email delivery (if enabled)
7. Test brief for empty watchlist (graceful handling)

## Subtasks
No subtasks yet — run task-master expand to generate.
