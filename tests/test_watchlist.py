"""Tests for analyst watchlist."""

import os
import shutil
import pytest


WATCHLIST_TEST_DIR = os.path.join(os.path.dirname(__file__), "test_watchlist_data")


@pytest.fixture(autouse=True)
def isolate_watchlist(monkeypatch):
    """Use isolated directory for each test."""
    os.makedirs(WATCHLIST_TEST_DIR, exist_ok=True)
    import data.watchlist as wl_mod
    monkeypatch.setattr(wl_mod, "WATCHLIST_DIR", WATCHLIST_TEST_DIR)
    monkeypatch.setattr(wl_mod, "WATCHLIST_FILE",
                        os.path.join(WATCHLIST_TEST_DIR, "watchlist.json"))
    yield
    shutil.rmtree(WATCHLIST_TEST_DIR, ignore_errors=True)


class TestWatchlistCRUD:
    def test_create_watchlist(self):
        from data.watchlist import create_watchlist, get_watchlists

        wl = create_watchlist("My List", "Test description")
        assert wl["name"] == "My List"
        assert wl["is_default"] is True
        assert get_watchlists()[0]["name"] == "My List"

    def test_create_second_watchlist_not_default(self):
        from data.watchlist import create_watchlist

        create_watchlist("First")
        wl2 = create_watchlist("Second")
        assert wl2["is_default"] is False

    def test_duplicate_name_rejected(self):
        from data.watchlist import create_watchlist

        create_watchlist("Dupes")
        with pytest.raises(ValueError, match="already exists"):
            create_watchlist("dupes")  # case-insensitive

    def test_watchlist_limit(self):
        from data.watchlist import create_watchlist, MAX_WATCHLISTS

        for i in range(MAX_WATCHLISTS):
            create_watchlist(f"List {i}")
        with pytest.raises(ValueError, match="limit"):
            create_watchlist("One Too Many")

    def test_delete_watchlist(self):
        from data.watchlist import create_watchlist, delete_watchlist, get_watchlists

        wl = create_watchlist("Delete Me")
        assert delete_watchlist(wl["id"]) is True
        assert len(get_watchlists()) == 0

    def test_delete_nonexistent(self):
        from data.watchlist import delete_watchlist

        assert delete_watchlist(9999) is False


class TestWatchlistItems:
    def test_add_ticker(self):
        from data.watchlist import create_watchlist, add_ticker, get_watchlist

        wl = create_watchlist("Test")
        item = add_ticker(wl["id"], "2222.SR", "Aramco")
        assert item["ticker"] == "2222.SR"

        loaded = get_watchlist(wl["id"])
        assert len(loaded["items"]) == 1

    def test_add_duplicate_ticker_rejected(self):
        from data.watchlist import create_watchlist, add_ticker

        wl = create_watchlist("Test")
        add_ticker(wl["id"], "2222.SR", "Aramco")
        with pytest.raises(ValueError, match="already in"):
            add_ticker(wl["id"], "2222.SR", "Aramco Again")

    def test_remove_ticker(self):
        from data.watchlist import create_watchlist, add_ticker, remove_ticker, get_watchlist

        wl = create_watchlist("Test")
        add_ticker(wl["id"], "2222.SR", "Aramco")
        assert remove_ticker(wl["id"], "2222.SR") is True
        assert len(get_watchlist(wl["id"])["items"]) == 0

    def test_remove_nonexistent_ticker(self):
        from data.watchlist import create_watchlist, remove_ticker

        wl = create_watchlist("Test")
        assert remove_ticker(wl["id"], "FAKE") is False

    def test_ticker_uppercased(self):
        from data.watchlist import create_watchlist, add_ticker

        wl = create_watchlist("Test")
        item = add_ticker(wl["id"], "aapl", "Apple")
        assert item["ticker"] == "AAPL"

    def test_get_all_watched_tickers(self):
        from data.watchlist import create_watchlist, add_ticker, get_all_watched_tickers

        wl1 = create_watchlist("List 1")
        wl2 = create_watchlist("List 2")
        add_ticker(wl1["id"], "2222.SR", "Aramco")
        add_ticker(wl1["id"], "AAPL", "Apple")
        add_ticker(wl2["id"], "2222.SR", "Aramco")  # duplicate across lists
        add_ticker(wl2["id"], "MSFT", "Microsoft")

        tickers = get_all_watched_tickers()
        assert sorted(tickers) == ["2222.SR", "AAPL", "MSFT"]

    def test_get_default_watchlist(self):
        from data.watchlist import create_watchlist, get_default_watchlist

        wl = create_watchlist("Default One")
        default = get_default_watchlist()
        assert default["id"] == wl["id"]
