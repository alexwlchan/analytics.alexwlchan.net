import datetime
import json
import uuid

from flask import abort, Flask, request, send_file
from flask.wrappers import Response
import hyperlink

from utils import (
    get_country_iso_code,
    get_database,
    get_session_identifier,
    guess_if_bot,
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

    row = {
        "id": uuid.uuid4(),
        "date": datetime.datetime.now().isoformat(),
        "url": url,
        "title": title,
        "session_id": get_session_identifier(
            datetime.date.today(), ip_address=request.remote_addr, user_agent=user_agent
        ),
        "country": get_country_iso_code(request.remote_addr),
        "host": u.host,
        "referrer": referrer,
        "path": "/" + "/".join(u.path),
        "query": json.dumps(u.query),
        "width": width,
        "height": height,
        "is_bot": guess_if_bot(user_agent),
    }

    db["events"].insert(row)

    return send_file("static/a.gif")
