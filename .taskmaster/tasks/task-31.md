# Task 31: Implement Research Cancel/Stop Functionality

## Status: PENDING
## Priority: high
## Dependencies: None

## Description
Add the ability to cancel an in-progress research analysis. When a user triggers analysis for the wrong ticker or wants to abort, they can click a 'Stop' button that cancels the Claude API call and returns to the chat input state without waiting for the full generation to complete.

## Details
Modify the analysis pipeline in app.py to support cancellation. Use threading: run analysis in a background thread, check a cancel flag periodically between section generations. Add a 'Stop Research' button (red, prominent) that appears during analysis progress. When clicked: set cancel flag, abort current API call (anthropic client supports cancel), clean up partial results, show 'Research cancelled' message. Partial results: offer to keep what was generated so far or discard entirely. Reset chat input state for new query.

## Test Strategy
1. Test cancel button appears during analysis
2. Test clicking cancel stops generation within 5 seconds
3. Test partial results are offered to user
4. Test discarding partial results cleans up properly
5. Test new analysis can start immediately after cancel
6. Test cancel during different stages (section 1, section 5, etc.)

## Subtasks
No subtasks yet — run task-master expand to generate.
