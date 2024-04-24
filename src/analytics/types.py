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
