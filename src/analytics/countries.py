import functools
import pathlib
import typing

import maxminddb
import pycountry


@functools.lru_cache
def get_country_iso_code(
    maxmind_db_path: pathlib.Path, *, ip_address: str
) -> str | None:
    """
    Guess the country where this IP address is located.

    Returns the 2-digit ISO country code, or None if the IP address cannot
    be geolocated.

        >>> country_iso_code('52.85.118.55')
        'US'

        >>> country_iso_code('127.0.0.1')
        None

    """
    with maxminddb.open_database(maxmind_db_path) as reader:
        result = reader.get(ip_address)

    if isinstance(result, dict) and isinstance(result["country"], dict):
        return typing.cast(str, result["country"]["iso_code"])

    return None


def get_flag_emoji(country_id: str) -> str:
    """
    Given a 2-digit ISO country code from ``get_country_iso_code()``,
    return a flag for that country.
    """
    code_point_start = ord("🇦") - ord("A")
    assert code_point_start == 127397

    code_points = [code_point_start + ord(char) for char in country_id]
    return "".join(chr(cp) for cp in code_points)


def get_country_name(country_id: str | None) -> str:
    """
    Given a 2-digit ISO country code from ``get_country_iso_code()``,
    return the name of the country.
    """
    if country_id is None:
        return "<unknown>"

    override_names = {
        "BN": "Brunei",
        "BO": "Bolivia",
        "CD": "Democratic Republic of the Congo",
        "GB": "UK",
        "IR": "Iran",
        "KR": "South Korea",
        "MD": "Moldova",
        "PS": "Palestine",
        "RU": "Russia",
        "SY": "Syria",
        "TW": "Taiwan",
        "TZ": "Tanzania",
        "US": "USA",
        "VE": "Venezuela",
    }

    try:
        return override_names[country_id]
    except KeyError:
        pass

    c = pycountry.countries.get(alpha_2=country_id)

    if c is not None:
        country_name: str = c.name
        return country_name
    else:
        return country_id
