#!/usr/bin/env bash
# Second half of update.sh (kept separate so that a newly pulled version is the one that runs).
set -euo pipefail
cd /opt/finsuite
./venv/bin/pip install -r requirements.txt
chown -R www-data:www-data /opt/finsuite
cp deploy/finsuite.service /etc/systemd/system/finsuite.service
install -m 644 deploy/finsuite.cron /etc/cron.d/finsuite
install -m 644 deploy/finsuite.logrotate /etc/logrotate.d/finsuite
mkdir -p /var/backups/finsuite
systemctl daemon-reload
systemctl restart finsuite
systemctl --no-pager status finsuite | head -5
