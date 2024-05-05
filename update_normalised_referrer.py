"""
Update the database with the latest definitions of get_normalised_referrer().
"""

import json

import tqdm

from analytics.referrers import get_normalised_referrer
from analytics.utils import get_database


def get_events_to_upsert(db):
    for row in tqdm.tqdm(db["events"].rows, total=db["events"].count):
        normalised_referrer = get_normalised_referrer(
            referrer=row["referrer"],
            query=tuple(tuple(q) for q in json.loads(row["query"])),
        )

        if normalised_referrer != row["normalised_referrer"]:
            yield {
                "id": row["id"],
                "normalised_referrer": normalised_referrer,
            }


if __name__ == "__main__":

    db = get_database(path="requests.sqlite")

    events = list(get_events_to_upsert(db))

    db["events"].upsert_all(events, pk="id")
