"""
Tools for working with country data -- in particular, the countries where
my visitors come from.

I look up the country of each visitor based on their IP address, using
an offline MaxMind database with an (IP) -> (country) mapping.  Then I
display the tally of countries on a world map later.

This approach means:

*   All the location lookups can happen locally; I'm not e.g. sending visitor
    IP addresses to a third-party service for the lookup
*   I can discard the original IP address and just store the country,
    which is broad enough not to be a privacy issue

"""

import functools
import glob
import pathlib
import typing

import maxminddb
import pycountry


def maxmind_db_path() -> pathlib.Path:
    """
    Return the path to the MaxMind database.

    This assumes that there will be one or more folders in the working
    directory like ``GeoLite2-Country_*``, and within those folders will
    be a database named ``GeoLite2-Country.mmdb``.

    This is the naming convention used in the packages I download
    from MaxMind.
    """
    # TODO: Should this be a config option?
    db_folder = max(glob.glob("GeoLite2-Country_*"))
    db_path = pathlib.Path(db_folder) / "GeoLite2-Country.mmdb"
    return db_path


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
