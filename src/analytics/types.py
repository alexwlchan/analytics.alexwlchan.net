"""
Types.

TODO: Merge this into ``database.py``.
"""

import datetime
import typing


class MissingPage(typing.TypedDict):
    """
    A page which wasn't found when the user requested it, i.e. any page
    which returned a 404 Not Found or 410 Gone.
    """

    path: str
    count: int


class RecentPost(typing.TypedDict):
    """
    An article which I posted recently.
    """

    host: str
    path: str
    title: str
    date_posted: datetime.datetime
    count: int


class CountedReferrers(typing.TypedDict):
    """
    A tally of referrers who've sent traffic to my site.
    """

    # (referrer, dict(page -> count))
    grouped_referrers: list[tuple[str, dict[str, int]]]

    # (page, dict(referrer -> count))
    long_tail: dict[str, dict[str, int]]


class PerDayCount(typing.TypedDict):
    """
    Count of hits per day.
    """

    day: str
    count: int


class PerPageCount(typing.TypedDict):
    """
    Count of hits per page.
    """

    host: str
    path: str
    title: str
    count: int
