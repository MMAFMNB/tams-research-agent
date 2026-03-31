# Task 16: Implement Role-Based Access Control (RBAC)

## Status: PENDING
## Priority: high
## Dependencies: 15

## Description
Build RBAC middleware that enforces permissions based on user role (super_admin, admin, analyst, viewer). Gate features, pages, and actions based on role. Viewer gets read-only access, analyst gets full research capabilities, admin adds user management.

## Details
Create auth/rbac.py module with role checking decorators/functions. Define permission matrix: super_admin (all), admin (user mgmt + analyst features), analyst (research + portfolio + watchlist + alerts + export), viewer (read-only dashboards + published reports). Apply role checks in app.py before rendering each page. Show/hide UI elements based on role. Enforce at DAL level too (belt and suspenders).

## Test Strategy
1. Test each role can access permitted features
2. Test each role is blocked from forbidden features
3. Test viewer cannot generate reports or modify data
4. Test admin can manage users but not system config
5. Test super_admin has full access
6. Test role enforcement at both UI and DAL levels

## Subtasks
No subtasks yet — run task-master expand to generate.
