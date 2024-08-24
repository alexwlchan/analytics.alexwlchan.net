"""
Look up my Netlify bandwidth usage.

This is used to show a small pie chart in the interface, which marks
how much of this month's allocation I've used.  This lets me see if I'm
at risk of incurring an overage charge, and need to take some preventative
measure (either reducing my usage, or changing my plan).
"""

import datetime
import json
import typing

import httpx

from .utils import get_password


class NetlifyBandwidthUsage(typing.TypedDict):
    """
    The parsed data from the Netlify Bandwidth Usage API.
    """

    used: int
    included: int
    period_start_date: datetime.datetime
    period_end_date: datetime.datetime


def parse_data(data: typing.Any) -> NetlifyBandwidthUsage:
    """
    Convert the untyped raw data into a typed object.
    """
    return {
        "used": data["used"],
        "included": data["included"],
        "period_start_date": datetime.datetime.fromisoformat(data["period_start_date"]),
        "period_end_date": datetime.datetime.fromisoformat(data["period_end_date"]),
    }


def fetch_netlify_bandwidth_usage() -> NetlifyBandwidthUsage:
    """
    Look up my Netlify bandwidth usage from the API.

    See https://alexwlchan.net/til/2024/get-netlify-usage-from-api/
    """
    team_slug = "netlify-mi34feu"
    analytics_token = get_password("netlify", "analytics_token")

    headers = {"Authorization": f"Bearer {analytics_token}"}

    try:
        with open("netlify_usage.json") as in_file:
            cached_data = json.load(in_file)
            headers["If-None-Match"] = cached_data["etag"]

        # The Netlify API returns a Retry-After header, which we include
        # in the cache.  We don't fetch the data if that expiry time hasn't
        # passed yet, because we know the response hasn't changed.
        retry_after = datetime.datetime.strptime(
            cached_data["retry-after"], "%Y-%m-%d %H:%M:%S UTC"
        ).replace(tzinfo=datetime.UTC)

        if datetime.datetime.now(datetime.UTC) < retry_after:
            return parse_data(data=cached_data["data"])
    except (FileNotFoundError, ValueError):
        pass

    resp = httpx.get(
        url=f"https://api.netlify.com/api/v1/accounts/{team_slug}/bandwidth",
        headers=headers,
    )

    if resp.status_code == 304:
        with open("netlify_usage.json", "w") as out_file:
            out_file.write(
                json.dumps({**cached_data, "retry-after": resp.headers["retry-after"]})
            )

        return parse_data(data=cached_data["data"])
    else:
        resp.raise_for_status()

        with open("netlify_usage.json", "w") as out_file:
            out_file.write(
                json.dumps(
                    {
                        "data": resp.json(),
                        "etag": resp.headers["etag"],
                        "retry-after": resp.headers["retry-after"],
                    }
                )
            )

        return parse_data(data=resp.json())
