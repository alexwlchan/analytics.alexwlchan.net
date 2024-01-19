# https://flask.palletsprojects.com/en/2.3.x/tutorial/database/#

import datetime
import functools
import json
import sqlite3
import uuid

from flask import abort, Flask, request, send_file
import hyperlink
import maxminddb
from sqlite_utils import Database

from utils import get_country_iso_code, get_database, get_session_identifier


app = Flask(__name__)

db = get_database(path="requests.sqlite")


@app.route("/a.gif")
def tracking_pixel():
    try:
        url = request.args['url']
        referrer = request.args['referrer']
        title = request.args['title']
        width = int(request.args['width'])
        height = int(request.args['height'])
    except KeyError:
        abort(400)

    u = hyperlink.DecodedURL.from_text(url)

    row = {
        'id': uuid.uuid4(),
        'date': datetime.datetime.now().isoformat(),
        'url': url,
        'title': title,
        'session_id': get_session_identifier(
            db,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string
        ),
        'country': get_country_iso_code(request.remote_addr),
        'host': u.host,
        'path': '/' + '/'.join(u.path),
        'query': json.dumps(u.query),
        'width': width,
        'height': height
    }

    db['events'].insert(row)

    return send_file("static/a.gif")
