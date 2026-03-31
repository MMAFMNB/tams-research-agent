# Task 18: Build Interactive Plotly Technical Charts

## Status: PENDING
## Priority: high
## Dependencies: None

## Description
Replace static Matplotlib charts with interactive Plotly charts featuring candlestick views, technical indicator overlays (MA, Bollinger, RSI, MACD, Fibonacci), time range selectors, dark theme matching TAM Liquid Glass, and comparison mode for overlaying multiple tickers.

## Details
Create data/interactive_charts.py module. Build functions: generate_candlestick_chart(), generate_technical_chart(), generate_comparison_chart(). Use plotly.graph_objects for candlestick + volume overlay. Add toggleable indicator overlays via Streamlit checkboxes. Support time ranges: 1W, 1M, 3M, 6M, 1Y, 5Y, MAX. Apply TAM dark theme (transparent bg, TAM accent colors). Use st.plotly_chart() with use_container_width=True. Embed in Research, Portfolio, Compare pages.

## Test Strategy
1. Test candlestick chart renders for Saudi tickers
2. Test each indicator overlay toggles correctly
3. Test time range selector changes data window
4. Test comparison mode with 2-3 tickers
5. Test chart responsiveness on different screen sizes
6. Verify dark theme colors match TAM Liquid Glass
7. Test zoom, pan, and crosshair interactions

## Subtasks
No subtasks yet — run task-master expand to generate.
