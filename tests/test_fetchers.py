import vcr

import httpx
from analytics.fetchers import fetch_rss_feed_entries


def test_fetch_rss_feed_entries() -> None:
    with vcr.use_cassette(
        "fetch_rss_feed_entries.yml",
        cassette_library_dir="tests/fixtures/cassettes",
    ):
        entries = list(fetch_rss_feed_entries())

        assert len(entries) == 25
