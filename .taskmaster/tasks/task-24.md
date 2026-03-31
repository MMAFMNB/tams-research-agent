# Task 24: Build User Activity Tracking System

## Status: PENDING
## Priority: medium
## Dependencies: 12, 15

## Description
Implement event tracking that logs every user action (search, analyze, view report, export, add watchlist, view chart, set alert) to the user_activity Supabase table. Build admin-facing usage analytics with heatmaps, top tickers, and feature adoption metrics.

## Details
Create data/activity_tracker.py with track_event(user_id, action_type, ticker, metadata) function. Instrument all key touchpoints in app.py: report generation, export downloads, watchlist modifications, chart views, alert rule creation. Metadata captures: page, duration, parameters used. Admin dashboard widgets: daily active users chart, top 10 tickers bar chart, feature adoption funnel (research → export → share), usage heatmap by hour/day.

## Test Strategy
1. Test events logged for each action type
2. Test event contains correct user_id and metadata
3. Test admin dashboard displays aggregated stats
4. Test filtering by date range and user
5. Test performance impact (logging should be async/non-blocking)
6. Test privacy: users cannot see others' activity

## Subtasks
No subtasks yet — run task-master expand to generate.
