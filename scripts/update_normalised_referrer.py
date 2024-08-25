"""
Update the database with the latest definitions of get_normalised_referrer().
"""

import functools
import json

from sqlite_utils import Database
import tqdm

from analytics.referrers import get_normalised_referrer, QueryParams


@functools.cache
def parse_query(qs: str) -> QueryParams:
    """
    Given a JSON-formatted query string stored in the database,
    turn it back into a proper ``QueryParams`` value.
    """
    return tuple(tuple(q) for q in json.loads(qs))


def get_events_to_upsert(db):
    """
    Find events in the database whose ``normalised_referrer`` is outdated.
    """
    cursor = db["events"].rows_where(
        "referrer != '' or query != '[]'",
        select="id, referrer, normalised_referrer, query",
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
    db = Database("requests.sqlite")

    events = list(get_events_to_upsert(db))

    db["events"].upsert_all(events, pk="id")
