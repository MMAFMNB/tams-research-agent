# TAM Research Terminal — V2 Polish & Fix PRD

## Overview

The TAM Research Terminal has undergone a light theme redesign. The inner app pages (Research, Sectors, Compare, etc.) are working well with the new light theme. However, several critical issues remain that must be fixed before the platform is presentable.

## Priority 1: Landing Page — Fix for Light Theme

### Problem
The landing page (`views/landing.py`) still renders with dark theme styling. The hero text uses `color:white` which is invisible on the new white/light background. Feature section heading "Everything You Need" also uses `color:white`. The overall page looks broken on light backgrounds.

### Requirements
- Fix hero heading: change `color:white` to use `C_TEXT` (#0F172A) for all heading text
- Fix "Everything You Need" heading: change `color:white` to `C_TEXT`
- Fix the fallback text "TAM CAPITAL" in navbar (line 90): change `color:white` to `C_TEXT`
- Fix footer border: change `rgba(255,255,255,0.05)` to use `C_BORDER`
- Ensure all text on the landing page has sufficient contrast on the light (#F8FAFC) background
- "Invest Smarter" text should be prominently visible (use `C_TEXT` or `C_DEEP`)
- "Saudi Markets" italic accent should remain `C_TURQUOISE` (already correct)
- Keep the gradient on the "Start Research" / "Get Started" buttons (already working)

### Files
- `views/landing.py` — lines 105, 138, 90, 198

---

## Priority 2: API / Rate Limit Error — Diagnose and Fix

### Problem
The app shows "Too Many Requests. Rate limited." error immediately on the very first research query, even after hours of inactivity. User is on Anthropic Tier 3 (2K req/min, 800K input tokens/min). This suggests the issue is NOT a real rate limit but potentially:
1. API key mismatch between Streamlit Cloud secrets and the key on the Anthropic dashboard
2. API key not properly loaded from secrets
3. Model string mismatch or deprecated model name

### Requirements
- Add startup diagnostic: on app load, verify the API key is present and valid (test with a minimal 1-token call)
- Add a visible error message if API key is missing or invalid (instead of showing "rate limited")
- Add better error classification: distinguish between "no API key", "invalid API key", "actual rate limit", and "server error"
- Catch the specific error message string "Too Many Requests" and map it to a helpful user message
- Show the model being used in the error message for debugging
- Consider adding a simple health check endpoint or status indicator

### Files
- `app.py` — `_call_with_retries()`, `call_claude()`, `_handle_user_prompt()`
- `config.py` — verify MODEL string is valid

---

## Priority 3: Quick Suggestion Chips — Make Clickable

### Problem
The quick action chips on the Research page ("Analyze SABIC", "TASI market outlook", etc.) are rendered as plain HTML `<span>` elements. They look like buttons but are NOT clickable — they have no click handler because they're just HTML text rendered via `st.markdown()`.

### Requirements
- Convert each quick chip to a native `st.button()` so it's actually clickable
- When clicked, the chip should auto-submit its text as a research query (set `st.session_state.quick_prompt` and rerun)
- Use the existing `quick_prompt` mechanism that already feeds into the chat input
- Style the buttons to look like pills/chips (rounded, compact) matching the current CSS `.quick-chip` class
- Remove the HTML-only chips after replacing with real buttons

### Files
- `app.py` — `_render_market_overview_empty_state()` function

---

## Priority 4: Sector "Analyze" Buttons — Fix Styling and Functionality

### Problem
The Sector page buttons ("Analyze Banks", "Analyze Petrochemicals", etc.) appear as white/washed-out rectangles. They should be styled as TAM gradient accent buttons and must be fully functional.

### Requirements
- Ensure sector "Analyze" buttons use the primary button type so they get the TAM gradient styling
- Verify each button triggers the correct sector analysis when clicked
- If any buttons are non-functional, either fix them or remove them
- All buttons across the entire app must be either functional or removed — no dead/decorative buttons

### Files
- `app.py` — `render_sectors()` function
- `assets/style.css` — button styling rules

---

## Priority 5: Compare Page Buttons — Fix Styling

### Problem
The "Run Comparison" button and quick comparison buttons ("Banks Comparison", "Telecom Comparison", "Energy Comparison") appear washed out with invisible text on light background.

### Requirements
- Ensure "Run Comparison" uses primary button type for gradient styling
- Ensure quick comparison buttons are properly styled and visible
- All buttons must have readable text on the light background

### Files
- `app.py` — `render_comparison()` function

---

## Priority 6: Chat Input Bar — Dark Background Strip

### Problem
The chat input bar at the bottom of the Research page still has a dark navy background strip that clashes with the light theme. This is residual from the dark theme.

### Requirements
- Remove the dark background strip behind the chat input
- Chat input should blend with the light page background
- The input box itself should be white with a subtle border (already mostly correct from CSS)
- The gradient send button should remain as-is (looks good)

### Files
- `assets/style.css` — `[data-testid="stChatInput"]` rules
- `app.py` — check for any inline dark background on the chat input container

---

## Priority 7: Sidebar Footer Text

### Problem
The sidebar shows "TAM Capital | CMA Regulated" and "Confidential - Internal Use Only" footer text. Verify this displays correctly on the light sidebar background.

### Requirements
- Footer text should be visible (use `C_TEXT2` or `C_MUTED` color)
- Ensure proper contrast on the light sidebar background

### Files
- `app.py` — sidebar footer section

---

## Priority 8: Global Button Audit

### Problem
User explicitly stated: "all buttons need to be clickable or we shouldn't have a button that's not clickable." Multiple buttons across the app may be decorative HTML or non-functional.

### Requirements
- Audit EVERY button across all pages: landing, research, dashboard, sectors, compare, portfolio, watchlist, alerts
- For each button: verify it has a click handler that does something
- Remove or replace any HTML-rendered fake buttons with native `st.button()`
- Ensure all primary action buttons use the gradient TAM styling
- Ensure all secondary buttons have visible text and borders on light backgrounds

### Files
- All page render functions in `app.py`
- `views/landing.py`

---

## Non-Functional Requirements

- All changes must maintain Python syntax validity (run `ast.parse()` check)
- No hardcoded `color:white` anywhere in inline HTML on any page
- All text must have WCAG AA contrast ratio on the light (#F8FAFC / #FFFFFF) backgrounds
- The app must load without errors on Streamlit Cloud
