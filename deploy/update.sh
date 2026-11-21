#!/usr/bin/env bash
# Pull the latest code from GitHub and restart. Run as root on the server:
#   sudo bash /opt/finsuite/deploy/update.sh
set -euo pipefail
cd /opt/finsuite
git config --global --add safe.directory /opt/finsuite    # the folder belongs to the www-data user
git pull
exec bash deploy/update_steps.sh                           # run the rest from the file just pulled
