#!/usr/bin/env python3

import httpx
import keyring


if __name__ == '__main__':
    team_slug = keyring.get_password('netlify', 'team_slug')
    analytics_token = keyring.get_password('netlify', 'analytics_token')

    assert team_slug is not None
    assert analytics_token is not None

    resp = httpx.get(
        f'https://api.netlify.com/api/v1/accounts/{team_slug}/bandwidth',
        headers={'Authorization': f'Bearer {analytics_token}'}
    )
    resp.raise_for_status()

    from pprint import pprint; pprint(resp.json())