"""Tests for report store and versioning system."""

import pytest
import time


class TestReportStore:
    def test_save_and_load_report(self, history_dir):
        from data.report_store import save_report, load_report

        rid = save_report("Aramco", "2222.SR", {"exec": "test content"})
        loaded = load_report(rid)

        assert loaded is not None
        assert loaded["stock_name"] == "Aramco"
        assert loaded["ticker"] == "2222.SR"
        assert loaded["sections"]["exec"] == "test content"

    def test_version_auto_increments(self, history_dir):
        from data.report_store import save_report, load_report

        id1 = save_report("Aramco", "2222.SR", {"exec": "v1"})
        id2 = save_report("Aramco", "2222.SR", {"exec": "v2"})
        id3 = save_report("Aramco", "2222.SR", {"exec": "v3"})

        r1 = load_report(id1)
        r2 = load_report(id2)
        r3 = load_report(id3)

        assert r1["version"] == 1
        assert r2["version"] == 2
        assert r3["version"] == 3

    def test_different_tickers_independent_versions(self, history_dir):
        from data.report_store import save_report, load_report

        id_a = save_report("Aramco", "2222.SR", {"exec": "aramco"})
        id_s = save_report("STC", "7010.SR", {"exec": "stc"})

        assert load_report(id_a)["version"] == 1
        assert load_report(id_s)["version"] == 1

    def test_list_reports_all(self, history_dir):
        from data.report_store import save_report, list_reports

        save_report("Aramco", "2222.SR", {"exec": "a"})
        save_report("STC", "7010.SR", {"exec": "b"})

        reports = list_reports()
        assert len(reports) == 2

    def test_list_reports_filter_by_ticker(self, history_dir):
        from data.report_store import save_report, list_reports

        save_report("Aramco", "2222.SR", {"exec": "a"})
        save_report("STC", "7010.SR", {"exec": "b"})

        reports = list_reports(ticker="2222.SR")
        assert len(reports) == 1
        assert reports[0]["ticker"] == "2222.SR"

    def test_get_versions(self, history_dir):
        from data.report_store import save_report, get_versions

        save_report("Aramco", "2222.SR", {"exec": "v1"})
        save_report("Aramco", "2222.SR", {"exec": "v2"})

        versions = get_versions("2222.SR")
        assert len(versions) == 2
        # Newest first
        assert versions[0]["version"] == 2
        assert versions[1]["version"] == 1

    def test_change_summary_generated(self, history_dir):
        from data.report_store import save_report, load_report

        save_report("Aramco", "2222.SR", {"exec": "Revenue: SAR 10B\nEPS: SAR 2.00"})
        id2 = save_report("Aramco", "2222.SR", {"exec": "Revenue: SAR 12B\nEPS: SAR 2.50"})

        r2 = load_report(id2)
        assert r2["change_summary"] != ""
        assert "Improved" in r2["change_summary"] or "updated" in r2["change_summary"]

    def test_first_version_no_change_summary(self, history_dir):
        from data.report_store import save_report, load_report

        rid = save_report("Aramco", "2222.SR", {"exec": "first"})
        r = load_report(rid)
        assert r["change_summary"] == ""

    def test_delete_report(self, history_dir):
        from data.report_store import save_report, load_report, delete_report

        rid = save_report("Test", "TEST", {"exec": "delete me"})
        assert load_report(rid) is not None

        deleted = delete_report(rid)
        assert deleted is True
        assert load_report(rid) is None

    def test_load_nonexistent_report_returns_none(self, history_dir):
        from data.report_store import load_report

        assert load_report("nonexistent_id_xyz") is None
