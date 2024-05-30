import datetime

import pytest

from analytics.fetchers import fetch_rss_feed_entries


@pytest.mark.vcr()
def test_fetch_rss_feed_entries() -> None:
    entries = list(fetch_rss_feed_entries())
    assert entries[:2] == [
        {
            "id": "https://alexwlchan.net/2024/documenting-my-dns",
            "date_posted": datetime.datetime(
                2024, 5, 25, 13, 21, 10, tzinfo=datetime.timezone.utc
            ),
            "title": "Documenting my DNS records",
            "url": "https://alexwlchan.net/2024/documenting-my-dns/",
            "host": "alexwlchan.net",
            "path": "/2024/documenting-my-dns/",
        },
        {
            "id": "https://alexwlchan.net/2024/preserving-pixels-in-paris",
            "date_posted": datetime.datetime(
                2024, 5, 23, 20, 52, 42, tzinfo=datetime.timezone.utc
            ),
            "title": "Preserving pixels in Paris",
            "url": "https://alexwlchan.net/2024/preserving-pixels-in-paris/",
            "host": "alexwlchan.net",
            "path": "/2024/preserving-pixels-in-paris/",
        },
    ]
