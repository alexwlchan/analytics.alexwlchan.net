import collections
import datetime
import json
import uuid

from flask import abort, Flask, render_template, request, send_file
from flask.wrappers import Response
import hyperlink
import pycountry

from utils import (
    get_country_iso_code,
    get_database,
    get_session_identifier,
    guess_if_bot,
    normalise_referrer,
)


app = Flask(__name__)

db = get_database(path="requests.sqlite")


@app.route("/")
def index() -> str:
    return """<p>This website hosts a tracking pixel for alexwlchan.net and its subdomains.</p>

    <p>For more information about what gets tracked, you can read:</p>

    <ul>
        <li><a href="https://alexwlchan.net/privacy/">my privacy policy</a></li>
        <li><a href="https://github.com/alexwlchan/analytics.alexwlchan.net">the code on GitHub</a></li>
    </ul>
    """


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

    from pprint import pprint; pprint(request.cookies)

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


def count_requests_by_day():
    return db.query(
        """
        select
          substring(date, 0, 11) as day,
          count(*) as count
        from
          events
        where
          host != 'localhost' and host not like '%--alexwlchan.netlify.app'
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
          host != 'localhost' and host not like '%--alexwlchan.netlify.app'
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
          and host != 'localhost' and host not like '%--alexwlchan.netlify.app'
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


def find_popular_pages():
    return db.query(
        """
        select
          *,
          count(*) as count
        from
          events
        where
          date >= :date
          and host != 'localhost' and host not like '%--alexwlchan.netlify.app'
        group by
          title
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
          and host != 'localhost' and host not like '%--alexwlchan.netlify.app'
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


def find_grouped_referrers():
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
          and host != 'localhost' and host not like '%--alexwlchan.netlify.app'
        group by
          title, normalised_referrer
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
        grouped_referrers[row["normalised_referrer"]][row["title"]] = row["count"]

    grouped_referrers = sorted(
        grouped_referrers.items(), key=lambda kv: sum(kv[1].values()), reverse=True
    )

    return grouped_referrers


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
app.jinja_env.filters["interpolate_color"] = get_hex_color_between


@app.route("/dashboard/")
def dashboard():
    by_date = count_requests_by_day()

    unique_users = count_unique_visitors()

    top_pages = find_popular_pages()

    missing_pages = find_missing_pages()

    grouped_referrers = find_grouped_referrers()

    visitors_by_country = count_visitors_by_country()

    country_names = {
        country: get_country_name(country) for country in visitors_by_country
    }

    return render_template(
        "dashboard.html",
        by_date=sorted(by_date, key=lambda row: row["day"]),
        unique_users=sorted(unique_users, key=lambda row: row["day"]),
        top_pages=list(top_pages),
        missing_pages=list(missing_pages),
        grouped_referrers=grouped_referrers,
        visitors_by_country=count_visitors_by_country(),
        country_names=country_names,
    )
