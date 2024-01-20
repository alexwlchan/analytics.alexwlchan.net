#!/usr/bin/env bash

set -o errexit
set -o nounset

source /home/alexwlchan/repos/analytics.alexwlchan.net/.venv/bin/activate

certbot certonly \
  --manual \
  --domains 'analytics.alexwlchan.net' \
  --preferred-challenges dns \
  -m alex@alexwlchan.net --agree-tos --no-eff-email \
  --keep-until-expiring

systemctl reload nginx
