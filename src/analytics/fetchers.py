import datetime
import typing

import httpx

from .utils import get_password


class NetlifyBandwidthUsage(typing.TypedDict):
    used: int
    included: int
    period_start_date: datetime.datetime
    period_end_date: datetime.datetime


def fetch_netlify_bandwidth_usage() -> NetlifyBandwidthUsage:
    """
    Look up my Netlify bandwidth usage from the API.

    See https://alexwlchan.net/til/2024/get-netlify-usage-from-api/
    """
    team_slug = get_password("netlify", "team_slug")
    analytics_token = get_password("netlify", "analytics_token")

    resp = httpx.get(
        url=f"https://api.netlify.com/api/v1/accounts/{team_slug}/bandwidth",
        headers={"Authorization": f"Bearer {analytics_token}"},
    )
    resp.raise_for_status()

    data = resp.json()

    return {
        "used": data["used"],
        "included": data["included"],
        "period_start_date": datetime.datetime.fromisoformat(data["period_start_date"]),
        "period_end_date": datetime.datetime.fromisoformat(data["period_end_date"]),
    }
