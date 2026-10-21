#!/usr/bin/env bash
# One-time setup of FinSuite on a fresh Ubuntu 22.04/24.04 VPS (e.g. Hostinger).
# Run as root:   DOMAIN=example.com bash setup.sh      (DOMAIN is optional)
set -euo pipefail

REPO="${REPO:-https://github.com/purvakakade450/finsuite-py.git}"
APP_DIR=/opt/finsuite
DOMAIN="${DOMAIN:-}"

apt-get update
apt-get install -y python3 python3-venv python3-pip git nginx ufw

# App code
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" pull
else
  git clone "$REPO" "$APP_DIR"
fi

# Python environment
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"
chown -R www-data:www-data "$APP_DIR"

# Service (runs on 127.0.0.1:8000, restarts on crash and on reboot)
cp "$APP_DIR/deploy/finsuite.service" /etc/systemd/system/finsuite.service
systemctl daemon-reload
systemctl enable --now finsuite

# Nginx in front of it
SERVER_NAME="${DOMAIN:-_}"
sed "s/__SERVER_NAME__/$SERVER_NAME/" "$APP_DIR/deploy/nginx.conf" > /etc/nginx/sites-available/finsuite
ln -sf /etc/nginx/sites-available/finsuite /etc/nginx/sites-enabled/finsuite
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

# Firewall: SSH + web only
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

# Optional HTTPS (needs DOMAIN pointing at this server's IP)
if [ -n "$DOMAIN" ]; then
  apt-get install -y certbot python3-certbot-nginx
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --register-unsafely-without-email --redirect || \
    echo "HTTPS step failed. Check that $DOMAIN points to this server, then run: certbot --nginx -d $DOMAIN"
fi

echo "Done. Open http://${DOMAIN:-YOUR_SERVER_IP}/"
