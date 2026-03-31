# Task 12: Build Data Access Layer (DAL) Module

## Status: PENDING
## Priority: high
## Dependencies: 11

## Description
Create a supabase_client.py module that provides a clean Python API for all database operations, replacing all JSON file read/write operations across the codebase. Include connection pooling, error handling, and graceful fallback to JSON for local development.

## Details
Create data/supabase_client.py with classes/functions for: UserDAO, WatchlistDAO, PortfolioDAO, ReportDAO, AlertDAO, ChatDAO, ActivityDAO, SentimentDAO. Each DAO mirrors the existing JSON operations but uses Supabase. Add connection management with supabase-py library. Implement retry logic and graceful degradation.

## Test Strategy
1. Unit test each DAO method with mock Supabase client
2. Integration test: write then read back data
3. Test fallback to JSON when Supabase unavailable
4. Test connection pooling under 15 concurrent users
5. Verify zero data loss during migration

## Subtasks
No subtasks yet — run task-master expand to generate.
