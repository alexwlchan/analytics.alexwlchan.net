from collections.abc import Iterator
import datetime
import json
import uuid

from flask import abort, Flask, redirect, render_template, request, send_file, url_for
from flask import Response as FlaskResponse
import humanize
import hyperlink
from sqlite_utils.db import Table
from werkzeug.wrappers.response import Response as WerkzeugResponse

from .database import AnalyticsDatabase
from .fetchers import fetch_netlify_bandwidth_usage, fetch_rss_feed_entries
from .referrers import get_normalised_referrer
from .types import MissingPage, RecentPost
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

    normalised_referrer = get_normalised_referrer(referrer=referrer, query=u.query)

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
        "normalised_referrer": normalised_referrer,
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
app.jinja_env.filters["naturaltime"] = humanize.naturaltime
app.jinja_env.globals["circular_arc"] = get_circular_arc_path_command

app.jinja_env.globals.update(
    now=lambda: datetime.datetime.now(tz=datetime.timezone.utc)
)

app.jinja_env.globals.update(
    yesterday=lambda: datetime.datetime.now(tz=datetime.timezone.utc)
    - datetime.timedelta(days=1)
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

    counted_referrers = analytics_db.count_referrers(start_date, end_date)

    country_names = {
        country: get_country_name(country) for country in visitors_by_country
    }

    recent_posts = get_recent_posts()

    netlify_usage = fetch_netlify_bandwidth_usage()

    latest_event = analytics_db.get_latest_recorded_event()

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
        counted_referrers=counted_referrers,
        visitors_by_country=visitors_by_country,
        country_names=country_names,
        recent_posts=recent_posts,
        netlify_usage=netlify_usage,
        latest_event=latest_event,
    )
