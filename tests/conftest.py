"""Shared fixtures for TAM Research Agent tests."""

import os
import sys
import shutil
import pytest

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

TEST_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "test_output")
TEST_HISTORY_DIR = os.path.join(os.path.dirname(__file__), "test_history")


@pytest.fixture(scope="session")
def output_dir():
    """Provide a clean test output directory."""
    os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)
    yield TEST_OUTPUT_DIR
    shutil.rmtree(TEST_OUTPUT_DIR, ignore_errors=True)


@pytest.fixture()
def history_dir(monkeypatch):
    """Provide a clean, isolated report history directory per test."""
    os.makedirs(TEST_HISTORY_DIR, exist_ok=True)
    import data.report_store as rs
    monkeypatch.setattr(rs, "REPORT_HISTORY_DIR", TEST_HISTORY_DIR)
    yield TEST_HISTORY_DIR
    shutil.rmtree(TEST_HISTORY_DIR, ignore_errors=True)


@pytest.fixture(scope="session")
def sample_sections():
    """Sample analysis sections for report generation tests."""
    return {
        "executive_summary": (
            "## Executive Summary\n"
            "- Revenue: SAR 12.5B (+15% YoY)\n"
            "- Net Income: SAR 3.2B\n"
            "- EPS: SAR 2.15\n"
            "- P/E Ratio: 18.5x\n"
            "- Dividend Yield: 4.2%\n"
            "### Recommendation\n"
            "- Strong buy with Price Target: SAR 45.00\n"
        ),
        "fundamental_analysis": (
            "## Financial Overview\n"
            "- Revenue: SAR 12.5B\n"
            "- Net Income: SAR 3.2B\n"
            "- EPS: SAR 2.15\n"
            "- ROE: 18.3%\n"
            "### Balance Sheet\n"
            "- Total Assets: SAR 85B\n"
            "- Debt/Equity: 0.35\n"
            "- Market Cap: SAR 250B\n"
            "\n"
            "| Metric | 2023 | 2024 | 2025E |\n"
            "|--------|------|------|-------|\n"
            "| Revenue (B) | 10.5 | 11.8 | 12.5 |\n"
            "| Net Income (B) | 2.8 | 3.0 | 3.2 |\n"
            "| EPS | 1.87 | 2.00 | 2.15 |\n"
        ),
        "key_takeaways": (
            "## Investment Thesis\n"
            "- Strong buy recommendation\n"
            "- Target price of SAR 45.00\n"
            "- Catalyst: Q2 earnings beat expected\n"
        ),
    }


@pytest.fixture(scope="session")
def sample_sections_v2():
    """Updated version of sample sections for comparison tests."""
    return {
        "executive_summary": (
            "## Executive Summary\n"
            "- Revenue: SAR 14.0B (+12% YoY)\n"
            "- Net Income: SAR 3.8B\n"
            "- EPS: SAR 2.45\n"
            "- P/E Ratio: 17.2x\n"
            "- Dividend Yield: 4.5%\n"
            "### Recommendation\n"
            "- Strong buy with Price Target: SAR 50.00\n"
        ),
        "fundamental_analysis": (
            "## Financial Overview\n"
            "- Revenue: SAR 14.0B\n"
            "- Net Income: SAR 3.8B\n"
            "- EPS: SAR 2.45\n"
            "- ROE: 19.1%\n"
            "### Balance Sheet\n"
            "- Total Assets: SAR 92B\n"
            "- Debt/Equity: 0.30\n"
            "- Market Cap: SAR 280B\n"
        ),
        "key_takeaways": (
            "## Investment Thesis\n"
            "- Strong buy recommendation maintained\n"
            "- Target price raised to SAR 50.00\n"
            "- Catalyst: Margin expansion and cost optimization\n"
        ),
        "risk_assessment": (
            "## Risk Factors\n"
            "- Oil price volatility\n"
            "- Regulatory changes\n"
        ),
    }
