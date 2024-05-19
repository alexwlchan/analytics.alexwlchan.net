#!/usr/bin/env bash

set -o errexit
set -o nounset

git pull origin main
kill -HUP $(cat analytics.pid)
curl -v https://analytics.alexwlchan.net >/dev/null
python3 update_normalised_referrer.py
