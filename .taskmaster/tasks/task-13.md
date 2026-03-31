# Task 13: Migrate Existing JSON Data to Supabase

## Status: PENDING
## Priority: high
## Dependencies: 11, 12

## Description
Write a migration script that reads all existing JSON data (watchlists, portfolio, reports, alerts) and inserts it into the corresponding Supabase tables. Include validation, rollback capability, and data integrity checks.

## Details
Script reads from watchlist_data/*.json and report_history/*.json. Maps JSON structures to Supabase table schemas. Handles ID generation (UUID), date parsing, and JSONB field conversion. Provides dry-run mode to preview changes before committing. Logs all operations for audit.

## Test Strategy
1. Run migration on test data, verify row counts match
2. Spot-check 10 random records for data accuracy
3. Test rollback: delete migrated data and re-run
4. Verify report version chains preserved
5. Test with empty JSON files (fresh install scenario)

## Subtasks
No subtasks yet — run task-master expand to generate.
