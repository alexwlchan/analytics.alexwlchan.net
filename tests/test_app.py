"""
Tests for the main Flask app.
"""

from flask.testing import FlaskClient
import pytest
from sqlite_utils.db import Table

from analytics.utils import get_database


def test_index_explains_domain(client: FlaskClient) -> None:
    """
    There's explanatory text at the root of the domain.
    """
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"This website hosts a tracking pixel for alexwlchan.net" in resp.data


def test_index_redirects_if_cookie(client: FlaskClient) -> None:
    """
    If you have the ``isMe`` cookie, you're automatically redirected
    from the homepage to the dashboard.
    """
    client.set_cookie("analytics.alexwlchan-isMe", "true")

    resp = client.get("/")
    assert resp.status_code == 302
    assert resp.headers["location"] == "/dashboard/"


class TestTrackingPixel:
    """
    Tests for the tracking pixel at ``/a.gif``
    """

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
        """
        If you omit one of the parameters, you get an HTTP 400 error.
        """
        resp = client.get("/a.gif", query_string=query_string)
        assert resp.status_code == 400

    @pytest.mark.filterwarnings("ignore::ResourceWarning")
    def test_records_single_event(self, client: FlaskClient) -> None:
        """
        If you pass the right parameters, an event gets recorded in
        the database.
        """
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
        """
        If your User-Agent looks like a bot, the recorded event has
        ``is_bot=1``.
        """
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
        """
        If the query parameter has a ``utm_source``, this is reflected
        in the ``normalised_referrer``.
        """
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
    """
    The ``/robots.txt`` page tells robots to ignore this domain.
    """
    resp = client.get("/robots.txt")
    assert resp.status_code == 200
    assert resp.data.splitlines() == [b"User-agent: *", b"Disallow: /"]


@pytest.mark.filterwarnings("ignore::ResourceWarning")
@pytest.mark.vcr()
def test_dashboard_can_be_rendered(client: FlaskClient) -> None:
    """
    The dashboard can be shown.

    This is a fairly minimal test that's just designed to get coverage
    for this code, but doesn't test any specific behaviours.  In future,
    it'd be nice to expand this and add tests that are more interesting
    than just "the dashboard loads okay".
    """
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

    # Manually insert a country code so it renders the shaded colours on the world map
    db = get_database("requests.sqlite")
    first_id = next(Table(db, "events").rows)["id"]
    Table(db, "events").upsert({"id": first_id, "country": "US"}, pk="id")

    dashboard_resp = client.get("/dashboard/")
    assert dashboard_resp.status_code == 200

    dashboard_resp = client.get("/dashboard/?startDate=2024-07-06")
    assert dashboard_resp.status_code == 200

    dashboard_resp = client.get("/dashboard/?endDate=2024-07-06")
    assert dashboard_resp.status_code == 200
