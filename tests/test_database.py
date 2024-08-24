"""
Tests for ``analytics.database``.
"""

import datetime
import random
import typing

import pytest

from analytics.database import AnalyticsDatabase
from analytics.types import CountedReferrers, PerDayCount


def create_event(
    day: str,
    visitor_id: int = -1,
    country_id: str | None = "GB",
    title: str = "Example post",
    path: str = "/example/",
    normalised_referrer: str = "",
) -> typing.Any:
    """
    Create an example event for testing.
    """
    return {
        "date": day + "T01:23:45Z",
        "session_id": visitor_id,
        "country": country_id,
        "is_me": False,
        "host": "alexwlchan.net",
        "title": title,
        "path": path,
        "normalised_referrer": normalised_referrer,
    }


def create_events(count: int, **kwargs: typing.Any) -> list[typing.Any]:
    """
    Create a list of example events for testing.
    """
    return [create_event(**kwargs) for _ in range(count)]


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
    analytics_db: AnalyticsDatabase,
    start_date: str,
    end_date: str,
    expected_result: list[PerDayCount],
) -> None:
    """
    Tally the number of unique visitors (=session IDs) each day.
    """
    requests = {"2001-01-01": 10, "2001-01-02": 15, "2001-01-04": 17, "2001-01-05": 16}

    for day, visitor_count in requests.items():
        for visitor_id in range(visitor_count):
            analytics_db.events_table.insert_all(
                create_events(
                    day=day, visitor_id=visitor_id, count=random.randint(1, 10)
                )
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
    analytics_db: AnalyticsDatabase,
    start_date: str,
    end_date: str,
    expected_result: dict[str, int],
) -> None:
    """
    Tally the number of visitors from each country.
    """
    requests: dict[str, dict[str | None, int]] = {
        "2001-01-01": {"US": 10, "GB": 5},
        "2001-01-02": {"US": 3, "GB": 4, "DE": 2},
        "2001-01-04": {"GB": 7, None: 3},
        "2001-01-05": {"US": 8, "FI": 6},
    }

    for day, country_info in requests.items():
        for country_id, count in country_info.items():
            analytics_db.events_table.insert_all(
                create_events(day=day, country_id=country_id, count=count)
            )

    actual = analytics_db.count_visitors_by_country(
        start_date=datetime.date.fromisoformat(start_date),
        end_date=datetime.date.fromisoformat(end_date),
    )
    assert actual == expected_result


records: list[typing.Any] = [
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
    """
    Tests for the ``AnalyticsDatabase`` class.
    """

    def test_count_referrers_gets_all_germany_posts(
        self, analytics_db: AnalyticsDatabase
    ) -> None:
        """
        It groups referrers for the "PDF larger than Germany" post, which
        is popular and has a long tail of referrers.
        """
        for row in records:
            analytics_db.events_table.insert_all(
                create_events(
                    day="2024-03-29",
                    title=row["title"],
                    path=row["path"],
                    normalised_referrer=row["normalised_referrer"],
                    count=row["count"],
                )
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

    def test_count_hits_per_page(self, analytics_db: AnalyticsDatabase) -> None:
        """
        Tally the number of htis per page.
        """
        for row in records:
            analytics_db.events_table.insert_all(
                create_events(
                    day="2024-03-29",
                    title=row["title"],
                    path=row["path"],
                    normalised_referrer=row["normalised_referrer"],
                    count=row["count"],
                )
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

    def test_count_missing_pages(self, analytics_db: AnalyticsDatabase) -> None:
        """
        Count the number of pages which got a 404 error.
        """
        for row in records:
            analytics_db.events_table.insert_all(
                create_events(
                    day="2024-03-29",
                    title=row["title"],
                    path=row["path"],
                    normalised_referrer=row["normalised_referrer"],
                    count=row["count"],
                )
            )

        for path, count in [("/404", 2), ("/not-found", 5), ("/files/2021/null", 1)]:
            analytics_db.events_table.insert_all(
                create_events(
                    day="2024-03-29",
                    title="404 Not Found – alexwlchan",
                    path=path,
                    count=count,
                )
            )

        result = analytics_db.count_missing_pages(
            start_date=datetime.date(2024, 3, 28),
            end_date=datetime.date(2024, 4, 26),
        )

        assert result == [
            {"path": "/not-found", "count": 5},
            {"path": "/404", "count": 2},
        ]

    def test_count_referrers_gets_missing_pages(
        self, analytics_db: AnalyticsDatabase
    ) -> None:
        """
        Count the number of pages which got a 404 Not Found or 410 Gone.
        """
        analytics_db.events_table.insert(
            create_event(
                day="2024-05-26",
                title="410 Gone – alexwlchan",
                path="/2019/08/a-post-that-has-been-removed",
                normalised_referrer="example.com",
            )
        )

        analytics_db.events_table.insert_all(
            create_events(
                day="2024-05-26",
                title="404 Not Found – alexwlchan",
                path="/2019/08/a-post-that-never-existed",
                normalised_referrer="example.net",
                count=3,
            )
        )

        result = analytics_db.count_referrers(
            start_date=datetime.date(2024, 5, 25), end_date=datetime.date(2024, 5, 27)
        )

        assert result == typing.cast(
            CountedReferrers,
            {
                "grouped_referrers": [
                    ("example.net", {"/2019/08/a-post-that-never-existed (404)": 3}),
                    ("example.com", {"/2019/08/a-post-that-has-been-removed (410)": 1}),
                ],
                "long_tail": {},
            },
        )

    def test_count_referrers_handles_multiple_pages_in_long_tail(
        self, analytics_db: AnalyticsDatabase
    ) -> None:
        """
        The long tail of popular posts can include multiple posts.
        """
        for title in (
            "Making a PDF that’s larger than Germany – alexwlchan",
            "Documenting my DNS records – alexwlchan",
        ):
            analytics_db.events_table.insert(
                create_event(
                    day="2024-03-29",
                    title=title,
                    path=f"/{title}",
                    normalised_referrer="https://example.com/",
                )
            )

        actual = analytics_db.count_referrers(
            start_date=datetime.date(2024, 3, 28), end_date=datetime.date(2024, 4, 26)
        )

        expected: CountedReferrers = {
            "grouped_referrers": [],
            "long_tail": {
                "Making a PDF that’s larger than Germany – alexwlchan": {
                    "https://example.com/": 1,
                },
                "Documenting my DNS records – alexwlchan": {
                    "https://example.com/": 1,
                },
            },
        }

        assert actual == expected

    @pytest.mark.parametrize(
        ["start_date", "end_date", "expected_result"],
        [
            ("2001-01-01", "2001-01-01", [{"day": "2001-01-01", "count": 10}]),
            (
                "2001-01-01",
                "2001-01-02",
                [
                    {"day": "2001-01-01", "count": 10},
                    {"day": "2001-01-02", "count": 15},
                ],
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
        self,
        analytics_db: AnalyticsDatabase,
        start_date: str,
        end_date: str,
        expected_result: list[PerDayCount],
    ) -> None:
        """
        Tally the total number of requests each day.
        """
        requests = {
            "2001-01-01": 10,
            "2001-01-02": 15,
            "2001-01-04": 17,
            "2001-01-05": 16,
        }

        for day, count in requests.items():
            analytics_db.events_table.insert_all(create_events(day=day, count=count))

        actual = analytics_db.count_requests_per_day(
            start_date=datetime.date.fromisoformat(start_date),
            end_date=datetime.date.fromisoformat(end_date),
        )
        assert actual == expected_result
