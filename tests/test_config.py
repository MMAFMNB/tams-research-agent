"""Tests for config and ticker resolution."""

import pytest
from config import resolve_ticker, TADAWUL_TICKERS


class TestTickerResolution:
    def test_tadawul_number(self):
        assert resolve_ticker("2222") == "2222.SR"
        assert resolve_ticker("1120") == "1120.SR"

    def test_already_has_suffix(self):
        assert resolve_ticker("2222.SR") == "2222.SR"

    def test_unknown_number_gets_sr_suffix(self):
        assert resolve_ticker("9999") == "9999.SR"

    def test_global_ticker_passthrough(self):
        assert resolve_ticker("AAPL") == "AAPL"
        assert resolve_ticker("MSFT") == "MSFT"

    def test_case_insensitive(self):
        assert resolve_ticker("aapl") == "AAPL"

    def test_whitespace_stripped(self):
        assert resolve_ticker("  2222  ") == "2222.SR"

    def test_tadawul_map_not_empty(self):
        assert len(TADAWUL_TICKERS) > 0
        assert "2222" in TADAWUL_TICKERS
