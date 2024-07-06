from collections.abc import Iterator
import os
import pathlib

from flask.testing import FlaskClient
from netaddr import IPSet
from mmdb_writer import MMDBWriter
import pytest


@pytest.fixture()
def client(maxmind_db_path: pathlib.Path) -> Iterator[FlaskClient]:
    """
    Creates an instance of the app for use in testing.

    See https://flask.palletsprojects.com/en/3.0.x/testing/#fixtures
    """
    from analytics import app

    app.config["TESTING"] = True

    # Reset to prevent this leaking between tests
    if "DATABASE" in app.config:
        del app.config["DATABASE"]

    with app.test_client() as client:
        yield client


@pytest.fixture
def maxmind_db_path(tmp_path: pathlib.Path) -> pathlib.Path:
    """
    Create a MaxMind database with the right name in the current directory.

    This is based on the example code for mmdb_writer.
    See https://pypi.org/project/mmdb-writer/
    """
    os.chdir(tmp_path)
    os.makedirs(tmp_path / "GeoLite2-Country_TEST")

    writer = MMDBWriter()

    writer.insert_network(
        IPSet(["1.1.0.0/24", "1.1.1.0/24"]), {"country": {"iso_code": "EXAMPLE"}}
    )

    db_path = tmp_path / "GeoLite2-Country_TEST" / "GeoLite2-Country.mmdb"
    writer.to_db_file(db_path)
    return db_path
