# Task 33: Build Peer Benchmarking Heat Map

## Status: PENDING
## Priority: medium
## Dependencies: 18

## Description
Create an interactive heat map visualization that compares a stock against its sector peers across 15+ financial ratios. Color-coded cells show relative ranking (green=top quartile, red=bottom quartile). Embedded in Research and Sectors pages.

## Details
Create data/peer_benchmark.py module. For a given ticker, identify sector peers from config.py TADAWUL_SECTORS mapping. Pull key metrics for all peers via yfinance: P/E, P/B, EV/EBITDA, ROE, ROA, debt/equity, dividend yield, revenue growth, profit margin, current ratio, beta, market cap, 52-week return, volume, free cash flow yield. Build Plotly heatmap: rows=tickers, columns=metrics, color scale=relative ranking within peer group. Highlight the target ticker's row. Add sort-by-metric capability. Export to Excel.

## Test Strategy
1. Test peer identification for each Tadawul sector
2. Test metrics pulled for all peers
3. Test heatmap renders with correct colors
4. Test target ticker row is highlighted
5. Test sort functionality
6. Test with sectors of different sizes (2 peers vs 8 peers)
7. Test Excel export includes all data

## Subtasks
No subtasks yet — run task-master expand to generate.
