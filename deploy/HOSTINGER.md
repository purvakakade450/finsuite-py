# Hosting FinSuite on a Hostinger VPS

Works on a fresh Ubuntu 22.04 or 24.04 VPS (1 GB RAM is enough, 2 GB is comfortable).

## 1. Before you start
- In hPanel, open your VPS and choose the **Ubuntu** template (no control panel needed).
- Note the VPS **IP address**. For a domain, add an **A record** pointing to that IP.
- Connect: `ssh root@YOUR_SERVER_IP` (or use the Browser terminal in hPanel).

## 2. Install (one command)
Without a domain (HTTP on the IP):
```
curl -fsSL https://raw.githubusercontent.com/purvakakade450/finsuite-py/main/deploy/setup.sh | bash
```
With a domain (also sets up free HTTPS):
```
curl -fsSL https://raw.githubusercontent.com/purvakakade450/finsuite-py/main/deploy/setup.sh | DOMAIN=yourdomain.com bash
```
Then open `http://YOUR_SERVER_IP/` or `https://yourdomain.com/`.

If the GitHub repo is private, clone it first with a token, then run `bash /opt/finsuite/deploy/setup.sh`.

## 3. Update after you push changes to GitHub
```
bash /opt/finsuite/deploy/update.sh
```

## 4. Useful commands
- App logs: `journalctl -u finsuite -f`
- Restart: `systemctl restart finsuite`
- Status: `systemctl status finsuite`
- Nginx test: `nginx -t`

## Notes
- The app listens only on 127.0.0.1:8000; nginx is the public entrance on ports 80/443.
- Live prices and news come from Yahoo Finance and Google News. Data centre IPs are sometimes
  rate limited by Yahoo, so if quotes fail on the VPS but work elsewhere, wait a few minutes and retry.
