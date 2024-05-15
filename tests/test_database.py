import datetime
import random
import typing

import pytest
from sqlite_utils import Database
from sqlite_utils.db import Table

from analytics.database import AnalyticsDatabase
from analytics.types import PerDayCount


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
) -> None:
    db = Database(":memory:")
    analytics_db = AnalyticsDatabase(db)

    requests = {"2001-01-01": 10, "2001-01-02": 15, "2001-01-04": 17, "2001-01-05": 16}

    for day, visitor_count in requests.items():
        for visitor_id in range(visitor_count):
            for i in range(random.randint(1, 10)):
                Table(db, "events").insert(
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
) -> None:
    db = Database(":memory:")
    analytics_db = AnalyticsDatabase(db)

    requests: dict[str, dict[str | None, int]] = {
        "2001-01-01": {"US": 10, "GB": 5},
        "2001-01-02": {"US": 3, "GB": 4, "DE": 2},
        "2001-01-04": {"GB": 7, None: 3},
        "2001-01-05": {"US": 8, "FI": 6},
    }

    for day, country_info in requests.items():
        for country_id, count in country_info.items():
            for _ in range(count):
                Table(db, "events").insert(
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


class DummyRecord(typing.TypedDict):
    title: str
    path: str
    normalised_referrer: str
    count: int


records: list[DummyRecord] = [
    {
        "title": "Making a PDF that’s larger than Germany – alexwlchan",
        "path": "/2024/big-pdf/",
        "normalised_referrer": "YouTube",
        "count": 5,
    },
    {
        "title": "Making a PDF that’s larger than Germany – alexwlchan",
        "path": "/2024/big-pdf/",
        "normalised_referrer": "https://example.com/",
        "count": 1,
    },
    {
        "title": "Making a PDF that’s larger than Germany – alexwlchan",
        "path": "/2024/big-pdf/",
        "normalised_referrer": "https://buttondown.email/",
        "count": 1,
    },
    {
        "title": "alexwlchan",
        "path": "/",
        "normalised_referrer": "https://buttondown.email/",
        "count": 2,
    },
    {
        "title": "Making a PDF that’s larger than Germany – alexwlchan",
        "path": "/2024/big-pdf/",
        "normalised_referrer": "https://gigazine.net/",
        "count": 1,
    },
]


class TestAnalyticsDatabase:
    def test_count_referrers_gets_all_germany_posts(self) -> None:
        db = Database(":memory:")
        analytics_db = AnalyticsDatabase(db)

        for row in records:
            for _ in range(row["count"]):
                Table(db, "events").insert(
                    {
                        **row,
                        "is_me": False,
                        "host": "alexwlchan.net",
                        "date": datetime.date(2024, 3, 29).isoformat(),
                    }
                )

        result = analytics_db.count_referrers(
            start_date=datetime.date(2024, 3, 28), end_date=datetime.date(2024, 4, 26)
        )

        assert result == {
            "grouped_referrers": [
                (
                    "YouTube",
                    {"Making a PDF that’s larger than Germany – alexwlchan": 5},
                ),
                (
                    "https://buttondown.email/",
                    {
                        "alexwlchan": 2,
                        "Making a PDF that’s larger than Germany – alexwlchan": 1,
                    },
                ),
            ],
            "long_tail": {
                "Making a PDF that’s larger than Germany – alexwlchan": {
                    "https://example.com/": 1,
                    "https://gigazine.net/": 1,
                }
            },
        }

    def test_count_hits_per_page(self) -> None:
        db = Database(":memory:")
        analytics_db = AnalyticsDatabase(db)

        for row in records:
            for _ in range(row["count"]):
                Table(db, "events").insert(
                    {
                        **row,
                        "is_me": False,
                        "host": "alexwlchan.net",
                        "date": datetime.date(2024, 3, 29).isoformat(),
                    }
                )

        result = analytics_db.count_hits_per_page(
            start_date=datetime.date(2024, 3, 28),
            end_date=datetime.date(2024, 4, 26),
            limit=10,
        )

        assert result == [
            {
                "count": 8,
                "host": "alexwlchan.net",
                "path": "/2024/big-pdf/",
                "title": "Making a PDF that’s larger than Germany – alexwlchan",
            },
            {"count": 2, "host": "alexwlchan.net", "path": "/", "title": "alexwlchan"},
        ]

    def test_count_missing_pages(self) -> None:
        db = Database(":memory:")
        analytics_db = AnalyticsDatabase(db)

        for row in records:
            for _ in range(row["count"]):
                Table(db, "events").insert(
                    {
                        **row,
                        "is_me": False,
                        "host": "alexwlchan.net",
                        "date": datetime.date(2024, 3, 29).isoformat(),
                    }
                )

        for path, count in [("/404", 2), ("/not-found", 5), ("/files/2021/null", 1)]:
            for _ in range(count):
                Table(db, "events").insert(
                    {
                        "title": "404 Not Found – alexwlchan",
                        "path": path,
                        "is_me": False,
                        "host": "alexwlchan.net",
                        "date": datetime.date(2024, 3, 29).isoformat(),
                    }
                )

        result = analytics_db.count_missing_pages(
            start_date=datetime.date(2024, 3, 28),
            end_date=datetime.date(2024, 4, 26),
        )

        assert result == [
            {"path": "/not-found", "count": 5},
            {"path": "/404", "count": 2},
        ]
