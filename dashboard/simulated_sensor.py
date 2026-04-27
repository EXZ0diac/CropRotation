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
from itertools import cycle

_env_api = os.getenv('DASHBOARD_API_URL')
_env_base = os.getenv('DASHBOARD_API_BASE')
if _env_api:
    API_URL = _env_api
else:
    base = _env_base or 'http://127.0.0.1:8000'
    API_URL = base.rstrip('/') + '/api/readings'
API_KEY = os.getenv('DASHBOARD_API_KEY', 'dev-token')
# default to 5 seconds between readings for testing. Override with SIM_INTERVAL env var.
SIM_INTERVAL = float(os.getenv('SIM_INTERVAL', '5'))
SIM_JITTER = float(os.getenv('SIM_JITTER', '2'))


ALT_PROFILES = [
    {
        'name': 'Chili',
        'np_n': 71.11,
        'np_p': 54.90,
        'np_k': 197.95,
        'ph': 6.51,
        'ec': 1.42,
        'humidity': 70.55,
        'temperature': 28.25,
    },
    {
        'name': 'Eggplant',
        'np_n': 71.17,
        'np_p': 45.20,
        'np_k': 216.79,
        'ph': 5.95,
        'ec': 1.58,
        'humidity': 62.32,
        'temperature': 25.84,
    },
]


def _with_jitter(value, delta, minimum=None, maximum=None, decimals=2):
    jittered = value + random.uniform(-delta, delta)
    if minimum is not None:
        jittered = max(minimum, jittered)
    if maximum is not None:
        jittered = min(maximum, jittered)
    return round(jittered, decimals)


_profile_cycle = cycle(ALT_PROFILES)


def gen_reading():
    profile = next(_profile_cycle)
    # Keep the readings close to real Chili/Eggplant samples so the model
    # alternates cleanly and the prediction page shows both class probabilities.
    return {
        'np_n': _with_jitter(profile['np_n'], 1.25, minimum=0.0, decimals=2),
        'np_p': _with_jitter(profile['np_p'], 1.25, minimum=0.0, decimals=2),
        'np_k': _with_jitter(profile['np_k'], 4.0, minimum=0.0, decimals=2),
        'ph': _with_jitter(profile['ph'], 0.12, minimum=0.0, maximum=14.0, decimals=2),
        'ec': _with_jitter(profile['ec'], 0.08, minimum=0.0, decimals=2),
        'humidity': _with_jitter(profile['humidity'], 1.0, minimum=0.0, maximum=100.0, decimals=1),
        'temperature': _with_jitter(profile['temperature'], 0.7, minimum=-20.0, maximum=60.0, decimals=1),
        'crop_hint': profile['name'],
    }


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
            crop_hint = payload.pop('crop_hint', None)
            print('SIM ->', crop_hint, payload)
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
