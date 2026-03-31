# Task 11: Set Up Supabase Project and Database Schema

## Status: PENDING
## Priority: high
## Dependencies: None

## Description
Initialize Supabase project, create all database tables (users, watchlists, watchlist_items, portfolio_positions, reports, alerts, alert_rules, research_notes, chat_sessions, user_activity, ai_sentiment_scores), configure indexes, and set up Row Level Security (RLS) policies for multi-tenant data isolation.

## Details
Create Supabase project via dashboard or CLI. Define all tables per PRD Phase 2 schema. Add proper indexes on frequently queried columns (user_id, ticker, created_at). Configure RLS so each user can only access their own data. Set up Supabase Vault for API key storage. Create migration SQL files for version control.

## Test Strategy
1. Verify all tables created with correct columns and types
2. Test RLS policies: user A cannot see user B's data
3. Test foreign key constraints
4. Benchmark query performance on indexed columns
5. Verify Supabase connection from Python client

## Subtasks
No subtasks yet — run task-master expand to generate.
