import pytest

from utils import get_country_iso_code


@pytest.mark.parametrize(
    ["ip_address", "country_code"],
    [
        ("52.85.118.55", "US"),
        ("127.0.0.1", None),
    ],
)
def test_get_country_iso_code(ip_address, country_code):
    assert get_country_iso_code(ip_address) == country_code
