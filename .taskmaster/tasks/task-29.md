# Task 29: Build Scheduled Report Generation

## Status: PENDING
## Priority: medium
## Dependencies: 14, 21

## Description
Allow users to configure recurring report generation: weekly watchlist refresh, monthly portfolio review, or custom ticker/schedule combinations. Uses APScheduler with Supabase-backed schedule storage. Generated reports are auto-stored and optionally emailed.

## Details
Create services/scheduler.py using APScheduler with Supabase job store. Schedule types: weekly watchlist refresh (regenerate all watched ticker reports), monthly portfolio review (comprehensive portfolio analysis), custom (any ticker, any cron schedule). UI: schedule manager page showing active schedules with next run time, toggle on/off, edit/delete. When triggered: run analysis silently, store report in Supabase, send email notification with PDF attachment (optional). Handle failures gracefully: retry once, then alert user.

## Test Strategy
1. Test creating weekly schedule
2. Test schedule triggers at correct time
3. Test generated report is stored correctly
4. Test email notification sent on completion
5. Test schedule can be paused and resumed
6. Test failure handling and retry logic
7. Test multiple concurrent scheduled jobs

## Subtasks
No subtasks yet — run task-master expand to generate.
