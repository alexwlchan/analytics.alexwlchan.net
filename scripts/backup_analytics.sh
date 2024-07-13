#!/usr/bin/env bash
# Save a snapshot of my analytics database.

set -o errexit
set -o nounset

scp alexwlchan@harmonia.linode:repos/analytics.alexwlchan.net/requests.sqlite .

cp \
  requests.sqlite \
  /Volumes/Media\ \(Sapphire\)/backups/alexwlchan.net/analytics/requests.$(date +"%Y-%m-%d").sqlite
