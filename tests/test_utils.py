import pytest

from analytics.utils import get_country_iso_code, get_country_name, get_flag_emoji


@pytest.mark.parametrize(
    ["ip_address", "country_code"], [("1.1.1.1", "EXAMPLE"), ("127.0.0.1", None)]
)
def test_get_country_iso_code(
    maxmind_database: None, ip_address: str, country_code: str | None
) -> None:
    assert get_country_iso_code(ip_address) == country_code


@pytest.mark.parametrize(
    ["country_id", "country_name"],
    [
        ("US", "USA"),
        ("GB", "UK"),
        ("RU", "Russia"),
        ("CN", "China"),
        ("XK", "XK"),
        (None, "<unknown>"),
    ],
)
def test_get_country_name(country_id: str | None, country_name: str) -> None:
    assert get_country_name(country_id) == country_name


@pytest.mark.parametrize(["country_id", "emoji"], [("US", "🇺🇸")])
def test_get_flag_emoji(country_id: str, emoji: str) -> None:
    assert get_flag_emoji(country_id) == emoji
