"""
Tests for ``analytics.fetch_rss_feed``.
"""

import datetime
import pathlib

import pytest

from analytics.fetch_rss_feed import fetch_rss_feed_entries, NoNewEntries


@pytest.mark.vcr()
def test_fetch_rss_feed_entries(tmp_working_dir: pathlib.Path) -> None:
    """
    Fetch entries from my RSS feed.
    """
    entries = fetch_rss_feed_entries()

    assert next(entries) == {
        "id": "https://alexwlchan.net/2024/documenting-my-dns",
        "date_posted": datetime.datetime(
            2024, 5, 25, 13, 21, 10, tzinfo=datetime.timezone.utc
        ),
        "title": "Documenting my DNS records",
        "url": "https://alexwlchan.net/2024/documenting-my-dns/",
        "host": "alexwlchan.net",
        "path": "/2024/documenting-my-dns/",
    }

    assert next(entries) == {
        "id": "https://alexwlchan.net/2024/preserving-pixels-in-paris",
        "date_posted": datetime.datetime(
            2024, 5, 23, 20, 52, 42, tzinfo=datetime.timezone.utc
        ),
        "title": "Preserving pixels in Paris",
        "url": "https://alexwlchan.net/2024/preserving-pixels-in-paris/",
        "host": "alexwlchan.net",
        "path": "/2024/preserving-pixels-in-paris/",
    }


@pytest.mark.vcr()
def test_it_skips_if_no_new_entries(tmp_working_dir: pathlib.Path) -> None:
    """
    If there are no new entries since I last fetched the RSS feed,
    do nothing.

    This is using the HTTP caching headers to reduce passing around
    unnecessary data.
    """
    for _ in fetch_rss_feed_entries():
        pass

    with pytest.raises(NoNewEntries):
        for _ in fetch_rss_feed_entries():
            pass  # pragma: no cover

    assert (tmp_working_dir / "rss_feed.etag.txt").exists()
