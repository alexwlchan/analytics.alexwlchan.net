import collections
from collections.abc import Iterator
import datetime
import typing

from sqlite_utils import Database

from .types import CountedReferrers, MissingPage, PerDayCount, PerPageCount


class AnalyticsDatabase:
    def __init__(self, db: Database):
        self.db = db

    @staticmethod
    def _where_clause(start_date: datetime.date, end_date: datetime.date) -> str:
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

    @staticmethod
    def _days_between(
        start_date: datetime.date, end_date: datetime.date
    ) -> Iterator[datetime.date]:
        """
        Generate all the days between two dates, including the dates
        themselves.
        """
        d = start_date

        while d <= end_date:
            yield d
            d += datetime.timedelta(days=1)

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
            for day in self._days_between(start_date, end_date)
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
            for day in self._days_between(start_date, end_date)
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
        }

        long_tail: dict[str, dict[str, int]] = collections.defaultdict(
            lambda: collections.Counter()
        )

        for source, tally in list(sorted_grouped_referrers):
            if sum(tally.values()) <= 3 and set(tally.keys()).issubset(popular_posts):
                (dest,) = tally.keys()
                long_tail[dest][source] = tally[dest]
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
        cursor = self.db.query(
            f"""
            SELECT
                path, count(*) as count
            FROM
                events
            WHERE
                {self._where_clause(start_date, end_date)}
                and title = '404 Not Found – alexwlchan'
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
        start_date = datetime.date(1970, 1, 1)
        end_date = datetime.date(2038, 1, 1)
        cursor = self.db.query(
            f"""
            SELECT
                MAX(date)
            FROM
                events
            WHERE
                {self._where_clause(start_date, end_date)}
            LIMIT
                1
        """
        )

        date_string = next(cursor)["MAX(date)"]

        return datetime.datetime.fromisoformat(date_string)
