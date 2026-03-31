# Task 22: Build DCF Model Builder

## Status: PENDING
## Priority: high
## Dependencies: None

## Description
Create an interactive discounted cash flow calculator with editable assumptions (revenue growth, margins, WACC, terminal growth), projected free cash flows, sensitivity analysis table, scenario analysis (bull/base/bear), and AI commentary on the valuation result.

## Details
Create data/dcf_model.py with DCFCalculator class. Inputs: revenue growth rates (5yr), operating margin trajectory, WACC (auto-calc from beta + risk-free + ERP, or manual), terminal growth rate, tax rate, shares outstanding (auto from yfinance). Outputs: projected FCF table, terminal value, enterprise value, equity value, implied price, upside/downside. Sensitivity table: 2D matrix of implied price across WACC (7-13%) and terminal growth (1-4%). Scenario toggles: Bull (optimistic), Base (consensus), Bear (conservative) with pre-set assumption shifts. Claude generates commentary interpreting result. UI: glass card input panel + output panel + sensitivity heatmap. Export to XLSX with formatted sensitivity table.

## Test Strategy
1. Test DCF calculation against manual spreadsheet for ARAMCO
2. Test sensitivity table values are mathematically correct
3. Test scenario toggles change assumptions correctly
4. Test auto-fill from Yahoo Finance data
5. Test WACC auto-calculation from beta
6. Test Excel export with proper formatting
7. Test AI commentary generation

## Subtasks
No subtasks yet — run task-master expand to generate.
