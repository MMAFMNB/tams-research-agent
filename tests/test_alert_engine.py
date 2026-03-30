"""Tests for alert engine with cooldown and history."""

import os
import shutil
import pytest
from datetime import datetime, timedelta

ALERT_TEST_DIR = os.path.join(os.path.dirname(__file__), "test_alert_data")


@pytest.fixture(autouse=True)
def isolate_alerts(monkeypatch):
    os.makedirs(ALERT_TEST_DIR, exist_ok=True)
    import data.alert_engine as ae
    monkeypatch.setattr(ae, "ALERT_DIR", ALERT_TEST_DIR)
    monkeypatch.setattr(ae, "ALERT_HISTORY_FILE",
                        os.path.join(ALERT_TEST_DIR, "alert_history.json"))
    yield
    shutil.rmtree(ALERT_TEST_DIR, ignore_errors=True)


class TestRecordAlert:
    def test_records_new_alert(self):
        from data.alert_engine import record_alert, get_recent_alerts
        result = record_alert("2222.SR", "price_movement", "major", "Aramco surged 5%")
        assert result is not None
        assert result["ticker"] == "2222.SR"
        assert len(get_recent_alerts()) == 1

    def test_cooldown_prevents_duplicate(self):
        from data.alert_engine import record_alert
        r1 = record_alert("2222.SR", "price_movement", "major", "Alert 1")
        r2 = record_alert("2222.SR", "price_movement", "major", "Alert 2")
        assert r1 is not None
        assert r2 is None  # Suppressed by cooldown

    def test_different_type_not_on_cooldown(self):
        from data.alert_engine import record_alert
        r1 = record_alert("2222.SR", "price_movement", "major", "Price alert")
        r2 = record_alert("2222.SR", "volume_spike", "moderate", "Volume alert")
        assert r1 is not None
        assert r2 is not None

    def test_different_ticker_not_on_cooldown(self):
        from data.alert_engine import record_alert
        r1 = record_alert("2222.SR", "price_movement", "major", "Aramco")
        r2 = record_alert("7010.SR", "price_movement", "major", "STC")
        assert r1 is not None
        assert r2 is not None


class TestCooldown:
    def test_is_on_cooldown_after_record(self):
        from data.alert_engine import record_alert, is_on_cooldown
        record_alert("TEST", "price_movement", "major", "Test")
        assert is_on_cooldown("TEST", "price_movement") is True

    def test_not_on_cooldown_initially(self):
        from data.alert_engine import is_on_cooldown
        assert is_on_cooldown("NEW", "price_movement") is False


class TestHistory:
    def test_get_recent_alerts_ordered(self):
        from data.alert_engine import record_alert, get_recent_alerts
        record_alert("A", "t1", "minor", "First")
        record_alert("B", "t1", "major", "Second")
        recent = get_recent_alerts()
        assert len(recent) == 2
        assert recent[0]["ticker"] == "B"  # Newest first
        assert recent[1]["ticker"] == "A"

    def test_unread_count(self):
        from data.alert_engine import record_alert, get_unread_count
        record_alert("A", "t1", "minor", "1")
        record_alert("B", "t2", "minor", "2")
        assert get_unread_count() == 2

    def test_mark_all_read(self):
        from data.alert_engine import record_alert, mark_all_read, get_unread_count
        record_alert("A", "t1", "minor", "1")
        record_alert("B", "t2", "minor", "2")
        mark_all_read()
        assert get_unread_count() == 0

    def test_clear_history(self):
        from data.alert_engine import record_alert, clear_history, get_recent_alerts
        record_alert("A", "t1", "minor", "1")
        clear_history()
        assert len(get_recent_alerts()) == 0


class TestProcessMonitorAlerts:
    def test_processes_alerts_with_cooldown(self):
        from data.alert_engine import process_monitor_alerts, get_recent_alerts
        raw = [
            {"ticker": "A", "type": "price_movement", "severity": "major", "message": "A up"},
            {"ticker": "A", "type": "price_movement", "severity": "major", "message": "A up again"},  # dup
            {"ticker": "B", "type": "volume_spike", "severity": "moderate", "message": "B vol"},
        ]
        new = process_monitor_alerts(raw)
        assert len(new) == 2  # Second A alert suppressed
        assert len(get_recent_alerts()) == 2
