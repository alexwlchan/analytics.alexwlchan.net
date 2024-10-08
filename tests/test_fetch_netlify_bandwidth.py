"""
Tests for ``analytics.fetch_netlify_bandwidth``.
"""

import datetime
import json
import pathlib

import pytest

from analytics.fetch_netlify_bandwidth import fetch_netlify_bandwidth_usage


@pytest.mark.vcr()
def test_fetch_netlify_bandwidth(tmp_working_dir: pathlib.Path) -> None:
    """
    Fetch the Netlify bandwidth.
    """
    bst = datetime.timezone(datetime.timedelta(days=-1, seconds=61200))

    assert fetch_netlify_bandwidth_usage() == {
        "included": 107374182400,
        "period_end_date": datetime.datetime(2024, 6, 17, 0, 0, tzinfo=bst),
        "period_start_date": datetime.datetime(2024, 5, 17, 0, 0, tzinfo=bst),
        "used": 55865320374,
    }


@pytest.mark.vcr()
def test_fetch_netlify_bandwidth_is_cached(tmp_working_dir: pathlib.Path) -> None:
    """
    If you fetch the Netlify bandwidth twice, it gets cached to disk.
    """
    result1 = fetch_netlify_bandwidth_usage()
    result2 = fetch_netlify_bandwidth_usage()

    assert result1 == result2
    assert (tmp_working_dir / "netlify_usage.json").exists()


def test_respects_retry_after_header(tmp_working_dir: pathlib.Path) -> None:
    """
    It won't re-fetch the Netlify bandwidth data until after the time
    sent by the HTTP ``Retry-After`` header has passed.
    """
    data = {
        "used": 100,
        "included": 200,
        "period_start_date": "2024-05-17T00:00:00.000-07:00",
        "period_end_date": "2024-06-17T00:00:00.000-07:00",
    }

    cached_response = json.dumps(
        {
            "etag": "123",
            "data": data,
            "retry-after": (
                datetime.datetime.now() + datetime.timedelta(minutes=10)
            ).strftime("%Y-%m-%d %H:%M:%S UTC"),
        }
    )

    (tmp_working_dir / "netlify_usage.json").write_text(cached_response)

    result = fetch_netlify_bandwidth_usage()
    assert result["used"] == 100
    assert result["included"] == 200
