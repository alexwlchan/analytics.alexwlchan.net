import pytest

from analytics.utils import get_country_iso_code


@pytest.mark.skip("Country DBs aren't currently available in CI")
@pytest.mark.parametrize(
    ["ip_address", "country_code"],
    [
        ("52.85.118.55", "US"),
        ("127.0.0.1", None),
    ],
)
def test_get_country_iso_code(ip_address: str, country_code: str | None) -> None:
    assert get_country_iso_code(ip_address) == country_code
