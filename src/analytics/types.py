import datetime
import typing


class MissingPage(typing.TypedDict):
    path: str
    count: int


class RecentPost(typing.TypedDict):
    url: str
    title: str
    date_posted: datetime.datetime
    count: int


class CountedReferrers(typing.TypedDict):
    # (referrer, dict(page -> count))
    grouped_referrers: list[tuple[str, dict[str, int]]]

    # (page, dict(referrer -> count))
    long_tail: dict[str, dict[str, int]]
