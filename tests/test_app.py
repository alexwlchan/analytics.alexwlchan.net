import datetime
import random

from flask.testing import FlaskClient
import pytest
from sqlite_utils import Database
from sqlite_utils.db import Table

from analytics.app import AnalyticsDatabase, PerDayCount
from analytics.utils import get_database


def test_index_explains_domain(client: FlaskClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"This website hosts a tracking pixel for alexwlchan.net" in resp.data


def test_index_redirects_if_cookie(client: FlaskClient) -> None:
    client.set_cookie("analytics.alexwlchan-isMe", "true")

    resp = client.get("/")
    assert resp.status_code == 302
    assert resp.headers["location"] == "/dashboard/"


class TestTrackingPixel:
    @pytest.mark.parametrize(
        "query_string",
        [
            {},
            {"url": "example.com", "referrer": "anotherexample.net"},
            {"referrer": "anotherexample.net", "title": "example page"},
            {"title": "example page", "url": "example.com"},
        ],
    )
    def test_missing_mandatory_parameter_is_error(
        self, client: FlaskClient, query_string: dict[str, str]
    ) -> None:
        resp = client.get("/a.gif", query_string=query_string)
        assert resp.status_code == 400

    @pytest.mark.filterwarnings("ignore::ResourceWarning")
    def test_records_single_event(self, client: FlaskClient) -> None:
        resp = client.get(
            "/a.gif",
            query_string={
                "url": "https://alexwlchan.net/",
                "title": "alexwlchan",
                "referrer": "",
            },
            headers={"X-Real-IP": "1.2.3.4"},
        )

        assert resp.status_code == 200

        db = get_database("requests.sqlite")
        assert Table(db, "events").count == 1

    @pytest.mark.filterwarnings("ignore::ResourceWarning")
    def test_utm_source_mastodon(self, client: FlaskClient) -> None:
        resp = client.get(
            "/a.gif",
            query_string={
                "url": "https://alexwlchan.net/?utm_source=mastodon",
                "title": "alexwlchan",
                "referrer": "",
            },
            headers={"X-Real-IP": "1.2.3.4"},
        )

        assert resp.status_code == 200

        db = get_database("requests.sqlite")
        assert Table(db, "events").count == 1
        row = next(Table(db, "events").rows)
        assert row["normalised_referrer"] == "Mastodon"


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
) -> None:
    db = Database(":memory:")
    analytics_db = AnalyticsDatabase(db)

    requests = {"2001-01-01": 10, "2001-01-02": 15, "2001-01-04": 17, "2001-01-05": 16}

    for day, count in requests.items():
        for i in range(count):
            Table(db, "events").insert(
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

    requests = {
        "2001-01-01": {"US": 10, "GB": 5},
        "2001-01-02": {"US": 3, "GB": 4, "DE": 2},
        "2001-01-04": {"GB": 7},
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


@pytest.mark.filterwarnings("ignore::ResourceWarning")
def test_robots_txt(client: FlaskClient) -> None:
    resp = client.get("/robots.txt")
    assert resp.status_code == 200
    assert resp.data.splitlines() == [b"User-agent: *", b"Disallow: /"]


class TestAnalyticsDatabase:
    def test_count_referrers_gets_all_germany_posts(self) -> None:
        db = Database(":memory:")
        analytics_db = AnalyticsDatabase(db)

        records = [
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

        for row in records:
            for _ in range(row["count"]):
                db["events"].insert(
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
