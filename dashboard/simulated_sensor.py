"""Simulated sensor that periodically POSTs fake NPK, pH, EC, humidity and temperature readings
to the dashboard API. Useful for testing without hardware.

Configuration via environment variables (or copy into `dashboard/.env`):
    DASHBOARD_API_URL  - full API base URL, e.g. http://127.0.0.1:8000/api/readings
    DASHBOARD_API_KEY  - API key header value to use
    SIM_INTERVAL       - seconds between readings (default 60)
    SIM_JITTER         - max random jitter in seconds to add/subtract (default 2)
"""
import os
import time
import random
import requests

_env_api = os.getenv('DASHBOARD_API_URL')
_env_base = os.getenv('DASHBOARD_API_BASE')
if _env_api:
    API_URL = _env_api
else:
    base = _env_base or 'http://127.0.0.1:8000'
    API_URL = base.rstrip('/') + '/api/readings'
API_KEY = os.getenv('DASHBOARD_API_KEY', 'dev-token')
# default to 60 seconds between readings (1 minute). Override with SIM_INTERVAL env var.
SIM_INTERVAL = float(os.getenv('SIM_INTERVAL', '60'))
SIM_JITTER = float(os.getenv('SIM_JITTER', '2'))


def gen_reading():
    # Simple ranges: N,P,K (mg/kg or relative), pH 5.5-8, EC 0.2-2.5, humidity 10-90%, temp 5-35C
    base = {
        'np_n': round(random.uniform(0.5, 3.5), 2),
        'np_p': round(random.uniform(0.1, 1.5), 2),
        'np_k': round(random.uniform(0.2, 2.0), 2),
        'ph': round(random.uniform(5.5, 8.0), 2),
        'ec': round(random.uniform(0.2, 2.5), 2),
        'humidity': round(random.uniform(20, 90), 1),
        'temperature': round(random.uniform(10, 35), 1),
    }
    return base


def main():
    print('Starting simulated sensor ->', API_URL)

    # Wait for the server to be reachable before sending data to avoid
    # repeated connection refused errors when the backend is still starting.
    def wait_for_server(timeout=60, interval=2):
        total = 0
        while total < timeout:
            try:
                r = requests.get(API_URL.replace('/api/readings', '/api/readings/latest'), timeout=5, headers={'x-api-key': API_KEY})
                if r.status_code in (200, 404):
                    return True
            except Exception:
                pass
            time.sleep(interval)
            total += interval
        return False

    if not wait_for_server(timeout=60, interval=2):
        print("Warning: dashboard API did not respond within timeout; simulator will still attempt to post and will retry on error.")

    while True:
        try:
            payload = gen_reading()
            print('SIM ->', payload)
            resp = requests.post(API_URL, json=payload, headers={'x-api-key': API_KEY}, timeout=10)
            print('POST', getattr(resp, 'status_code', 'no-response'))
        except Exception as e:
            print('Error posting simulated reading:', e)
        interval = SIM_INTERVAL + random.uniform(-SIM_JITTER, SIM_JITTER)
        if interval < 0.5:
            interval = 0.5
        time.sleep(interval)


if __name__ == '__main__':
    main()
