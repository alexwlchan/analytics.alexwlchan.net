# https://flask.palletsprojects.com/en/2.3.x/tutorial/database/#

import datetime
import functools
import json
import uuid

from flask import abort, Flask, request, send_file
import hyperlink
import maxminddb
from sqlite_utils import Database


@functools.lru_cache
def country_iso_code(ip_address):
    with maxminddb.open_database('GeoLite2-Country_20240116/GeoLite2-Country.mmdb') as reader:
        result = reader.get(ip_address)

    try:
        return result['country']['iso_code']
    except TypeError:
        if result is None:
            return None
        else:
            raise



app = Flask(__name__)

db = Database("requests.sqlite")
events = db["events"]
events.create(
    {
        "id": str,
        "date": str,
        "url": str,
        "title": str,
        "session_id": str,
        "country": str,
        "host": str,
        "path": str,
        "query": str,
        "width": int,
        "height": int,
    },
    pk="id",
    if_not_exists=True
)


@functools.lru_cache()
def get_session_identifier(today, ip_address):
    # mix in user-agent here

    return uuid.uuid4()



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
            today=datetime.date.today(),
            ip_address=request.remote_addr
        ),
        'country': country_iso_code(request.remote_addr),
        'host': u.host,
        'path': '/' + '/'.join(u.path),
        'query': json.dumps(u.query),
        'width': width,
        'height': height
    }

    db = Database("requests.sqlite")
    events = db["events"]
    events.insert(row)

    return send_file("static/a.gif")
