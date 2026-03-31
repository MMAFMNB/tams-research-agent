# Task 28: Build Research Notes System

## Status: PENDING
## Priority: medium
## Dependencies: 12, 15

## Description
Allow analysts to attach timestamped markdown notes to any ticker. Notes are searchable, taggable, and visible on report detail and ticker overview pages. Includes pin-to-top functionality for important notes.

## Details
Create data/research_notes.py with NotesDAO for CRUD operations. UI: notes panel on Research page sidebar and ticker detail view. Each note: markdown content, tags (multi-select), pinned status, timestamp, author. New note form: text area + tag selector + save button. Notes list: sorted by pinned first, then date. Search bar: full-text search across all notes for the user. Tags: predefined (Bullish, Bearish, Catalyst, Risk, Earnings, Technical) + custom. Display author avatar + name for team visibility.

## Test Strategy
1. Test creating, editing, deleting notes
2. Test notes appear on correct ticker pages
3. Test search returns matching notes
4. Test tag filtering
5. Test pin/unpin functionality
6. Test notes persist across sessions via Supabase

## Subtasks
No subtasks yet — run task-master expand to generate.
