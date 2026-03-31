# Task 34: Build Financial Statement Interactive Viewer

## Status: PENDING
## Priority: medium
## Dependencies: 18

## Description
Create an interactive 5-year financial statement viewer (income statement, balance sheet, cash flow) with expandable line items, growth rate calculations, margin analysis, and trend sparklines. Displayed as glass-styled tables with Plotly mini-charts.

## Details
Create data/financial_viewer.py module. Pull 5-year annual financials from yfinance (income_stmt, balance_sheet, cashflow). Display as expandable HTML tables with: line item name, 5 years of values, YoY growth %, CAGR, sparkline trend. Three tabs: Income Statement, Balance Sheet, Cash Flow. Key metrics highlighted: revenue, net income, total assets, free cash flow. Margins calculated inline: gross margin, operating margin, net margin. All numbers formatted with locale-aware formatting (SAR thousands/millions). Glass card styling consistent with TAM Liquid Glass theme.

## Test Strategy
1. Test data loads for Saudi tickers
2. Test all three statement types display correctly
3. Test growth rate calculations are accurate
4. Test sparklines render correctly
5. Test expandable sections toggle properly
6. Test with tickers missing some data (graceful handling)

## Subtasks
No subtasks yet — run task-master expand to generate.
