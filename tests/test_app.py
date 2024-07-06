import pathlib

from flask.testing import FlaskClient
import pytest
from sqlite_utils.db import Table

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
    def test_records_single_event(
        self, tmp_working_dir: pathlib.Path, client: FlaskClient
    ) -> None:
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
    def test_records_bot_event(
        self, tmp_working_dir: pathlib.Path, client: FlaskClient
    ) -> None:
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
    def test_utm_source_mastodon(
        self, tmp_working_dir: pathlib.Path, client: FlaskClient
    ) -> None:
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


@pytest.mark.filterwarnings("ignore::ResourceWarning")
def test_robots_txt(client: FlaskClient) -> None:
    resp = client.get("/robots.txt")
    assert resp.status_code == 200
    assert resp.data.splitlines() == [b"User-agent: *", b"Disallow: /"]


@pytest.mark.filterwarnings("ignore::ResourceWarning")
@pytest.mark.vcr()
def test_dashboard_can_be_rendered(client: FlaskClient) -> None:
    # VCR cassette note: Netlify returns a ``Retry-After`` header which tells you
    # when you can call the "get bandwidth usage" API again.
    #
    # To avoid this test trying to call it perpetually and creating new requests,
    # I've manually set it to the far future.
    for _ in range(5):
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

    dashboard_resp = client.get("/dashboard/")
    assert dashboard_resp.status_code == 200

    dashboard_resp = client.get("/dashboard/?startDate=2024-07-06")
    assert dashboard_resp.status_code == 200

    dashboard_resp = client.get("/dashboard/?endDate=2024-07-06")
    assert dashboard_resp.status_code == 200
