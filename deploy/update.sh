#!/usr/bin/env bash
# Pull the latest code from GitHub and restart. Run as root on the VPS.
set -euo pipefail
cd /opt/finsuite
git pull
./venv/bin/pip install -r requirements.txt
chown -R www-data:www-data /opt/finsuite
cp deploy/finsuite.service /etc/systemd/system/finsuite.service
install -m 644 deploy/finsuite.cron /etc/cron.d/finsuite
mkdir -p /var/backups/finsuite
systemctl daemon-reload
systemctl restart finsuite
systemctl --no-pager status finsuite | head -5
