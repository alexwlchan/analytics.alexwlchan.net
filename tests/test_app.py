import datetime
import random

import pytest
from sqlite_utils import Database

from app import AnalyticsDatabase, PerDayCount


@pytest.fixture
def analytics_db() -> AnalyticsDatabase:
    return AnalyticsDatabase(db=Database(":memory:"))


@pytest.mark.parametrize(
    ["start_date", "end_date", "expected_result"],
    [
        ("2001-01-01", "2001-01-01", [{"day": "2001-01-01", "count": 10}]),
        (
            "2001-01-01",
            "2001-01-02",
            [{"day": "2001-01-01", "count": 10}, {"day": "2001-01-02", "count": 15}],
        ),
        (
            "2001-01-02",
            "2001-01-04",
            [
                {"day": "2001-01-02", "count": 15},
                {"day": "2001-01-03", "count": 0},
                {"day": "2001-01-04", "count": 17},
            ],
        ),
    ],
)
def test_count_requests_per_day(
    start_date: str, end_date: str, expected_result: list[PerDayCount]
):
    db = Database(":memory:")
    analytics_db = AnalyticsDatabase(db)

    requests = {"2001-01-01": 10, "2001-01-02": 15, "2001-01-04": 17, "2001-01-05": 16}

    for day, count in requests.items():
        for i in range(count):
            db["events"].insert(
                {"date": day + "T01:23:45Z", "is_me": False, "host": "alexwlchan.net"}
            )

    actual = analytics_db.count_requests_per_day(
        start_date=datetime.date.fromisoformat(start_date),
        end_date=datetime.date.fromisoformat(end_date),
    )
    assert actual == expected_result


@pytest.mark.parametrize(
    ["start_date", "end_date", "expected_result"],
    [
        ("2001-01-01", "2001-01-01", [{"day": "2001-01-01", "count": 10}]),
        (
            "2001-01-01",
            "2001-01-02",
            [{"day": "2001-01-01", "count": 10}, {"day": "2001-01-02", "count": 15}],
        ),
        (
            "2001-01-02",
            "2001-01-04",
            [
                {"day": "2001-01-02", "count": 15},
                {"day": "2001-01-03", "count": 0},
                {"day": "2001-01-04", "count": 17},
            ],
        ),
    ],
)
def test_count_unique_visitors_per_day(
    start_date: str, end_date: str, expected_result: list[PerDayCount]
):
    db = Database(":memory:")
    analytics_db = AnalyticsDatabase(db)

    requests = {"2001-01-01": 10, "2001-01-02": 15, "2001-01-04": 17, "2001-01-05": 16}

    for day, visitor_count in requests.items():
        for visitor_id in range(visitor_count):
            for i in range(random.randint(1, 10)):
                db["events"].insert(
                    {
                        "date": day + "T01:23:45Z",
                        "session_id": visitor_id,
                        "is_me": False,
                        "host": "alexwlchan.net",
                    }
                )

    actual = analytics_db.count_unique_visitors_per_day(
        start_date=datetime.date.fromisoformat(start_date),
        end_date=datetime.date.fromisoformat(end_date),
    )
    assert actual == expected_result


@pytest.mark.parametrize(
    ["start_date", "end_date", "expected_result"],
    [
        ("2001-01-01", "2001-01-01", {"US": 10, "GB": 5}),
        ("2001-01-01", "2001-01-02", {"US": 13, "GB": 9, "DE": 2}),
        ("2001-01-02", "2001-01-04", {"US": 3, "GB": 11, "DE": 2}),
        ("2001-01-03", "2001-01-05", {"US": 8, "GB": 7, "FI": 6}),
        ("2001-01-05", "2001-01-05", {"US": 8, "FI": 6}),
        ("2010-01-05", "2010-01-05", {}),
    ],
)
def test_count_visitors_by_country(
    start_date: str, end_date: str, expected_result: dict[str, int]
):
    db = Database(":memory:")
    analytics_db = AnalyticsDatabase(db)

    requests = {
        "2001-01-01": {"US": 10, "GB": 5},
        "2001-01-02": {"US": 3, "GB": 4, "DE": 2},
        "2001-01-04": {"GB": 7},
        "2001-01-05": {"US": 8, "FI": 6},
    }

    for day, country_info in requests.items():
        for country_id, count in country_info.items():
            for _ in range(count):
                db["events"].insert(
                    {
                        "date": day + "T01:23:45Z",
                        "country": country_id,
                        "is_me": False,
                        "host": "alexwlchan.net",
                    }
                )

    actual = analytics_db.count_visitors_by_country(
        start_date=datetime.date.fromisoformat(start_date),
        end_date=datetime.date.fromisoformat(end_date),
    )
    assert actual == expected_result
