"""Tests for market monitoring module."""

import os
import shutil
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


MONITOR_TEST_DIR = os.path.join(os.path.dirname(__file__), "test_monitor_data")


@pytest.fixture(autouse=True)
def isolate_monitor(monkeypatch):
    os.makedirs(MONITOR_TEST_DIR, exist_ok=True)
    import data.market_monitor as mm
    monkeypatch.setattr(mm, "MONITOR_CACHE_DIR", MONITOR_TEST_DIR)
    monkeypatch.setattr(mm, "MONITOR_CACHE_FILE",
                        os.path.join(MONITOR_TEST_DIR, "monitor_cache.json"))
    yield
    shutil.rmtree(MONITOR_TEST_DIR, ignore_errors=True)


class TestCacheManagement:
    def test_empty_cache_loads(self):
        from data.market_monitor import _load_cache
        cache = _load_cache()
        assert "tickers" in cache

    def test_cache_round_trip(self):
        from data.market_monitor import _load_cache, _save_cache
        cache = _load_cache()
        cache["tickers"]["TEST"] = {"price": 100}
        _save_cache(cache)
        loaded = _load_cache()
        assert loaded["tickers"]["TEST"]["price"] == 100

    def test_stale_detection(self):
        from data.market_monitor import _is_stale
        assert _is_stale(None) is True
        assert _is_stale("2020-01-01T00:00:00") is True
        assert _is_stale(datetime.now().isoformat()) is False

    def test_stale_after_ttl(self):
        from data.market_monitor import _is_stale, CACHE_TTL_MINUTES
        old_time = (datetime.now() - timedelta(minutes=CACHE_TTL_MINUTES + 1)).isoformat()
        assert _is_stale(old_time) is True


class TestCheckTicker:
    @patch("data.market_monitor.yf.Ticker")
    def test_returns_price_data(self, mock_ticker_cls):
        mock_info = {
            "longName": "Saudi Aramco",
            "currentPrice": 35.50,
            "previousClose": 35.00,
            "volume": 5000000,
            "averageVolume": 3000000,
        }
        mock_ticker_cls.return_value.info = mock_info

        from data.market_monitor import check_ticker
        result = check_ticker("2222.SR", force=True)

        assert result["current_price"] == 35.50
        assert result["previous_close"] == 35.00
        assert result["price_change_pct"] == pytest.approx(1.43, abs=0.01)
        assert result["error"] is None

    @patch("data.market_monitor.yf.Ticker")
    def test_flags_large_price_movement(self, mock_ticker_cls):
        mock_ticker_cls.return_value.info = {
            "longName": "Test Corp",
            "currentPrice": 110,
            "previousClose": 100,
            "volume": 1000000,
            "averageVolume": 1000000,
        }
        from data.market_monitor import check_ticker
        result = check_ticker("TEST", force=True)

        assert len(result["alerts"]) >= 1
        assert result["alerts"][0]["type"] == "price_movement"
        assert "surged" in result["alerts"][0]["message"]

    @patch("data.market_monitor.yf.Ticker")
    def test_flags_volume_spike(self, mock_ticker_cls):
        mock_ticker_cls.return_value.info = {
            "longName": "Volume Corp",
            "currentPrice": 50,
            "previousClose": 50,
            "volume": 10000000,
            "averageVolume": 2000000,
        }
        from data.market_monitor import check_ticker
        result = check_ticker("VOL", force=True)

        volume_alerts = [a for a in result["alerts"] if a["type"] == "volume_spike"]
        assert len(volume_alerts) == 1

    @patch("data.market_monitor.yf.Ticker")
    def test_no_alerts_on_normal_day(self, mock_ticker_cls):
        mock_ticker_cls.return_value.info = {
            "longName": "Calm Corp",
            "currentPrice": 100.50,
            "previousClose": 100.00,
            "volume": 1000000,
            "averageVolume": 1000000,
        }
        from data.market_monitor import check_ticker
        result = check_ticker("CALM", force=True)

        assert len(result["alerts"]) == 0

    @patch("data.market_monitor.yf.Ticker")
    def test_handles_api_error_gracefully(self, mock_ticker_cls):
        mock_ticker_cls.return_value.info.__getitem__ = MagicMock(side_effect=Exception("API down"))
        mock_ticker_cls.return_value.info = None

        from data.market_monitor import check_ticker
        result = check_ticker("FAIL", force=True)
        # Should not raise, should have error field
        assert result["ticker"] == "FAIL"

    @patch("data.market_monitor.yf.Ticker")
    def test_uses_cache_when_fresh(self, mock_ticker_cls):
        mock_ticker_cls.return_value.info = {
            "longName": "Cache Corp", "currentPrice": 50,
            "previousClose": 50, "volume": 100, "averageVolume": 100,
        }
        from data.market_monitor import check_ticker

        # First call hits API
        check_ticker("CACHE", force=True)
        # Second call should use cache (force=False)
        result = check_ticker("CACHE", force=False)
        # yf.Ticker should only be called once (second uses cache)
        assert mock_ticker_cls.call_count == 1


class TestScanWatchlist:
    @patch("data.market_monitor.yf.Ticker")
    def test_scan_multiple_tickers(self, mock_ticker_cls):
        mock_ticker_cls.return_value.info = {
            "longName": "Test", "currentPrice": 50, "previousClose": 50,
            "volume": 100, "averageVolume": 100,
        }
        from data.market_monitor import scan_watchlist
        results = scan_watchlist(["A", "B", "C"], force=True)
        assert len(results) == 3

    @patch("data.market_monitor.yf.Ticker")
    def test_alerts_sorted_first(self, mock_ticker_cls):
        call_count = [0]
        def mock_info_side_effect(ticker):
            call_count[0] += 1
            m = MagicMock()
            if ticker == "ALERT":
                m.info = {"longName": "Alert", "currentPrice": 120,
                         "previousClose": 100, "volume": 100, "averageVolume": 100}
            else:
                m.info = {"longName": "Calm", "currentPrice": 100,
                         "previousClose": 100, "volume": 100, "averageVolume": 100}
            return m

        mock_ticker_cls.side_effect = mock_info_side_effect

        from data.market_monitor import scan_watchlist
        results = scan_watchlist(["CALM", "ALERT"], force=True)
        # ALERT should be first (has alerts)
        assert results[0]["ticker"] == "ALERT"
