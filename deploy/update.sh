#!/usr/bin/env bash
# Pull the latest code from GitHub and restart. Run as root on the VPS.
set -euo pipefail
cd /opt/finsuite
git pull
./venv/bin/pip install -r requirements.txt
chown -R www-data:www-data /opt/finsuite
systemctl restart finsuite
systemctl --no-pager status finsuite | head -5
