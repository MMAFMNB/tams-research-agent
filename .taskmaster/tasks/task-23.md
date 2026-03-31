# Task 23: Build Risk Metrics Dashboard

## Status: PENDING
## Priority: medium
## Dependencies: 18

## Description
Add portfolio-level risk analytics: Value at Risk (95% confidence), Sharpe ratio, maximum drawdown, correlation matrix heatmap, and beta analysis. Displayed as interactive Plotly visualizations on the Portfolio page.

## Details
Create data/risk_metrics.py module. Calculate: historical VaR (95%, 1-day and 10-day), parametric VaR, Sharpe ratio (using TASI as benchmark), max drawdown with recovery period, correlation matrix between portfolio holdings, individual and portfolio beta. Use 1-year daily returns from yfinance. Display: VaR gauge chart, Sharpe ratio card, drawdown chart (Plotly area), correlation heatmap (Plotly), risk summary table. All styled with TAM Liquid Glass theme.

## Test Strategy
1. Test VaR calculation against known formula
2. Test Sharpe ratio with risk-free rate input
3. Test drawdown calculation identifies correct peak-to-trough
4. Test correlation matrix is symmetric with 1.0 diagonal
5. Test with portfolio of 1 stock (edge case)
6. Test visualizations render correctly

## Subtasks
No subtasks yet — run task-master expand to generate.
