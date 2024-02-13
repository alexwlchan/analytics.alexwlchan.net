import collections
import datetime
import json
import uuid

from flask import abort, Flask, redirect, render_template, request, send_file, url_for
from flask.wrappers import Response
import humanize
import hyperlink
import pycountry

from referrers import normalise_referrer
from utils import (
    get_country_iso_code,
    get_database,
    get_session_identifier,
    guess_if_bot,
)


app = Flask(__name__)

db = get_database(path="requests.sqlite")


@app.route("/")
def index():
    if request.cookies.get("analytics.alexwlchan-isMe") == "true":
        return redirect(url_for("dashboard"))

    return render_template("index.html")


@app.route("/a.gif")
def tracking_pixel() -> Response:
    try:
        url = request.args["url"]
        referrer = request.args["referrer"]
        title = request.args["title"]
        width = int(request.args["width"])
        height = int(request.args["height"])
    except KeyError:
        abort(400)

    user_agent = request.user_agent.string

    u = hyperlink.DecodedURL.from_text(url)

    ip_address = request.headers["X-Real-IP"]

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
        "normalised_referrer": normalise_referrer(referrer),
        "path": "/" + "/".join(u.path),
        "query": json.dumps(u.query),
        "width": width,
        "height": height,
        "is_bot": guess_if_bot(user_agent),
        "is_me": request.cookies.get("analytics.alexwlchan-isMe") == "true",
    }

    db["events"].insert(row)

    return send_file("static/a.gif")


@app.route("/robots.txt")
def robots_txt():
    return send_file("static/robots.txt")


def count_requests_by_day():
    return db.query(
        """
        select
          substring(date, 0, 11) as day,
          count(*) as count
        from
          events
        where
          is_me = '0' and host != 'localhost' and host not like '%--alexwlchan.netlify.app'
        group by
          day
        order by
          date desc
        limit
          30
    """
    )


def count_unique_visitors():
    return db.query(
        """
        select
          substring(date, 0, 11) as day,
          count(distinct session_id) as unique_session_count
        from
          events
        where
          is_me = '0' and host != 'localhost' and host not like '%--alexwlchan.netlify.app'
        group by
          day
        order by
          date desc
        limit 30
    """
    )


def count_visitors_by_country():
    cursor = db.query(
        """
        select
          country,
          count(*) as count
        from
          events
        where
          date >= :date
          and country != ''
          and is_me = '0' and host != 'localhost' and host not like '%--alexwlchan.netlify.app'
        group by
          country
        order by
          count desc
        """,
        {
            "date": (datetime.date.today() - datetime.timedelta(days=29)).strftime(
                "%Y-%m-%d"
            )
        },
    )

    return collections.Counter({row["country"]: row["count"] for row in cursor})


def get_per_page_counts():
    result = db.query(
        """
        select
          *,
          count(*) as count
        from
          events
        where
          date >= :date
          and is_me = '0' and host != 'localhost' and host not like '%--alexwlchan.netlify.app'
        group by
          title
        order by
          count desc
    """,
        {
            "date": (datetime.date.today() - datetime.timedelta(days=29)).strftime(
                "%Y-%m-%d"
            )
        },
    )

    return list(result)


def find_missing_pages():
    return db.query(
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
    )


def get_recent_posts(per_page_counts):
    per_url_counts = collections.Counter()

    for p in per_page_counts:
        per_url_counts[f"https://{p['host']}{p['path']}"] += p["count"]

    posts = list(
        db.query(
            """
        select
          *
        from
          posts
        order by
          date_posted desc
        limit
          10
        """
        )
    )

    for p in posts:
        p["count"] = per_url_counts.get(p["url"], 0)
        p["date_posted"] = datetime.datetime.fromisoformat(p["date_posted"])

    return posts


Counter = dict[str, int]


