"""Run-all entrypoint for the Soil Sensor Dashboard project.

This script loads environment configuration (from a local .env if present),
then starts three components:
 - FastAPI server (uvicorn subprocess)
 - Serial bridge (dashboard.serial_reader.main)
 - Telegram bot (dashboard.bot.bot.main)

Usage:
  python run_all.py            # loads .env (if present) and starts components
  python run_all.py --no-bot   # don't start the Telegram bot
  python run_all.py --no-serial# don't start the serial bridge
    python run_all.py --public   # expose dashboard over internet (default: cloudflare)

Control the configuration via a `.env` file in `dashboard/.env` or environment variables.
See `dashboard/.env.example` for available options.
"""
import os
import sys
import time
import argparse
import subprocess
import multiprocessing
import re
from dotenv import load_dotenv
import requests


def start_ngrok_tunnel(port):
    """Start an ngrok HTTP tunnel to the dashboard and return the tunnel object.

    Returns:
        A tunnel object when successful, otherwise None.
    """
    try:
        from pyngrok import ngrok
    except Exception as e:
        print(f"⚠ Could not import pyngrok: {e}")
        print("  Install it with: pip install pyngrok")
        return None

    auth_token = os.environ.get('NGROK_AUTHTOKEN', '').strip()
    if auth_token:
        try:
            ngrok.set_auth_token(auth_token)
        except Exception as e:
            print(f"⚠ Failed to set NGROK_AUTHTOKEN: {e}")

    try:
        # Tunnel to local dashboard port. Use localhost even when uvicorn listens on 0.0.0.0.
        tunnel = ngrok.connect(str(port), "http")
        public_url = getattr(tunnel, 'public_url', None)
        if public_url:
            print(f"\n🌍 Public dashboard URL: {public_url}")
            print("   You can open this URL from any network (home/mobile/etc).")
            print("   Keep your DASHBOARD_API_KEY secret before sharing this URL.\n")
            os.environ['DASHBOARD_PUBLIC_URL'] = public_url
        return tunnel
    except Exception as e:
        print(f"⚠ Failed to start ngrok tunnel: {e}")
        return None


def start_cloudflare_tunnel(port, timeout_seconds=25):
    """Start a Cloudflare quick tunnel and return (process, public_url).

    Requires cloudflared to be installed and available in PATH, or set
    CLOUDFLARED_BIN to the executable path.
    """
    cloudflared_bin = os.environ.get('CLOUDFLARED_BIN', 'cloudflared').strip() or 'cloudflared'
    local_url = f'http://127.0.0.1:{port}'
    cmd = [cloudflared_bin, 'tunnel', '--url', local_url, '--no-autoupdate']
    print('Starting Cloudflare tunnel:', ' '.join(cmd))

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError:
        print('⚠ cloudflared not found in PATH.')
        print('  Install it: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/')
        print('  Or set CLOUDFLARED_BIN to the full executable path.')
        return None, None
    except Exception as e:
        print(f'⚠ Failed to start cloudflared: {e}')
        return None, None

    pattern = re.compile(r'https://[-a-zA-Z0-9]+\.trycloudflare\.com')
    public_url = None
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        if proc.poll() is not None:
            print(f'⚠ cloudflared exited early with code {proc.returncode}')
            return None, None

        line = proc.stdout.readline() if proc.stdout else ''
        if not line:
            time.sleep(0.1)
            continue

        line = line.strip()
        match = pattern.search(line)
        if match:
            public_url = match.group(0)
            break

    if not public_url:
        print(f'⚠ Could not detect Cloudflare public URL within {timeout_seconds}s')
        print('  cloudflared may still be starting; check process output/logs.')
        return proc, None

    print(f"\n🌍 Public dashboard URL: {public_url}")
    print('   Tunnel provider: cloudflare')
    print('   You can open this URL from any network (home/mobile/etc).')
    print('   Keep your DASHBOARD_API_KEY secret before sharing this URL.\n')
    os.environ['DASHBOARD_PUBLIC_URL'] = public_url
    return proc, public_url


def stop_ngrok_tunnel(tunnel):
    if not tunnel:
        return
    try:
        from pyngrok import ngrok
        public_url = getattr(tunnel, 'public_url', None)
        if public_url:
            ngrok.disconnect(public_url)
        ngrok.kill()
    except Exception:
        # best-effort cleanup
        pass


