"""
This file has a couple of functions for fetching data from remote sources --
anything that can't come from the local database.
"""

from collections.abc import Iterator
import datetime
import typing
from xml.etree import ElementTree as ET

import httpx
import hyperlink

from .utils import get_password


class RssEntry(typing.TypedDict):
    id: str
    date_posted: datetime.datetime
    title: str
    url: str
    host: str
    path: str


def fetch_rss_feed_entries() -> Iterator[RssEntry]:
    """
    Returns recent entries from the RSS feed for my main website.
    """
    resp = httpx.get("https://alexwlchan.net/atom.xml")
    resp.raise_for_status()

    # Note: ET.fromstring() is not safe against maliciously constructed XML,
    # but this is my RSS feed!  So I trust it.
    xml = ET.fromstring(resp.text)

    for entry in xml.findall("{http://www.w3.org/2005/Atom}entry"):
        url = entry.find("{http://www.w3.org/2005/Atom}id").text

        # See https://github.com/alexwlchan/alexwlchan.net/issues/787
        if not url.endswith("/"):
            url += "/"

        title = entry.find("{http://www.w3.org/2005/Atom}title").text
        date_posted = datetime.datetime.fromisoformat(
            entry.find("{http://www.w3.org/2005/Atom}published").text
        )

        yield {
            "id": url,
            "date_posted": date_posted,
            "title": title,
            "url": url,
            "host": hyperlink.DecodedURL.from_text(url).host,
            "path": "/" + "/".join(hyperlink.DecodedURL.from_text(url).path),
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

    resp = httpx.get(
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
