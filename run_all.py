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

Control the configuration via a `.env` file in `dashboard/.env` or environment variables.
See `dashboard/.env.example` for available options.
"""
import os
import sys
import time
import argparse
import subprocess
import multiprocessing
from dotenv import load_dotenv


def load_config(env_path=None):
    # load .env from dashboard/ if exists, then project root
    if env_path and os.path.exists(env_path):
        load_dotenv(env_path, override=False)
    else:
        # common places
        root_env = os.path.join(os.path.dirname(__file__), '.env')
        dashboard_env = os.path.join(os.path.dirname(__file__), 'dashboard', '.env')
        if os.path.exists(root_env):
            load_dotenv(root_env, override=False)
        if os.path.exists(dashboard_env):
            load_dotenv(dashboard_env, override=False)


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
    parser.add_argument('--env', help='Path to .env file to load')
    args = parser.parse_args()

    load_config(args.env)

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
    start_serial = not args.no_serial and serial_port
    # Simulator: explicit flag or env var SIMULATE_SENSOR=1; also allow starting simulator when no SERIAL_PORT configured
    start_simulator = args.simulate or (os.environ.get('SIMULATE_SENSOR') == '1') or (not serial_port and args.simulate)

    # Export API base and readings endpoint variables expected by serial_reader, bot and simulator
    base_url = f'http://127.0.0.1:{PORT}'
    os.environ.setdefault('DASHBOARD_API_BASE', base_url)
    os.environ.setdefault('DASHBOARD_API_URL', base_url + '/api/readings')

    uvicorn_proc = start_uvicorn(HOST, PORT)

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
