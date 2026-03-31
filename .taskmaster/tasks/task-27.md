# Task 27: Build Predictive Signals System (Experimental)

## Status: PENDING
## Priority: low
## Dependencies: 25, 23

## Description
Create experimental ML signals: earnings surprise probability, momentum score, and risk signal. Display as 'AI Signals' badges on ticker cards with confidence levels. Clearly labeled as experimental with CMA compliance disclaimers.

## Details
Create ml/predictive_signals.py. Earnings Surprise: analyze historical earnings vs estimates pattern from yfinance, combine with current sentiment score, output probability (0-100%). Momentum Score: composite of 14-day price momentum + volume trend (20-day) + sentiment trend, normalized 0-100. Risk Signal: combines VaR percentile + sentiment decline rate + volume anomaly score, outputs low/medium/high with score. Display as colored badges on ticker cards and research page. Every signal includes: confidence level, calculation timestamp, disclaimer text. CMA compliance: 'This is an AI-generated experimental signal and does not constitute investment advice.'

## Test Strategy
1. Test each signal produces valid output range
2. Test signals update when new data available
3. Test badge display on ticker cards
4. Test disclaimer is always visible
5. Test with tickers that have limited history (edge case)
6. Backtest signals against historical data for basic validation

## Subtasks
No subtasks yet — run task-master expand to generate.
