from collections.abc import Iterator
import datetime
import typing

import feedparser
import httpx
import hyperlink


class RssEntry(typing.TypedDict):
    id: str
    date_posted: datetime.datetime
    title: str
    url: str
    host: str
    path: str


class NoNewEntries(Exception):
    """
    Thrown if there are no new entries in the RSS feed.
    """

    pass


def fetch_rss_feed_entries() -> Iterator[RssEntry]:
    """
    Returns recent entries from the RSS feed for my main website.

    This will throw a ``NoNewEntries`` exception if the RSS feed hasn't
    changed since the last time is was fetched.
    """
    try:
        with open("rss_feed.etag.txt") as etag_file:
            headers = {"If-None-Match": etag_file.read()}
    except (FileNotFoundError, ValueError):
        headers = {}

    resp = httpx.get("https://alexwlchan.net/atom.xml", headers=headers)

    if resp.status_code == 304:
        raise NoNewEntries()

    resp.raise_for_status()
    with open("rss_feed.etag.txt", "w") as out_file:
        out_file.write(resp.headers["etag"])

    feed = feedparser.parse(resp.text)

    for e in feed["entries"]:
        url = e["id"]

        if not url.endswith("/"):
            url += "/"

        post_url = hyperlink.parse(url)

        yield {
            "id": e["id"],
            "date_posted": datetime.datetime.fromisoformat(e["published"]),
            "title": e["title"],
            "url": url,
            "host": post_url.host,
            "path": "/" + "/".join(post_url.path),
        }
