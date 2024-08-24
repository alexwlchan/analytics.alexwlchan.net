"""
Tests for the pytest fixtures defined in ``conftest.py``.
"""

import os
import re

import pytest


@pytest.mark.parametrize("cassette_name", os.listdir("tests/cassettes"))
def test_no_netlify_token_in_cassettes(cassette_name: str) -> None:
    """
    There's nothing that looks like a Netlify API token in the test cassettes.
    """
    with open(os.path.join("tests/cassettes", cassette_name)) as in_file:
        cassette_contents = in_file.read()

    assert re.search(r"Bearer nfp_", cassette_contents) is None
