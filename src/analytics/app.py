import collections
from collections.abc import Iterator
import datetime
import json
import typing
import uuid

from flask import abort, Flask, redirect, render_template, request, send_file, url_for
from flask import Response as FlaskResponse
import humanize
import hyperlink
from sqlite_utils import Database
from sqlite_utils.db import Table
from werkzeug.wrappers.response import Response as WerkzeugResponse

from .fetchers import fetch_netlify_bandwidth_usage, fetch_rss_feed_entries
from .referrers import normalise_referrer
from .types import CountedReferrers, MissingPage, RecentPost
from .utils import (
    get_circular_arc_path_command,
    get_country_iso_code,
    get_country_name,
    get_database,
    get_flag_emoji,
    get_hex_color_between,
    get_session_identifier,
    guess_if_bot,
)


app = Flask(__name__)

db = get_database(path="requests.sqlite")


def db_table(name: str) -> Table:
    db = app.config.setdefault("DATABASE", get_database(path="requests.sqlite"))

    return Table(db, name)


@app.route("/")
def index() -> str | WerkzeugResponse:
    if request.cookies.get("analytics.alexwlchan-isMe") == "true":
        return redirect(url_for("dashboard"))
    else:
        return render_template("index.html")


@app.route("/a.gif")
def tracking_pixel() -> FlaskResponse:
    try:
        url = request.args["url"]
        referrer = request.args["referrer"]
        title = request.args["title"]
    except KeyError:
        abort(400)

    user_agent = request.user_agent.string

    u = hyperlink.DecodedURL.from_text(url)

    ip_address = request.headers["X-Real-IP"]

    n_referrer: str | None

    if u.query == (("utm_source", "mastodon"),):
        n_referrer = "Mastodon"
    else:
        n_referrer = normalise_referrer(referrer)

    row = {
        "id": uuid.uuid4(),
        "date": datetime.datetime.now().isoformat(),
        "url": url,
        "title": title,
        "session_id": get_session_identifier(
            datetime.date.today(), ip_address=ip_address, user_agent=user_agent
        ),
        "country": get_country_iso_code(ip_address),
        "host": u.host,
        "referrer": referrer,
        "normalised_referrer": n_referrer,
        "path": "/" + "/".join(u.path),
        "query": json.dumps(u.query),
        "is_bot": guess_if_bot(user_agent),
        "is_me": request.cookies.get("analytics.alexwlchan-isMe") == "true",
    }

    db_table("events").insert(row)

    return send_file("static/a.gif")


@app.route("/robots.txt")
def robots_txt() -> FlaskResponse:
    return send_file("static/robots.txt")


class PerDayCount(typing.TypedDict):
    day: str
    count: int


class PerPageCount(typing.TypedDict):
    host: str
    path: str
    title: str
    count: int


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

        result: list[PerPageCount] = []

        for row in cursor:
            result.append(
                {
                    "title": row["title"],
                    "host": row["host"],
                    "path": row["path"],
                    "count": row["count"],
                }
            )

        return result

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


def find_missing_pages() -> Iterator[MissingPage]:
    for row in db.query(
        """
        select
          path,
          count(*) as count
        from
          events
        where
          date >= :date
          and title = '404 Not Found – alexwlchan'
          and is_me = '0' and host != 'localhost' and host not like '%--alexwlchan.netlify.app'
        group by
          path
        order by
          count desc
        limit
          25
    """,
        {
            "date": (datetime.date.today() - datetime.timedelta(days=29)).strftime(
                "%Y-%m-%d"
            )
        },
    ):
        yield {
            "path": row["path"],
            "count": row["count"],
        }


def get_recent_posts() -> list[RecentPost]:
    """
    Return a list of the ten most recent posts, and the number of times
    they were viewed.
    """
    for entry in fetch_rss_feed_entries():
        db_table("posts").upsert(entry, pk="id")

    query = """
        SELECT p.url, p.title, p.date_posted, COUNT(e.url) AS count
        FROM posts p
        LEFT JOIN events e ON p.url = e.url
        GROUP BY p.url, p.date_posted
        ORDER BY p.date_posted DESC
        LIMIT 10;
    """

    return [
        {
            "url": row["url"],
            "title": row["title"],
            "date_posted": datetime.datetime.fromisoformat(row["date_posted"]),
            "count": row["count"],
        }
        for row in db.query(query)
    ]


Counter = dict[str, int]


app.jinja_env.filters["flag_emoji"] = get_flag_emoji
app.jinja_env.filters["country_name"] = get_country_name
app.jinja_env.filters["intcomma"] = humanize.intcomma
app.jinja_env.filters["interpolate_color"] = get_hex_color_between
app.jinja_env.filters["naturalsize"] = humanize.naturalsize
app.jinja_env.globals["circular_arc"] = get_circular_arc_path_command

app.jinja_env.globals.update(
    now=lambda: datetime.datetime.now(tz=datetime.timezone.utc)
)


@app.template_filter("prettydate")
def prettydate(d: str) -> str:
    return datetime.datetime.strptime(d, "%Y-%m-%d").strftime("%a %-d %b")


@app.route("/dashboard/")
def dashboard() -> str:
    try:
        start_date = datetime.date.fromisoformat(request.args["startDate"])
        start_is_default = False
    except KeyError:
        start_date = datetime.date.today() - datetime.timedelta(days=29)
        start_is_default = True

    try:
        end_date = datetime.date.fromisoformat(request.args["endDate"])
        end_is_default = False
    except KeyError:
        end_date = datetime.date.today()
        end_is_default = True

    analytics_db = AnalyticsDatabase(db)

    by_date = analytics_db.count_requests_per_day(start_date, end_date)
    unique_visitors = analytics_db.count_unique_visitors_per_day(start_date, end_date)
    visitors_by_country = analytics_db.count_visitors_by_country(start_date, end_date)

    popular_pages = analytics_db.count_hits_per_page(start_date, end_date, limit=25)

    missing_pages = find_missing_pages()

    grouped_referrers = analytics_db.count_referrers(start_date, end_date)

    country_names = {
        country: get_country_name(country) for country in visitors_by_country
    }

    recent_posts = get_recent_posts()

    netlify_usage = fetch_netlify_bandwidth_usage()

    return render_template(
        "dashboard.html",
        start=start_date,
        end=end_date,
        start_is_default=start_is_default,
        end_is_default=end_is_default,
        by_date=by_date,
        unique_visitors=unique_visitors,
        popular_pages=popular_pages,
        missing_pages=list(missing_pages),
        grouped_referrers=grouped_referrers,
        visitors_by_country=visitors_by_country,
        country_names=country_names,
        recent_posts=recent_posts,
        netlify_usage=netlify_usage,
    )
