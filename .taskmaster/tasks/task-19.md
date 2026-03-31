# Task 19: Build Custom Alert Rules Builder UI

## Status: PENDING
## Priority: high
## Dependencies: 12

## Description
Create an interface for users to define custom alert rules per ticker: price targets (above/below), percentage change thresholds, volume spikes, news keyword triggers, and technical signal triggers (RSI/MACD crossovers). Rules stored in Supabase with active/inactive toggles.

## Details
Add alert rules section to Watchlist page and as a standalone Alert Rules page. UI: glass card per rule with ticker selector, rule type dropdown, parameter inputs (threshold, keywords), notification preference (in-app/email/both), active toggle. CRUD operations via AlertRuleDAO. Background checker scans rules against live data. Link to existing alert_engine.py for alert generation. Show rule status: last triggered, times triggered.

## Test Strategy
1. Test creating each rule type (price, volume, news, technical)
2. Test editing existing rules
3. Test activating/deactivating rules
4. Test rule triggers correctly when condition met
5. Test alert cooldown prevents spam
6. Test rules persist across sessions via Supabase

## Subtasks
No subtasks yet — run task-master expand to generate.
