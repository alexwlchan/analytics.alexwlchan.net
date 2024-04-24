import vcr

from analytics.fetchers import fetch_rss_feed_entries


def test_fetch_rss_feed_entries() -> None:
    with vcr.use_cassette(
        "fetch_rss_feed_entries.yml",
        cassette_library_dir="tests/fixtures/cassettes",
    ):
        # Check we can fetch it.  This should set the
        # If-Modified-Since header.
        entries1 = list(fetch_rss_feed_entries())

        assert len(entries1) == 25

        # Check we can fetch it when sending the If-Modified-Since header.
        entries2 = list(fetch_rss_feed_entries())

        assert entries1 == entries2
        assert len(entries2) == 25
