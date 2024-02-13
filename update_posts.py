"""
Update the database with my most recent posts.
"""

import datetime

import feedparser
import httpx

from utils import get_database


if __name__ == "__main__":
    db = get_database("requests.sqlite")

    resp = httpx.get("https://alexwlchan.net/atom.xml")
    resp.raise_for_status()

    feed = feedparser.parse(resp.text)

    for e in feed["entries"]:
        url = e["links"][0]["href"]

        if not url.endswith("/"):
            url += "/"

        db["posts"].upsert(
            {
                "id": e["id"],
                "date_posted": datetime.datetime.fromisoformat(e["published"]),
                "title": e["title"],
                "url": url,
            },
            pk="id",
        )
