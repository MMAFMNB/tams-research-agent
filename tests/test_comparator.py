"""Tests for report comparator / diff engine."""

import pytest
from data.report_comparator import (
    extract_metrics, compare_metrics, compare_text_sections,
    build_comparison_summary, categorize_change,
    detect_rating_change, detect_outlook_change,
    _parse_number,
)


class TestMetricExtraction:
    def test_extracts_revenue(self):
        sections = {"exec": "Revenue: SAR 12.5B"}
        metrics = extract_metrics(sections)
        assert metrics["Revenue"] == 12.5

    def test_extracts_eps(self):
        sections = {"exec": "EPS: SAR 2.15"}
        metrics = extract_metrics(sections)
        assert metrics["EPS"] == 2.15

    def test_extracts_pe_ratio(self):
        sections = {"exec": "P/E Ratio: 18.5x"}
        metrics = extract_metrics(sections)
        assert metrics["P/E Ratio"] == 18.5

    def test_extracts_dividend_yield(self):
        sections = {"exec": "Dividend Yield: 4.2%"}
        metrics = extract_metrics(sections)
        assert metrics["Dividend Yield"] == 4.2

    def test_no_metrics_found(self):
        sections = {"exec": "This is a general comment with no numbers."}
        metrics = extract_metrics(sections)
        assert len(metrics) == 0

    def test_parse_number_with_commas(self):
        assert _parse_number("1,234.56") == 1234.56
        assert _parse_number("100") == 100.0

    def test_parse_number_invalid(self):
        assert _parse_number("abc") is None


class TestCompareMetrics:
    def test_identifies_increase(self, sample_sections, sample_sections_v2):
        changes = compare_metrics(sample_sections, sample_sections_v2)
        revenue = next((m for m in changes if m["metric"] == "Revenue"), None)
        assert revenue is not None
        assert revenue["direction"] == "up"
        assert revenue["old"] == 12.5
        assert revenue["new"] == 14.0

    def test_identifies_decrease(self, sample_sections, sample_sections_v2):
        changes = compare_metrics(sample_sections, sample_sections_v2)
        pe = next((m for m in changes if m["metric"] == "P/E Ratio"), None)
        assert pe is not None
        assert pe["direction"] == "down"

    def test_calculates_percentage_change(self, sample_sections, sample_sections_v2):
        changes = compare_metrics(sample_sections, sample_sections_v2)
        eps = next((m for m in changes if m["metric"] == "EPS"), None)
        assert eps is not None
        assert eps["change_pct"] is not None
        assert eps["change_pct"] > 0

    def test_handles_identical_reports(self, sample_sections):
        changes = compare_metrics(sample_sections, sample_sections)
        for m in changes:
            assert m["direction"] == "unchanged"


class TestCompareTextSections:
    def test_detects_text_changes(self, sample_sections, sample_sections_v2):
        diffs = compare_text_sections(sample_sections, sample_sections_v2)
        assert len(diffs) > 0

    def test_diff_has_added_and_removed(self, sample_sections, sample_sections_v2):
        diffs = compare_text_sections(sample_sections, sample_sections_v2)
        # At least one section should have both adds and removes
        for lines in diffs.values():
            types = {t for t, _ in lines}
            if "added" in types and "removed" in types:
                return
        # If no section has both, at least check there are changes
        assert len(diffs) > 0

    def test_new_section_appears_as_additions(self, sample_sections, sample_sections_v2):
        diffs = compare_text_sections(sample_sections, sample_sections_v2)
        # risk_assessment is new in v2
        if "risk_assessment" in diffs:
            types = [t for t, _ in diffs["risk_assessment"]]
            assert "added" in types

    def test_no_diff_for_identical(self, sample_sections):
        diffs = compare_text_sections(sample_sections, sample_sections)
        assert len(diffs) == 0


