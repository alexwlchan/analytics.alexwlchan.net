import datetime

from flask.testing import FlaskClient
import pytest
from sqlite_utils import Database
from sqlite_utils.db import Table

from analytics.database import AnalyticsDatabase
from analytics.types import PerDayCount
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
    def test_records_bot_event(self, client: FlaskClient) -> None:
        resp = client.get(
            "/a.gif",
            query_string={
                "url": "https://alexwlchan.net/",
                "title": "alexwlchan",
                "referrer": "",
            },
            headers={"X-Real-IP": "1.2.3.4", "User-Agent": "Googlebot/1.0"},
        )

        assert resp.status_code == 200

        db = get_database("requests.sqlite")
        assert Table(db, "events").count == 1
        row = next(Table(db, "events").rows)
        assert row["is_bot"]

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


@pytest.mark.filterwarnings("ignore::ResourceWarning")
def test_robots_txt(client: FlaskClient) -> None:
    resp = client.get("/robots.txt")
    assert resp.status_code == 200
    assert resp.data.splitlines() == [b"User-agent: *", b"Disallow: /"]
