import datetime
import glob
import json
import pathlib
import uuid

from flask import abort, Flask, redirect, render_template, request, send_file, url_for
from flask import Response as FlaskResponse
import humanize
import hyperlink
from sqlite_utils.db import Table
from werkzeug.wrappers.response import Response as WerkzeugResponse

from . import date_helpers
from .countries import get_country_iso_code, get_country_name, get_flag_emoji
from .database import AnalyticsDatabase
from .fetch_netlify_bandwidth import fetch_netlify_bandwidth_usage
from .fetch_rss_feed import fetch_rss_feed_entries, NoNewEntries
from .referrers import get_normalised_referrer
from .types import RecentPost
from .utils import (
    get_circular_arc_path_command,
    get_database,
    get_hex_color_between,
    get_session_identifier,
    guess_if_bot,
)


app = Flask(__name__)

db = get_database(path="requests.sqlite")


def db_table(name: str) -> Table:
    db = app.config.setdefault("DATABASE", get_database(path="requests.sqlite"))

    return Table(db, name)


def maxmind_db_path() -> pathlib.Path:
    db_folder = max(glob.glob("GeoLite2-Country_*"))
    db_path = pathlib.Path(db_folder) / "GeoLite2-Country.mmdb"
    return db_path


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

    u = hyperlink.parse(url)

    ip_address = request.headers["X-Real-IP"]

    normalised_referrer = get_normalised_referrer(referrer=referrer, query=u.query)

    country = get_country_iso_code(
        maxmind_db_path=maxmind_db_path(), ip_address=ip_address
    )

    row = {
        "id": uuid.uuid4(),
        "date": datetime.datetime.now().isoformat(),
        "url": url,
        "title": title,
        "session_id": get_session_identifier(
            datetime.date.today(), ip_address=ip_address, user_agent=user_agent
        ),
        "country": country,
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


def get_recent_posts() -> list[RecentPost]:
    """
    Return a list of the ten most recent posts, and the number of times
    they were viewed.
    """
    try:
        entries = fetch_rss_feed_entries()
        db_table("posts").upsert_all(entries, pk="id")
    except NoNewEntries:
        pass

    query = """
        SELECT p.host, p.path, p.title, p.date_posted, COUNT(e.url) AS count
        FROM posts p
        LEFT JOIN events e ON p.host = e.host AND p.path = e.path
        GROUP BY p.host, p.path, p.date_posted
        ORDER BY p.date_posted DESC
        LIMIT 10;
    """

    return [
        {
            "host": row["host"],
            "path": row["path"],
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
app.jinja_env.filters["prettydate"] = date_helpers.prettydate
app.jinja_env.globals["circular_arc"] = get_circular_arc_path_command


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

    missing_pages = analytics_db.count_missing_pages(start_date, end_date)

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
        now=date_helpers.now(),
        today=datetime.date.today(),
        yesterday=date_helpers.yesterday(),
    )
