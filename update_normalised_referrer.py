"""
Update the database with the latest definitions of normalise_referrer().
"""

from referrers import normalise_referrer
from utils import get_database

db = get_database(path="requests.sqlite")

for row in db["events"].rows:
    if (
        json.loads(row["query"]) == [["utm_source", "mastodon"]]
        and row["normalised_referrer"] != "Mastodon"
    ):
        db["events"].upsert(
            {
                "id": row["id"],
                "normalised_referrer": "Mastodon",
            },
            pk="id",
        )
        continue

    if row["normalised_referrer"] != normalise_referrer(row["referrer"]):
        db["events"].upsert(
            {
                "id": row["id"],
                "normalised_referrer": normalise_referrer(row["referrer"]),
            },
            pk="id",
        )
