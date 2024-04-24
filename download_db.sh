#!/usr/bin/env bash

set -o errexit
set -o nounset

today=$(date +"%Y-%m-%d")

scp alexwlchan@harmonia.linode:repos/analytics.alexwlchan.net/requests.sqlite "requests.$today.sqlite.tmp"

mv "requests.$today.sqlite.tmp" requests.sqlite
