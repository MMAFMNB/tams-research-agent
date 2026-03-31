# Task 20: Build Enhanced Alert Dashboard

## Status: PENDING
## Priority: medium
## Dependencies: 19

## Description
Redesign the alert system with a centralized alert feed showing severity badges (info/warning/critical), filtering by ticker/type/severity/date, one-click 'Analyze this' action, mark as read/dismiss/snooze, unread badge count in navigation, and alert history with search.

## Details
New render_alerts() section or enhanced watchlist page. Glass-styled alert cards with severity color coding (info=TAM blue, warning=orange, critical=red). Filter bar at top with multi-select dropdowns. Each alert card has: ticker, type icon, message, timestamp, severity badge, and action buttons (Analyze, Dismiss, Snooze). 'Analyze' pre-loads research chat with alert context. Unread count badge in sidebar nav next to Watchlist. Alert history tab with date range picker and search.

## Test Strategy
1. Test alert display with all severity levels
2. Test filtering by each criterion
3. Test 'Analyze this' opens research with correct context
4. Test mark as read updates count
5. Test snooze hides alert for configured duration
6. Test alert history search returns correct results

## Subtasks
No subtasks yet — run task-master expand to generate.