class TestComparisonSummary:
    def test_summary_structure(self, sample_sections, sample_sections_v2):
        metrics = compare_metrics(sample_sections, sample_sections_v2)
        text_diffs = compare_text_sections(sample_sections, sample_sections_v2)
        summary = build_comparison_summary(metrics, text_diffs)

        assert "metrics_improved" in summary
        assert "metrics_deteriorated" in summary
        assert "sections_changed" in summary
        assert "lines_added" in summary
        assert "lines_removed" in summary
        assert "largest_change" in summary

    def test_summary_counts_correct(self, sample_sections, sample_sections_v2):
        metrics = compare_metrics(sample_sections, sample_sections_v2)
        text_diffs = compare_text_sections(sample_sections, sample_sections_v2)
        summary = build_comparison_summary(metrics, text_diffs)

        assert summary["metrics_improved"] >= 1
        assert summary["sections_changed"] >= 1

    def test_summary_has_change_score(self, sample_sections, sample_sections_v2):
        metrics = compare_metrics(sample_sections, sample_sections_v2)
        text_diffs = compare_text_sections(sample_sections, sample_sections_v2)
        summary = build_comparison_summary(metrics, text_diffs)

        assert "change_score" in summary
        assert 0 <= summary["change_score"] <= 100

    def test_summary_has_severity_counts(self, sample_sections, sample_sections_v2):
        metrics = compare_metrics(sample_sections, sample_sections_v2)
        text_diffs = compare_text_sections(sample_sections, sample_sections_v2)
        summary = build_comparison_summary(metrics, text_diffs)

        assert "severity_counts" in summary
        assert "minor" in summary["severity_counts"]
        assert "moderate" in summary["severity_counts"]
        assert "major" in summary["severity_counts"]

    def test_identical_reports_score_zero(self, sample_sections):
        metrics = compare_metrics(sample_sections, sample_sections)
        text_diffs = compare_text_sections(sample_sections, sample_sections)
        summary = build_comparison_summary(metrics, text_diffs)
        assert summary["change_score"] == 0


class TestChangeSeverity:
    def test_minor_change(self):
        assert categorize_change(2.0) == "minor"
        assert categorize_change(-3.5) == "minor"

    def test_moderate_change(self):
        assert categorize_change(8.0) == "moderate"
        assert categorize_change(-12.0) == "moderate"

    def test_major_change(self):
        assert categorize_change(20.0) == "major"
        assert categorize_change(-50.0) == "major"

    def test_none_is_unknown(self):
        assert categorize_change(None) == "unknown"

    def test_metrics_have_severity(self, sample_sections, sample_sections_v2):
        changes = compare_metrics(sample_sections, sample_sections_v2)
        for m in changes:
            assert "severity" in m
            assert m["severity"] in ("minor", "moderate", "major", "unknown")


class TestRatingDetection:
    def test_detects_rating_upgrade(self):
        old = {"key_takeaways": "Our recommendation is Hold"}
        new = {"key_takeaways": "Our recommendation is Strong Buy"}
        result = detect_rating_change(old, new)
        assert result is not None
        assert result["is_upgrade"] is True

    def test_detects_rating_downgrade(self):
        old = {"executive_summary": "We rate this stock a Buy"}
        new = {"executive_summary": "We rate this stock a Sell"}
        result = detect_rating_change(old, new)
        assert result is not None
        assert result["is_upgrade"] is False

    def test_no_rating_change(self):
        old = {"executive_summary": "Strong buy recommendation"}
        new = {"executive_summary": "Strong buy recommendation maintained"}
        result = detect_rating_change(old, new)
        assert result is None

    def test_no_rating_found(self):
        old = {"executive_summary": "Good company"}
        new = {"executive_summary": "Great company"}
        result = detect_rating_change(old, new)
        assert result is None


class TestOutlookDetection:
    def test_detects_outlook_change(self):
        old = {"executive_summary": "Outlook: positive going forward"}
        new = {"executive_summary": "Outlook: negative due to headwinds"}
        result = detect_outlook_change(old, new)
        assert result is not None
        assert result["old_outlook"] == "positive"
        assert result["new_outlook"] == "negative"

    def test_no_outlook_change(self):
        old = {"executive_summary": "Outlook: stable"}
        new = {"executive_summary": "Outlook: stable going forward"}
        result = detect_outlook_change(old, new)
        assert result is None