def stop_cloudflare_tunnel(proc):
    if not proc:
        return
    try:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def load_config(env_path=None):
    loaded_files = []
    # load .env from dashboard/ if exists, then project root
    if env_path and os.path.exists(env_path):
        load_dotenv(env_path, override=False)
        loaded_files.append(env_path)
    else:
        # common places
        root_env = os.path.join(os.path.dirname(__file__), '.env')
        dashboard_env = os.path.join(os.path.dirname(__file__), 'dashboard', '.env')
        if os.path.exists(root_env):
            load_dotenv(root_env, override=False)
            loaded_files.append(root_env)
        if os.path.exists(dashboard_env):
            load_dotenv(dashboard_env, override=False)
            loaded_files.append(dashboard_env)
    return loaded_files


def wait_for_api_ready(host, port, timeout_seconds=30):
    """Wait for the API server to be ready to accept connections.
    
    Args:
        host: API host
        port: API port
        timeout_seconds: Maximum seconds to wait before giving up
        
    Returns:
        True if API became ready, False if timeout
    """
    url = f"http://{host}:{port}/docs"  # Check if the API docs endpoint is available
    start_time = time.time()
    
    while time.time() - start_time < timeout_seconds:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code < 500:  # Any response that's not 5xx indicates server is up
                print(f"✓ API is ready (status: {response.status_code})")
                return True
        except (requests.ConnectionError, requests.Timeout, requests.RequestException):
            # Server not ready yet
            pass
        
        time.sleep(0.5)
    
    print(f"⚠ API did not become ready within {timeout_seconds} seconds")
    return False


def is_raspberry_pi() -> bool:
    """Best-effort Raspberry Pi detection.

    Checks for common Pi indicators (device-tree model, /proc/cpuinfo, or ARM/aarch
    in platform.machine()). Returns True when likely running on a Pi.
    """
    try:
        if os.path.exists('/proc/device-tree/model'):
            try:
                with open('/proc/device-tree/model', 'r', encoding='utf-8', errors='ignore') as f:
                    if 'raspberry' in f.read().lower():
                        return True
            except Exception:
                pass
        if os.path.exists('/proc/cpuinfo'):
            try:
                with open('/proc/cpuinfo', 'r', encoding='utf-8', errors='ignore') as f:
                    txt = f.read().lower()
                    if 'raspberry' in txt or 'bcm' in txt:
                        return True
            except Exception:
                pass
        import platform
        m = (platform.machine() or '').lower()
        if m.startswith('arm') or m.startswith('aarch'):
            return True
    except Exception:
        pass
    return False


def start_uvicorn(host, port, extra_env=None):
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    cmd = [sys.executable, '-m', 'uvicorn', 'dashboard.backend.app:app', '--host', host, '--port', str(port)]
    print('Starting uvicorn:', ' '.join(cmd))
    p = subprocess.Popen(cmd, env=env)
    return p


def run_serial_process():
    # import inside function so environment is ready
    try:
        from dashboard import serial_reader
        serial_reader.main()
    except Exception as e:
        print('Serial bridge exited with error:', e)


def run_bot_process():
    try:
        from dashboard.bot import bot as tbot
        tbot.main()
    except Exception as e:
        print('Telegram bot exited with error:', e)


def run_simulator_process():
    try:
        from dashboard import simulated_sensor
        simulated_sensor.main()
    except Exception as e:
        print('Simulator exited with error:', e)


