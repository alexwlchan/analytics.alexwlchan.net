import functools
import hashlib
import os
import secrets
import sqlite3
import time
import uuid

import maxminddb
from sqlite_utils import Database
from sqlite_utils.db import NotFoundError


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
    with maxminddb.open_database(
        "GeoLite2-Country_20240116/GeoLite2-Country.mmdb"
    ) as reader:
        result = reader.get(ip_address)

    try:
        return result["country"]["iso_code"]
    except TypeError:
        if result is None:
            return None
        else:
            raise


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


SALT = os.environ.get('SESSION_ID_SALT', secrets.token_hex())
ONE_HOUR = 60 * 60


def get_session_identifier(db: Database, ip_address: str, user_agent: str) -> str:
    """
    Create a session identifier. This is a UUID that can be used
    to correlate requests within a single session.

    This identifiers are anonymous and only last for eight hours -- after
    that, the session gets a new identifier.
    """
    # How it works:
    #
    #   1.  Create a salted hash of the IP address and user agent.
    #       The salt isn't saved anywhere, so these hashes should
    #       be basically impossible to reverse.
    #
    #   2.  Look in the database table of session identifiers, which is
    #       keyed by this salted hash.
    #
    #       If there's a session ID that hasn't expired, return that.
    #       If there's a session ID that's expired, delete it.
    #
    #   3.  If there is no session ID or the existing ID has expired,
    #       create a new one, and record it in the database.
    #
    raw_id = f"{ip_address}--{user_agent}".encode("utf8")
    hash_id = hashlib.sha256(f"{SALT}--{raw_id}").hexdigest()

    try:
        existing_row = db["session_identifiers"].get(hash_id)
    except NotFoundError:
        pass
    else:
        if existing_row['expires'] >= time.monotonic():
            return existing_row['session_id']
        else:
            db['session_identifiers'].delete(hash_id)

    session_id = uuid.uuid4()
    expires = time.monotonic() + 8 * ONE_HOUR

    db["session_identifiers"].insert(
        {"hash_id": hash_id, "session_id": session_id, "expires": expires},
    )

    return session_id
