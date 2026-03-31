# Task 14: Update All App Modules to Use Supabase DAL

## Status: PENDING
## Priority: high
## Dependencies: 12, 13

## Description
Replace all JSON file operations in app.py, portfolio.py, watchlist.py, report_store.py, alert_engine.py, and market_monitor.py with calls to the new Supabase DAL. Ensure all existing features work identically with the new backend.

## Details
Systematically update imports and function calls in each module. Replace get_positions() JSON reads with PortfolioDAO.get_positions(user_id). Replace watchlist.json reads with WatchlistDAO calls. Replace report_history JSON reads with ReportDAO calls. Update chat session storage. Test each page end-to-end after migration.

## Test Strategy
1. Test each page (Dashboard, Research, Portfolio, Sectors, Compare, Watchlist)
2. Verify all CRUD operations work: add/remove watchlist items, positions, etc.
3. Test report generation and storage
4. Test report versioning and comparison
5. Run full regression: every feature must work as before

## Subtasks
No subtasks yet — run task-master expand to generate.
