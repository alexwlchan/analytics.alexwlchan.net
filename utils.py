import datetime
import functools
import glob
import sqlite3
import sys
import uuid

import hyperlink
import maxminddb
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

    if result is None:
        return None
    else:
        return result["country"]["iso_code"]


def get_database(path: str) -> Database:
    """
    Create a SQLite database with the necessary tables.
    """
    # Check we can use SQLite safely across multiple threads.
    #
    # See https://ricardoanderegg.com/posts/python-sqlite-thread-safety/
    assert sqlite3.threadsafety == 3
    con = sqlite3.connect(path, check_same_thread=False)

    with open("schema.sql") as f:
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
    return uuid.uuid4()


def guess_if_bot(user_agent: str) -> bool:
    """
    Guess whether a particular User-Agent string is a bot/crawler.
    """
    for word in ("bot", "spider", "crawler"):
        if word in user_agent.lower():
            return True

    return False


def normalise_referrer(referrer: str | None) -> str | None:
    """
    If possible, create a "normalised form" of a referrer.
    """
    if referrer is None:
        return None

    search_catchall = "Search (Google, Bing, DDG, …)"

    exact_matches = {
        "android-app://com.google.android.googlequicksearchbox/": search_catchall,
        "https://news.ycombinator.com/": "Hacker News",
        "https://t.co/": "Twitter",
        "https://www.bing.com/": search_catchall,
        "https://www.reddit.com/": "Reddit",
        "https://duckduckgo.com/": search_catchall,
        "https://search.brave.com/": search_catchall,
        "https://www.startpage.com/": search_catchall,
        "https://yandex.ru/": search_catchall,
    }

    try:
        return exact_matches[referrer]
    except KeyError:
        pass

    try:
        u = hyperlink.DecodedURL.from_text(referrer)
    except Exception as e:
        print(f"Unable to parse {referrer}: {e}", file=sys.stderr)
        return None

    if u.host.startswith("www.google."):
        return search_catchall

    if u.host == "facebook.com" or u.host.endswith(".facebook.com"):
        return "Facebook"

    if "alexwlchan.net" in u.host or "localhost" in u.host:
        return None

    return referrer
