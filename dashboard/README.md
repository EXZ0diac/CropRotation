# Soil Sensor Dashboard (PWA) + Telegram backup

This folder provides a simple FastAPI backend, a frontend dashboard (PWA) and helper scripts to bridge an RS485 serial soil sensor and a Telegram backup bot.

Quick overview
- `dashboard/backend/app.py` - FastAPI backend exposing `/api/readings` and history endpoints.
- `dashboard/frontend/` - static PWA frontend (HTML/JS/CSS) using Chart.js.
- `dashboard/serial_reader.py` - reads serial lines (JSON or CSV) and POSTs to backend.
- `dashboard/bot/bot.py` - Telegram bot (polling) that queries the backend.

Requirements
- Python packages in the repository `requirements.txt`. Install with:

```powershell
python -m pip install -r requirements.txt
```

Running the backend

Set an API key (recommended):

```powershell
 # in PowerShell, set the envvar and run uvicorn
 $env:DASHBOARD_API_KEY = 'super-secret'
 python -m uvicorn dashboard.backend.app:app --host 0.0.0.0 --port 8000
```

Serving the frontend

The frontend is static and expects the API to be available at the same host on port 8000. For development you can serve it using a simple static server or configure the FastAPI app to serve static files.

Running the serial bridge

Configure the serial port and run:

```powershell
 # example PowerShell usage
 $env:SERIAL_PORT = 'COM3'
 $env:BAUDRATE = '9600'
 $env:DASHBOARD_API_URL = 'http://127.0.0.1:8000/api/readings'
 $env:DASHBOARD_API_KEY = 'super-secret'
 python dashboard/serial_reader.py
```

Telegram bot

Set the bot token and start it:

```powershell
 $env:TELEGRAM_TOKEN = '<your-token>'
 $env:DASHBOARD_API_URL = 'http://127.0.0.1:8000'
 $env:DASHBOARD_API_KEY = 'super-secret'
 python dashboard/bot/bot.py
```

Android app (recommended approach)

The frontend is a PWA. For a fast Android app, install the PWA from Chrome (Add to Home screen) or wrap it with Capacitor/Android WebView. A minimal approach:

- Host the frontend at a reachable URL (or serve from the device)
- Use Capacitor to build an APK that loads the PWA URL in a WebView.

Security notes
- Protect `DASHBOARD_API_KEY` and restrict access in production.
- If exposing the backend to the internet, use HTTPS and firewall rules.

Next steps (optional)
- Add user authentication, alerts, thresholds, and push notifications.
- Add device gateway to forward commands to RS485 network.
