# Task 32: Add Interactive Pre-Analysis Questions

## Status: PENDING
## Priority: high
## Dependencies: None

## Description
Before running any research, sector analysis, or comparison, ask the user clarifying questions to tailor the output: investment horizon, risk tolerance, specific focus areas, comparison metrics preference, language preference (Arabic/English/Both). Display as a glass-styled question card with smart defaults.

## Details
Create a pre-analysis questionnaire system. For single stock research: ask about investment horizon (short/medium/long-term), focus areas (fundamentals only, technicals only, both, specific sections), risk appetite, output language. For sector analysis: ask about which metrics to emphasize, peer group size, include ESG? For comparison: ask which metrics to compare, weighting preferences, visualization preference (table vs chart). UI: glass card with radio buttons / multi-select checkboxes, 'Quick Start' button that uses defaults, 'Customize' that shows full options. Store user's last preferences as defaults for next time. Inject selected preferences into the Claude prompt for customized output.

## Test Strategy
1. Test question card appears before research
2. Test 'Quick Start' uses saved defaults
3. Test 'Customize' shows full options
4. Test selected preferences affect Claude output
5. Test preferences persist between sessions
6. Test for each analysis type (research, sector, comparison)
7. Test Arabic/English language selection works

## Subtasks
No subtasks yet — run task-master expand to generate.
