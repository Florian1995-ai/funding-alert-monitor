# Funding Alerts — Push Notifications

Real-time desktop notifications when startups raise funding. Powered by ntfy.

## Quick Start

### 1. Install Docker
- Mac: https://docs.docker.com/desktop/install/mac-install/
- Windows: https://docs.docker.com/desktop/install/windows-install/
- Linux: `curl -fsSL https://get.docker.com | sh`

### 2. Start the server
```bash
docker compose up -d
```

### 3. Subscribe to alerts
Open http://localhost:8080/jorge-funding in your browser and click "Subscribe".

### 4. Test it
```bash
curl -d "Test notification" http://localhost:8080/jorge-funding
```

You should see a desktop notification pop up.

## How It Works

- A funding monitor runs automatically every 15 minutes
- When a startup announces new funding, you get a push notification
- Each notification includes: company name, amount raised, founder contact, LinkedIn URL
- Click the notification to open the full research report

## Notification Buttons

Each alert has clickable action buttons:
- **Open Report** — opens the deep research report in Google Drive
- **News Article** — opens the original funding announcement
- **Founder LinkedIn** — opens the founder's personal LinkedIn profile

## Files

- `docker-compose.yml` — Docker setup (runs ntfy server)
- `server.yml` — ntfy server config
- `ntfy_desktop_listener.py` — Optional: native Windows desktop notifications (no browser needed)

## Optional: Native Desktop Notifications (Windows)

If you want notifications even when the browser is closed:

```bash
pip install plyer requests
python ntfy_desktop_listener.py --topic jorge-funding
```

To auto-start on Windows boot:
```bash
python ntfy_desktop_listener.py --topic jorge-funding --startup-install
```

## Support

Contact Florian for any issues.
