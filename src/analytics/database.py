"""
Database code.

Ideally this file should handle all interactions between the app and
the database.
"""

import collections
import datetime
import pathlib
import typing

from sqlite_utils import Database
from sqlite_utils.db import Table

from .date_helpers import days_between
from .types import CountedReferrers, MissingPage, PerDayCount, PerPageCount


class AnalyticsDatabase:
    """
    Wraps a SQLite database and provides some convenience methods for
    updating and querying it.
    """

    def __init__(self, path: pathlib.Path | str):
        """
        Create a new instance of AnalyticsDatabase.
        """
        self.db = Database(path)
        self.path = pathlib.Path(path)

    def close(self) -> None:
        """
        Close the underlying database connection.
        """
        self.db.close()  # type: ignore

    @property
    def events_table(self) -> Table:
        """
        The table which stores all the analytics events -- that is,
        any time somebody visits my site.
        """
        return Table(self.db, "events")

    @property
    def posts_table(self) -> Table:
        """
        The table which stores all my recent posts -- that is, articles
        I've published on my site.
        """
        return Table(self.db, "posts")

    @staticmethod
    def _where_clause(start_date: datetime.date, end_date: datetime.date) -> str:
        """
        This creates a SQLite query fragment that filters out certain
        values I don't want, and filters to a date range.
        """
        # Note: we add the 'x' so that complete datestamps
        # e.g. 2001-02-03T04:56:07Z sort lower than a date like '2001-02-03'
        return f"""
            is_me = '0'
            and host != 'localhost'
            and host != '127.0.0.1'
            and host not like '%--alexwlchan.netlify.app'
            and date >= '{start_date.isoformat()}'
            and date <= '{end_date.isoformat() + 'x'}'
        """.strip()

    def count_requests_per_day(
        self, start_date: datetime.date, end_date: datetime.date
    ) -> list[PerDayCount]:
        """
        Given a range of days, return a count of total hits in those days, e.g.

            {"2001-01-01" -> 123, "2001-01-02" -> 456, …}

        This will return a complete range of days between start/end, even
        if there were no hits on some of the days.
        """
        cursor = self.db.query(
            f"""
            SELECT
                substring(date, 0, 11) as day,
                count(*) as count
            FROM
                events
            WHERE
                {self._where_clause(start_date, end_date)}
            GROUP BY
                day
            ORDER BY
                date desc
            """
        )

        count_lookup = {row["day"]: row["count"] for row in cursor}

        return [
            {"day": day.isoformat(), "count": count_lookup.get(day.isoformat(), 0)}
            for day in days_between(start_date, end_date)
        ]

    def count_unique_visitors_per_day(
        self, start_date: datetime.date, end_date: datetime.date
    ) -> list[PerDayCount]:
        """
        Given a range of days, count the unique visitors each day, e.g.

            {"2001-01-01" -> 123, "2001-01-02" -> 456, …}

        This will return a complete range of days between start/end, even
        if there were no hits on some of the days.
        """
        cursor = self.db.query(
            f"""
            SELECT
                substring(date, 0, 11) as day,
                count(distinct session_id) as count
            FROM
                events
            WHERE
                {self._where_clause(start_date, end_date)}
            GROUP BY
                day
            ORDER BY
                date desc
            """
        )

        count_lookup = {row["day"]: row["count"] for row in cursor}

        return [
            {"day": day.isoformat(), "count": count_lookup.get(day.isoformat(), 0)}
            for day in days_between(start_date, end_date)
        ]

    def count_visitors_by_country(
        self, start_date: datetime.date, end_date: datetime.date
    ) -> dict[str, int]:
        """
        Given a range of days, count the requests from each country in
        that range:

            {"US" -> 100, "GB" -> 80, …}

        The keys will (mostly) be the 2-digit ISO country codes.
        """
        cursor = self.db.query(
            f"""
            SELECT
                country,
                count(*) as count
            FROM
                events
            WHERE
                {self._where_clause(start_date, end_date)}
                AND country IS NOT NULL
            GROUP BY
                country
            """
        )

        return collections.Counter({row["country"]: row["count"] for row in cursor})

    def count_hits_per_page(
        self, start_date: datetime.date, end_date: datetime.date, *, limit: int
    ) -> list[PerPageCount]:
        """
        Given a range of dates, count the hits per unique page.
        """
        cursor = self.db.query(
            f"""
            SELECT
                title, host, path,
                count(*) as count
            FROM
                events
            WHERE
                {self._where_clause(start_date, end_date)}
            GROUP BY
                title
            ORDER BY
                count desc
            LIMIT
                {limit}
            """
        )

        return [typing.cast(PerPageCount, row) for row in cursor]

    def count_referrers(
        self, start_date: datetime.date, end_date: datetime.date
    ) -> CountedReferrers:
        """
        Get a list of referrers, grouped by source.  The entries look
        something like

            (
                "Hacker News",
                {
                    "Making a PDF that’s larger than Germany": 200,
                    "You should take more screenshots": 50,
                    "Cut the cutesy errors": 1,
                }
            )

        """
        referrers_by_page = self.db.query(
            f"""
            SELECT
                title, path, normalised_referrer,
                count(*) as count
            FROM
                events
            WHERE
                {self._where_clause(start_date, end_date)}
                and normalised_referrer != ''
            GROUP BY
                path, normalised_referrer
            ORDER BY
                count desc
        """
        )

        # normalised referrer -> dict(page -> count)
        grouped_referrers: dict[str, dict[str, int]] = collections.defaultdict(
            lambda: collections.Counter()
        )

        for row in referrers_by_page:
            if row["title"] == "410 Gone – alexwlchan":
                label = row["path"] + " (410)"
            elif row["title"] == "404 Not Found – alexwlchan":
                label = row["path"] + " (404)"
            else:
                label = row["title"]

            grouped_referrers[row["normalised_referrer"]][label] = row["count"]

        # (normalised_referrer, dict(page -> count))
        sorted_grouped_referrers: list[tuple[str, dict[str, int]]] = sorted(
            grouped_referrers.items(), key=lambda kv: sum(kv[1].values()), reverse=True
        )

        # These popular posts will have a long tail of referrers, so
        # gather up the long tail to display "and these N other sites
        # had one or two links to this popular post".
        popular_posts = {
            "Making a PDF that’s larger than Germany – alexwlchan",
            "The Collected Works of Ian Flemingo – alexwlchan",
            "You should take more screenshots – alexwlchan",
            "Creating a Safari webarchive from the command line – alexwlchan",
            "Documenting my DNS records – alexwlchan",
        }

        long_tail: dict[str, dict[str, int]] = collections.defaultdict(
            lambda: collections.Counter()
        )

        for source, tally in list(sorted_grouped_referrers):
            if sum(tally.values()) <= 3 and set(tally.keys()).issubset(popular_posts):
                for dest, dest_count in tally.items():
                    long_tail[dest][source] = dest_count
                sorted_grouped_referrers.remove((source, tally))

        return {"grouped_referrers": sorted_grouped_referrers, "long_tail": long_tail}

    def count_missing_pages(
        self, start_date: datetime.date, end_date: datetime.date
    ) -> list[MissingPage]:
        """
        Get a list of pages which returned a 404.

        We can't see the page status code in JavaScript, so we can't sent it to the
        tracking pixel -- we have to look for the 404 page title.
        """
        # Skip paths that end in `/null`.
        #
        # I see a handful of URLs like this -- I don't really know where
        # they're coming from, but they're infrequent enough that I think
        # it's a client issue rather than an issue on my site.
        cursor = self.db.query(
            f"""
            SELECT
                path, count(*) as count
            FROM
                events
            WHERE
                {self._where_clause(start_date, end_date)}
                and title = '404 Not Found – alexwlchan'
                and path NOT LIKE '%/null'
            GROUP BY
                path
            ORDER BY
                count desc
            LIMIT
                25
            """
        )

        return [
            {
                "path": row["path"],
                "count": row["count"],
            }
            for row in cursor
        ]

    def get_latest_recorded_event(self) -> datetime.datetime:
        """
        Return the time of the last event recorded in the database.
        """
        cursor = self.db.query("SELECT MAX(date) FROM events")

        date_string = next(cursor)["MAX(date)"]

        return datetime.datetime.fromisoformat(date_string)
