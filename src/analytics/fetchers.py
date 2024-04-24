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


class SingleUrlClient(httpx.Client):
    """
    An HTTP client which will only ever be used to fetch a single URL.

    This does caching of the URL with the If-Modified-Since header
    to get faster responses.
    """

    def __init__(self):
        super().__init__()
        self._cache = {}

    def get(self, url: str):
        resp = super().get(url)

        if resp.status_code == 304:
            try:
                return self._cache[resp.request.url]
            except KeyError:
                return resp

        now = datetime.datetime.now(datetime.UTC)
        self.headers["If-Modified-Since"] = now.strftime("%a, %d %b %Y %H:%M:%S %Z")

        self._cache[resp.request.url] = resp

        return resp


rss_client = SingleUrlClient()


class RssEntry(typing.TypedDict):
    id: str
    date_posted: datetime.datetime
    title: str
    url: str


def fetch_rss_feed_entries() -> Iterator[RssEntry]:
    """
    Returns recent entries from the RSS feed for my main website.
    """
    resp = rss_client.get("https://alexwlchan.net/atom.xml")
    resp.raise_for_status()

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


netlify_client = SingleUrlClient()


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

    resp = netlify_client.get(
        url=f"https://api.netlify.com/api/v1/accounts/{team_slug}/bandwidth",
        headers={"Authorization": f"Bearer {analytics_token}"},
    )
    resp.raise_for_status()

    data = resp.json()

    return {
        "used": data["used"],
        "included": data["included"],
        "period_start_date": datetime.datetime.fromisoformat(data["period_start_date"]),
        "period_end_date": datetime.datetime.fromisoformat(data["period_end_date"]),
    }
