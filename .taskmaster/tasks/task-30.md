# Task 30: Build Audit Trail and Compliance Logging

## Status: PENDING
## Priority: medium
## Dependencies: 12, 15, 17

## Description
Log every significant user action (report generation, exports, logins, admin changes, data modifications) to an append-only audit log in Supabase. Build admin-facing audit log viewer with filtering. Meets CMA regulatory record-keeping requirements.

## Details
Create data/audit_log.py with log_action(user_id, action, resource, details) function. Actions to log: login/logout, report generated, report exported (which format), watchlist modified, portfolio modified, alert rule created/modified, admin actions (user invite, role change, deactivation), system config changes. Audit table: append-only (no UPDATE/DELETE permissions via RLS). Admin viewer: filterable table with columns for timestamp, user, action, resource, details. Export audit log to CSV/Excel for compliance submissions.

## Test Strategy
1. Test all action types are logged
2. Test log entries cannot be modified or deleted
3. Test admin viewer displays correct data
4. Test filtering by user, action, date range
5. Test export to CSV
6. Test high-volume logging doesn't impact performance

## Subtasks
No subtasks yet — run task-master expand to generate.
