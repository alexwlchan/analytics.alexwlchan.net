import datetime
import functools
import glob
import math
import os
import pathlib
import sqlite3
import typing
import uuid

import keyring
import maxminddb
import pycountry
from sqlite_utils import Database


@functools.lru_cache
def get_country_iso_code(ip_address: str) -> str | None:
    """
    Guess the country where this IP address is located.

    Returns the 2-digit ISO country code, or None if the IP address cannot
    be geolocated.

        >>> country_iso_code('52.85.118.55')
        'US'

        >>> country_iso_code('127.0.0.1')
        None

    """
    db_folder = max(glob.glob("GeoLite2-Country_*"))

    with maxminddb.open_database(f"{db_folder}/GeoLite2-Country.mmdb") as reader:
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

    if country_id == "US":
        return "USA"

    if country_id == "GB":
        return "UK"

    if country_id == "RU":
        return "Russia"

    c = pycountry.countries.get(alpha_2=country_id)

    if c is not None:
        country_name: str = c.name
        return country_name
    else:
        return country_id


def get_database(path: str) -> Database:
    """
    Create a SQLite database with the necessary tables.
    """
    # Check we can use SQLite safely across multiple threads.
    #
    # See https://ricardoanderegg.com/posts/python-sqlite-thread-safety/
    assert sqlite3.threadsafety == 3
    con = sqlite3.connect(path, check_same_thread=False)

    this_file = pathlib.Path(os.path.abspath(__file__))

    with open(this_file.parent / "schema.sql") as f:
        schema = f.read()
        con.executescript(schema)

    db = Database(con)

    return db


# 100,000 unique visitors a day is way more than I usually get,
# so this is plenty big enough!
@functools.lru_cache(maxsize=100000)
def get_session_identifier(d: datetime.date, ip_address: str, user_agent: str) -> str:
    """
    Create a session identifier. This is a UUID that can be used
    to correlate requests within a single session.

    This identifiers are anonymous and only last for a single day -- after
    that, the session gets a new identifier.
    """
    return str(uuid.uuid4())


def guess_if_bot(user_agent: str) -> bool:
    """
    Guess whether a particular User-Agent string is a bot/crawler.
    """
    for word in ("bot", "spider", "crawler"):
        if word in user_agent.lower():
            return True

    return False


@functools.cache
def get_password(service_name: str, username: str) -> str:  # pragma: no cover
    """
    Retrieve a password from the system keychain.
    """
    password = keyring.get_password(service_name, username)
    return typing.cast(str, password)


def get_hex_color_between(hex1: str, hex2: str, proportion: float) -> str:
    """
    Interpolate a colour between two hex strings.

    This is used to shade areas on the world map.

    TODO: Is there a better way to do this?
    """
    r1, g1, b1 = int(hex1[1:3], 16), int(hex1[3:5], 16), int(hex1[5:7], 16)
    r2, g2, b2 = int(hex2[1:3], 16), int(hex2[3:5], 16), int(hex2[5:7], 16)

    r_new = int(r1 + (r2 - r1) * proportion)
    g_new = int(g1 + (g2 - g1) * proportion)
    b_new = int(b1 + (b2 - b1) * proportion)

    return "#%02x%02x%02x" % (r_new, g_new, b_new)


def get_circular_arc_path_command(
    *,
    centre_x: float,
    centre_y: float,
    radius: float,
    start_angle: float,
    sweep_angle: float,
    angle_unit: typing.Literal["radians", "degrees"],
) -> str:
    """
    Returns a path command to draw a circular arc in an SVG <path> element.

    See https://developer.mozilla.org/en-US/docs/Web/SVG/Tutorial/Paths#line_commands
    See https://alexwlchan.net/2022/circle-party/
    """
    if angle_unit == "radians":
        pass
    elif angle_unit == "degrees":
        start_angle = start_angle / 180 * math.pi
        sweep_angle = sweep_angle / 180 * math.pi
    else:
        raise ValueError(f"Unrecognised angle unit: {angle_unit}")

    # Work out the start/end points of the arc using trig identities
    start_x = centre_x + radius * math.sin(start_angle)
    start_y = centre_y - radius * math.cos(start_angle)

    end_x = centre_x + radius * math.sin(start_angle + sweep_angle)
    end_y = centre_y - radius * math.cos(start_angle + sweep_angle)

    # An arc path in SVG defines an ellipse/curve between two points.
    # The `x_axis_rotation` parameter defines how an ellipse is rotated,
    # if at all, but circles don't change under rotation, so it's irrelevant.
    x_axis_rotation = 0

    # For a given radius, there are two circles that intersect the
    # start/end points.
    #
    # The `sweep-flag` parameter determines whether we move in
    # a positive angle (=clockwise) or negative (=counter-clockwise).
    # I'only doing clockwise sweeps, so this is constant.
    sweep_flag = 1

    # There are now two arcs available: one that's more than 180 degrees,
    # one that's less than 180 degrees (one from each of the two circles).
    # The `large-arc-flag` decides which to pick.
    if sweep_angle > math.pi:
        large_arc_flag = 1
    else:
        large_arc_flag = 0

    return (
        f"M {start_x} {start_y} "
        f"A {radius} {radius} "
        f"{x_axis_rotation} {large_arc_flag} {sweep_flag} {end_x} {end_y}"
    )
