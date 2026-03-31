# Task 17: Build Admin Panel Page

## Status: PENDING
## Priority: high
## Dependencies: 15, 16

## Description
Create a new Admin page accessible only to admin/super_admin roles. Includes user management (invite, edit role, deactivate), usage dashboard (reports per user, API consumption, top tickers), system configuration (API keys, model selection), and audit log viewer.

## Details
New render_admin() function in app.py. Tabs: Users, Usage, Config, Audit Log. Users tab: table of all users with role dropdown, status toggle, invite button. Usage tab: bar charts of reports/user, line chart of daily API calls, top 10 researched tickers. Config tab: API key management (masked display), default model selector, alert threshold settings. Audit log: filterable table with user, action, timestamp, details. All styled with TAM Liquid Glass theme.

## Test Strategy
1. Test admin can invite new user
2. Test admin can change user roles
3. Test admin can deactivate account
4. Test usage stats display correctly
5. Test non-admin users cannot access this page
6. Test audit log filtering by user, action, date

## Subtasks
No subtasks yet — run task-master expand to generate.
