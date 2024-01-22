import collections
import datetime
import json

from flask import Flask, render_template

from utils import get_database


app = Flask(__name__)

db = get_database(path="requests.sqlite")


@app.route("/")
def index():
    by_date = db.query(
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

    unique_users = db.query(
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

    top_pages = db.query(
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

    missing_pages = db.query(
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
        grouped_referrers[row['normalised_referrer']][row['title']] = row['count']

    grouped_referrers = sorted(grouped_referrers.items(), key=lambda kv: sum(kv[1].values()), reverse=True)

    return render_template(
        "dashboard.html",
        by_date=sorted(by_date, key=lambda row: row["day"]),
        unique_users=sorted(unique_users, key=lambda row: row["day"]),
        top_pages=list(top_pages),
        missing_pages=list(missing_pages),
        referrers_by_page=referrers_by_page,
        grouped_referrers=grouped_referrers,
    )