def find_grouped_referrers() -> list[tuple[str, Counter]]:
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
    referrers_by_page = db.query(
        """
        select
          *,
          count(*) as count
        from
          events
        where
          date >= :date
           and normalised_referrer != ''
          and is_me = '0' and host != 'localhost' and host not like '%--alexwlchan.netlify.app'
        group by
          path, normalised_referrer
        order by
          count desc
    """,
        {
            "date": (datetime.date.today() - datetime.timedelta(days=29)).strftime(
                "%Y-%m-%d"
            )
        },
    )

    grouped_referrers = collections.defaultdict(lambda: collections.Counter())

    for row in referrers_by_page:
        if row["title"] == "410 Gone – alexwlchan":
            label = row["path"] + " (410)"
        elif row["title"] == "404 Not Found – alexwlchan":
            label = row["path"] + " (404)"
        else:
            label = row["title"]

        grouped_referrers[row["normalised_referrer"]][label] = row["count"]

    grouped_referrers = sorted(
        grouped_referrers.items(), key=lambda kv: sum(kv[1].values()), reverse=True
    )

    popular_posts = {
        "Making a PDF that’s larger than Germany – alexwlchan",
        "The Collected Works of Ian Flemingo – alexwlchan",
    }

    long_tail = collections.defaultdict(lambda: collections.Counter())

    for source, tally in list(grouped_referrers):
        if sum(tally.values()) <= 3 and set(tally.keys()).issubset(popular_posts):
            (dest,) = tally.keys()
            long_tail[dest][source] = tally[dest]
            grouped_referrers.remove((source, tally))

    return {"grouped_referrers": grouped_referrers, "long_tail": long_tail}


def get_flag_emoji(country_id: str) -> str:
    code_point_start = ord("🇦") - ord("A")
    assert code_point_start == 127397

    code_points = [code_point_start + ord(char) for char in country_id]
    return "".join(chr(cp) for cp in code_points)


def get_country_name(country_id: str) -> str:
    if country_id == "US":
        return "USA"

    if country_id == "GB":
        return "UK"

    if country_id == "RU":
        return "Russia"

    c = pycountry.countries.get(alpha_2=country_id)

    if c is not None:
        return c.name
    else:
        return country_id


def get_hex_color_between(hex1, hex2, proportion):
    r1, g1, b1 = int(hex1[1:3], 16), int(hex1[3:5], 16), int(hex1[5:7], 16)
    r2, g2, b2 = int(hex2[1:3], 16), int(hex2[3:5], 16), int(hex2[5:7], 16)

    r_new = int(r1 + (r2 - r1) * proportion)
    g_new = int(g1 + (g2 - g1) * proportion)
    b_new = int(b1 + (b2 - b1) * proportion)

    return "#%02x%02x%02x" % (r_new, g_new, b_new)


app.jinja_env.filters["flag_emoji"] = get_flag_emoji
app.jinja_env.filters["country_name"] = get_country_name
app.jinja_env.filters["intcomma"] = humanize.intcomma
app.jinja_env.filters["interpolate_color"] = get_hex_color_between


@app.template_filter("prettydate")
def prettydate(d: str) -> str:
    return datetime.datetime.strptime(d, "%Y-%m-%d").strftime("%a %-d %b")


@app.route("/dashboard/")
def dashboard():
    by_date = count_requests_by_day()

    unique_users = count_unique_visitors()

    per_page_counts = get_per_page_counts()
    popular_pages = per_page_counts[:25]

    missing_pages = find_missing_pages()

    grouped_referrers = find_grouped_referrers()

    visitors_by_country = count_visitors_by_country()

    country_names = {
        country: get_country_name(country) for country in visitors_by_country
    }

    recent_posts = get_recent_posts(per_page_counts)

    return render_template(
        "dashboard.html",
        by_date=sorted(by_date, key=lambda row: row["day"]),
        unique_users=sorted(unique_users, key=lambda row: row["day"]),
        popular_pages=popular_pages,
        missing_pages=list(missing_pages),
        grouped_referrers=grouped_referrers,
        visitors_by_country=count_visitors_by_country(),
        country_names=country_names,
        recent_posts=recent_posts,
    )
