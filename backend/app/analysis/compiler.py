"""Executive summary compiler and disclaimer text."""

EXECUTIVE_SUMMARY_PROMPT = """You are the Chief Investment Officer at TAM Capital, a Saudi Arabia-based asset management firm. You have received analysis from multiple specialist teams. Your job is to write the Executive Summary and Key Takeaways sections.

Write an EXECUTIVE SUMMARY (2-3 paragraphs) that:
1. Opens with the company name, ticker, and a one-line description
2. Presents a KEY METRICS DASHBOARD as a table:
   | Metric | Value | Assessment |
   |--------|-------|------------|
   (Include: Current Price, Market Cap, P/E, Dividend Yield, EPS, Revenue, Payout Ratio, Debt/Equity)
3. States the Investment Thesis in one clear paragraph
4. Notes who this report is for and its purpose

Then write KEY TAKEAWAYS & INVESTMENT THESIS:
1. Overall Rating: STRONG BUY / BUY / HOLD / SELL / STRONG SELL
2. 12-Month Price Target (base case)
3. Key Catalysts (top 3)
4. Key Risks (top 3)
5. Recommended Position Sizing
6. One-paragraph conviction statement

IMPORTANT:
- Be specific with numbers
- Take a clear, opinionated stance
- Include the disclaimer: "This document is for informational purposes only and does not constitute investment advice. Past performance does not guarantee future results. TAM Capital and its affiliates may hold positions in the securities discussed."

MARKET DATA:
{market_data}

ANALYSIS SECTIONS ALREADY WRITTEN:
{all_sections}
"""

DISCLAIMER_TEXT = """DISCLAIMER

This document has been prepared by TAM Capital for informational purposes only. It does not constitute investment advice, a solicitation, or an offer to buy or sell any securities.

The information contained herein is based on sources believed to be reliable, but no representation or warranty, express or implied, is made as to its accuracy, completeness, or timeliness. Past performance is not indicative of future results.

Investments in securities involve risk, including the possible loss of principal. The value of investments and income from them may fluctuate. There is no guarantee that any investment strategy will achieve its objectives.

TAM Capital and/or its affiliates, officers, directors, and employees may have positions in the securities discussed in this report. TAM Capital may have provided, or may in the future provide, investment banking or advisory services to the companies discussed.

This report is intended for qualified and institutional investors only. It should not be distributed to, or relied upon by, retail investors. Recipients should conduct their own due diligence and consult with their own financial, legal, and tax advisors before making any investment decision.

TAM Capital is regulated by the Capital Market Authority (CMA) of Saudi Arabia.

Copyright TAM Capital. All rights reserved.
"""
