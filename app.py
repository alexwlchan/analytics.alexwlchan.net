from flask import Flask, request, send_file
import hyperlink
from sqlite_utils import Database


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
    }
)


@app.route("/a.gif")
def tracking_pixel():
    return send_file("static/a.gif")
