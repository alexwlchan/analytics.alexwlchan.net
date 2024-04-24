from collections.abc import Iterator
import os
import pathlib

from flask.testing import FlaskClient
from netaddr import IPSet
from mmdb_writer import MMDBWriter
import pytest


@pytest.fixture()
def client(maxmind_database: None) -> Iterator[FlaskClient]:
    """
    Creates an instance of the app for use in testing.

    See https://flask.palletsprojects.com/en/3.0.x/testing/#fixtures
    """
    from analytics import app

    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


@pytest.fixture
def maxmind_database(tmp_path: pathlib.Path) -> None:
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

    writer.to_db_file(tmp_path / "GeoLite2-Country_TEST" / "GeoLite2-Country.mmdb")
