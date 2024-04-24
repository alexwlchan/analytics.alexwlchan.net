import os
import pathlib

from netaddr import IPSet
from mmdb_writer import MMDBWriter
import pytest

from analytics.utils import get_country_iso_code


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


@pytest.mark.parametrize(
    ["ip_address", "country_code"], [("1.1.1.1", "EXAMPLE"), ("127.0.0.1", None)]
)
def test_get_country_iso_code(
    maxmind_database: None, ip_address: str, country_code: str | None
) -> None:
    assert get_country_iso_code(ip_address) == country_code