def main():
    parser = argparse.ArgumentParser(description='Run all Soil Sensor Dashboard components')
    parser.add_argument('--no-bot', action='store_true', help="Don't start Telegram bot")
    parser.add_argument('--no-serial', action='store_true', help="Don't start serial bridge")
    parser.add_argument('--simulate', action='store_true', help='Start simulated sensor instead of real serial')
    parser.add_argument('--public', action='store_true', help='Expose dashboard over the internet using a public tunnel')
    parser.add_argument('--public-provider', choices=['ngrok', 'cloudflare'], help='Public tunnel provider to use')
    parser.add_argument('--env', help='Path to .env file to load')
    args = parser.parse_args()

    loaded_env_files = load_config(args.env)
    if loaded_env_files:
        print('Loaded env file(s):', ', '.join(loaded_env_files))
    else:
        print('No .env file found; using existing environment variables/defaults.')

    current_modbus_map = os.environ.get('MODBUS_MAP', '')
    if current_modbus_map:
        print('Effective MODBUS_MAP:', current_modbus_map)
    else:
        print('Effective MODBUS_MAP: <not set> (serial_reader will use single-field defaults)')

    HOST = os.environ.get('DASHBOARD_HOST', '0.0.0.0')
    PORT = int(os.environ.get('DASHBOARD_PORT', '8001'))

    # Accept either TELEGRAM_TOKEN or TELEGRAM_BOT_TOKEN for compatibility
    telegram_token = os.environ.get('TELEGRAM_TOKEN') or os.environ.get('TELEGRAM_BOT_TOKEN')
    # Auto-skip starting the Telegram bot on Raspberry Pi to avoid running two bot
    # processes (the main.py bot and the dashboard bot) for the same token.
    # Override with FORCE_START_BOT_ON_PI=1 to allow starting the bot on Pi.
    start_bot = not args.no_bot and telegram_token
    if is_raspberry_pi():
        force_flag = os.environ.get('FORCE_START_BOT_ON_PI', '0')
        if force_flag != '1':
            if start_bot:
                print('ℹ️ Detected Raspberry Pi — skipping Telegram bot process to avoid conflicts. Set FORCE_START_BOT_ON_PI=1 to override.')
            start_bot = False
    serial_port = os.environ.get('SERIAL_PORT')
    # On Raspberry Pi, default to ttyAMA0 for stable UART behavior on newer models.
    if not serial_port and is_raspberry_pi():
        serial_port = '/dev/ttyAMA0'
        os.environ['SERIAL_PORT'] = serial_port
        print('ℹ️ SERIAL_PORT not set; defaulting to /dev/ttyAMA0 on Raspberry Pi')

    start_serial = not args.no_serial and bool(serial_port)

    # Simulator policy:
    # - --simulate always enables simulator (explicit override)
    # - SIMULATE_SENSOR=1 enables simulator only when no real serial port is configured
    # This prevents accidentally using simulated data when a real sensor is available.
    simulate_env = os.environ.get('SIMULATE_SENSOR') == '1'
    start_simulator = args.simulate or (simulate_env and not start_serial)
    public_enabled = args.public or os.environ.get('ENABLE_PUBLIC_DASHBOARD', '0') == '1'
    public_provider = (
        args.public_provider
        or os.environ.get('PUBLIC_TUNNEL_PROVIDER', 'cloudflare')
    ).strip().lower()

    # Export API base and readings endpoint variables expected by serial_reader, bot and simulator
    base_url = f'http://127.0.0.1:{PORT}'
    os.environ.setdefault('DASHBOARD_API_BASE', base_url)
    os.environ.setdefault('DASHBOARD_API_URL', base_url + '/api/readings')

    uvicorn_proc = start_uvicorn(HOST, PORT)
    
    # Wait for API to be ready before starting dependent processes
    wait_for_api_ready('127.0.0.1', PORT)

    public_tunnel = None
    public_tunnel_proc = None
    if public_enabled:
        if public_provider == 'cloudflare':
            public_tunnel_proc, _ = start_cloudflare_tunnel(PORT)
        else:
            public_tunnel = start_ngrok_tunnel(PORT)

    procs = []

    if start_serial and not start_simulator:
        p = multiprocessing.Process(target=run_serial_process, name='serial_bridge')
        p.start()
        procs.append(p)
        print('Started serial bridge process (pid=%s)' % p.pid)
    elif start_simulator:
        # start simulator instead of serial bridge
        p = multiprocessing.Process(target=run_simulator_process, name='simulated_sensor')
        p.start()
        procs.append(p)
        print('Started simulated sensor process (pid=%s)' % p.pid)
    else:
        print('Serial bridge not started (SERIAL_PORT not set or --no-serial used)')

    if start_bot:
        p = multiprocessing.Process(target=run_bot_process, name='telegram_bot')
        p.start()
        procs.append(p)
        print('Started telegram bot process (pid=%s)' % p.pid)
    else:
        print('Telegram bot not started (TELEGRAM_TOKEN not set or --no-bot used)')

    try:
        while True:
            time.sleep(1)
            # if uvicorn died, break
            if uvicorn_proc.poll() is not None:
                print('Uvicorn process ended with code', uvicorn_proc.returncode)
                break
            # respawn behavior could be added here
    except KeyboardInterrupt:
        print('\nShutting down...')
    finally:
        if public_tunnel or public_tunnel_proc:
            print('Stopping public tunnel...')
            if public_tunnel:
                stop_ngrok_tunnel(public_tunnel)
            if public_tunnel_proc:
                stop_cloudflare_tunnel(public_tunnel_proc)
        # Terminate child processes
        if uvicorn_proc and uvicorn_proc.poll() is None:
            print('Terminating uvicorn...')
            uvicorn_proc.terminate()
        for p in procs:
            if p.is_alive():
                print('Terminating', p.name)
                p.terminate()
                p.join(timeout=5)


if __name__ == '__main__':
    main()

# add improvement to the back side of the server to handle bundle of data and store in the 
# database with timestamp, and add endpoint to retrieve historical data with pagination and filtering by date range.
