"""
This file has a couple of functions for fetching data from remote sources --
anything that can't come from the local database.
"""

from collections.abc import Iterator
import datetime
import typing

import feedparser
import httpx

from .utils import get_password


class CachingClient(httpx.Client):
    """
    An HTTP client which does caching using the If-Modified-Since header
    to get faster responses.
    """

    def __init__(self) -> None:
        super().__init__()

        # (URL) -> (If-Modified-At, response)
        self._cache: dict[httpx.URL | str, tuple[str, httpx.Response]] = {}

    def get_with_caching(
        self, url: httpx.URL | str, headers: dict[str, str] | None = None
    ) -> httpx.Response:
        new_headers = headers or {}

        try:
            if_modified_since, cached_resp = self._cache[url]
            new_headers["If-Modified-Since"] = if_modified_since
        except KeyError:
            cached_resp = None
            pass

        resp = super().get(url, headers=new_headers)

        if resp.status_code == 304 and cached_resp is not None:
            return cached_resp

        # Note that an HTTP 304 will cause this to throw, so we need to
        # do this *after* we look for an entry in the cache.
        resp.raise_for_status()

        now = datetime.datetime.now(datetime.UTC)
        self._cache[url] = (now.strftime("%a, %d %b %Y %H:%M:%S %Z"), resp)

        return resp


client = CachingClient()


class RssEntry(typing.TypedDict):
    id: str
    date_posted: datetime.datetime
    title: str
    url: str


def fetch_rss_feed_entries() -> Iterator[RssEntry]:
    """
    Returns recent entries from the RSS feed for my main website.
    """
    resp = client.get_with_caching("https://alexwlchan.net/atom.xml")

    feed = feedparser.parse(resp.text)

    for e in feed["entries"]:
        url = e["id"]

        if not url.endswith("/"):
            url += "/"

        yield {
            "id": e["id"],
            "date_posted": datetime.datetime.fromisoformat(e["published"]),
            "title": e["title"],
            "url": url,
        }


class NetlifyBandwidthUsage(typing.TypedDict):
    used: int
    included: int
    period_start_date: datetime.datetime
    period_end_date: datetime.datetime


def fetch_netlify_bandwidth_usage() -> NetlifyBandwidthUsage:
    """
    Look up my Netlify bandwidth usage from the API.

    See https://alexwlchan.net/til/2024/get-netlify-usage-from-api/
    """
    team_slug = get_password("netlify", "team_slug")
    analytics_token = get_password("netlify", "analytics_token")

    resp = client.get_with_caching(
        url=f"https://api.netlify.com/api/v1/accounts/{team_slug}/bandwidth",
        headers={"Authorization": f"Bearer {analytics_token}"},
    )

    data = resp.json()

    return {
        "used": data["used"],
        "included": data["included"],
        "period_start_date": datetime.datetime.fromisoformat(data["period_start_date"]),
        "period_end_date": datetime.datetime.fromisoformat(data["period_end_date"]),
    }
