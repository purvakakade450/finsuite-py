# Hosting FinSuite on an AWS EC2 server

Tested on an Ubuntu 26.04 `t`-class instance with about 1 GB of memory (the setup script adds a 2 GB swap file).

## 1. Create the server
1. EC2 > Launch instance > Ubuntu, 1 GB memory or more, 8 GB disk. Create a key pair and keep the `.pem` file private
   (it is the only key to the server; `*.pem` is in `.gitignore`).
2. Security group, inbound rules:
   - SSH, port 22, from your own address (or anywhere, if your address changes often: only the key can log in)
   - HTTP, port 80, and HTTPS, port 443, from anywhere
3. Note the **public IPv4 address** (it changes if the instance is stopped and started; an Elastic IP keeps it fixed).

## 2. Install
```
ssh -i finsuite.pem ubuntu@YOUR_SERVER_IP
curl -fsSL https://raw.githubusercontent.com/purvakakade450/finsuite-py/main/deploy/setup.sh -o setup.sh
sudo bash setup.sh                  # or: sudo DOMAIN=yourdomain.com bash setup.sh   (adds free HTTPS)
```
This installs the app in `/opt/finsuite`, runs it as the `finsuite` service behind nginx, opens the firewall for web and SSH,
and installs the daily backup and the five-minute uptime check (`/etc/cron.d/finsuite`).

## 3. Settings (keys and passwords)
Put them in `/etc/finsuite.env` (readable only by root), then restart:
```
sudo nano /etc/finsuite.env
sudo chmod 600 /etc/finsuite.env && sudo systemctl restart finsuite
```
```
# AI assistant: a FREE key from https://aistudio.google.com/apikey (Google) ...
AI_API_KEY=...
AI_PROVIDER=gemini
# ... or, if you pay for Claude: ANTHROPIC_API_KEY=...
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your-16-letter-app-password
SMTP_FROM=FinSuite Alerts <you@gmail.com>
TELEGRAM_BOT_TOKEN=...
PUBLIC_URL=https://yourdomain.com
ADMIN_EMAIL=you@gmail.com
```
Then open the account window on the site and press "Send me a test email". (The app reads `/etc/finsuite.env`, not a `.env` in your home folder.)

## 4. Domain and HTTPS
Point the domain's **A record** (`@`) at the server's IP, and `www` at the domain. Then, on the server:
`sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com`. Installing the app, push notifications and the offline
mode only work on an HTTPS address.

## 5. Update, check, restore
- Update: `sudo bash /opt/finsuite/deploy/update.sh`
- Logs: `sudo journalctl -u finsuite -f`
- Health: `curl localhost:8000/api/health?deep=1`
- Backups: `/var/backups/finsuite/` (14 daily copies). Restore:
  `gunzip -c /var/backups/finsuite/finsuite-DATE.db.gz | sudo tee /var/lib/finsuite/finsuite.db > /dev/null && sudo chown www-data: /var/lib/finsuite/finsuite.db && sudo systemctl restart finsuite`
