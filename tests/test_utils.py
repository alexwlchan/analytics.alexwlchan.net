import pytest

from analytics.utils import get_country_iso_code


@pytest.mark.parametrize(
    ["ip_address", "country_code"], [("1.1.1.1", "EXAMPLE"), ("127.0.0.1", None)]
)
def test_get_country_iso_code(
    maxmind_database: None, ip_address: str, country_code: str | None
) -> None:
    assert get_country_iso_code(ip_address) == country_code
