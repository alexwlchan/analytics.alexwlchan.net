"""
Update the database with the latest definitions of get_normalised_referrer().
"""

import functools
import json

import tqdm

from analytics.referrers import get_normalised_referrer, QueryParams
from analytics.utils import get_database


@functools.cache
def parse_query(qs: str) -> QueryParams:
    return tuple(tuple(q) for q in json.loads(qs))


def get_events_to_upsert(db):
    cursor = db["events"].rows_where(
        "referrer != '' or query != '[]'", select="id, referrer, normalised_referrer, query"
    )
    total = db["events"].count_where("referrer != '' or query != '[]'")

    for row in tqdm.tqdm(cursor, total=total):
        normalised_referrer = get_normalised_referrer(
            referrer=row["referrer"],
            query=parse_query(row["query"]),
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
