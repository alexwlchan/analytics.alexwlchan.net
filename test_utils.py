import pytest

from utils import get_country_iso_code, normalise_referrer


@pytest.mark.skip("Country DBs aren't currently available in CI")
@pytest.mark.parametrize(
    ["ip_address", "country_code"],
    [
        ("52.85.118.55", "US"),
        ("127.0.0.1", None),
    ],
)
def test_get_country_iso_code(ip_address, country_code):
    assert get_country_iso_code(ip_address) == country_code


@pytest.mark.parametrize(
    ["referrer", "expected"],
    [
        ("https://www.google.pl/", "Google"),
        ("https://www.google.de/", "Google"),
        ("https://l.facebook.com/", "Facebook"),
        ("android-app://com.google.android.googlequicksearchbox/", "Google"),
        ("https://alexwlchan.net/2014/part-ia-exams/", None),
        ("https://t.co/", "Twitter"),
        (None, None),
        ("https://shkspr.mobi/", "https://shkspr.mobi/"),
    ],
)
def test_normalise_referrer(referrer, expected):
    assert normalise_referrer(referrer) == expected
