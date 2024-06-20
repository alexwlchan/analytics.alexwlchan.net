from collections.abc import Iterator
import datetime


def now() -> datetime.datetime:
    """
    Return the current time as a UTC timestamp.
    """
    return datetime.datetime.now(tz=datetime.UTC)


def yesterday() -> datetime.date:
    """
    Return yesterday's date.
    """
    return datetime.date.today() - datetime.timedelta(days=1)


def days_between(
    start_date: datetime.date, end_date: datetime.date
) -> Iterator[datetime.date]:
    """
    Generate all the days between two dates, including the dates
    themselves.
    """
    d = start_date

    while d <= end_date:
        yield d
        d += datetime.timedelta(days=1)


def prettydate(d: str) -> str:
    return datetime.datetime.strptime(d, "%Y-%m-%d").strftime("%a %-d %b")
