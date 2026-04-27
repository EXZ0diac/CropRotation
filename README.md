# CropRotationAI — Quick runbook

This README explains the three main entrypoints in this repository and how to run them, with common environment variables and Raspberry Pi deployment notes.

## Overview

- `run_all.py` — Orchestration script that starts the dashboard (FastAPI/uvicorn), the serial bridge (real sensor), and optionally the dashboard's Telegram bot. Intended to run on a host that directly connects to the soil sensor (e.g., a Raspberry Pi).

- `main.py` — The Telegram bot and ML model runner. This script runs the crop prediction bot, the Flask webhook endpoint, and the crop prediction model (Keras/TFLite). Typical use: run this on a machine reachable from Telegram (laptop or cloud) so it can receive updates via webhook. It contains logic to detect Raspberry Pi and default to polling/local mode there.

- `model_training.py` — Notebooks/scripting entrypoint for training or re-training the crop rotation model. Use this to produce model artifacts (Keras `.h5`/`.keras`, TFLite `.tflite`, `scaler.save`, `label_encoder.save`) placed in the `model/` directory.

## High-level deployment pattern (recommended)

- Raspberry Pi (or the machine connected to the soil sensor): run `run_all.py` to host the dashboard (uvicorn) and the serial-to-dashboard bridge. By default the Pi will NOT start the dashboard's Telegram bot to avoid multiple processes using the same Telegram token.

- Laptop or cloud server: run `main.py` to run the Telegram bot which receives Telegram updates. `main.py` can create an ngrok tunnel (if `USE_WEBHOOK=1`) so Telegram can reach your laptop behind NAT.

This separation avoids running two processes that both receive Telegram updates for the same token, which causes conflicts.

## `run_all.py` — usage and env

Purpose: start dashboard components together for local deployments.

Usage:

PowerShell (Windows) / Bash (Linux):

```bash
# From repo root
python run_all.py            # load .env if present in project/dashboad and start components
python run_all.py --no-bot   # explicitly don't start the dashboard bot
python run_all.py --no-serial # don't start serial bridge
python run_all.py --simulate  # start simulator instead of real serial
python run_all.py --env /path/to/.env  # load a specific .env
```

Important environment variables used by `run_all.py`:

- `DASHBOARD_HOST` — host for uvicorn (default `0.0.0.0`).
- `DASHBOARD_PORT` — port for uvicorn (default `8001`).
- `TELEGRAM_TOKEN` / `TELEGRAM_BOT_TOKEN` — when set, `run_all.py` can start the dashboard's Telegram bot unless skipped.
- `SERIAL_PORT` — serial device for the sensor bridge.
- `SIMULATE_SENSOR` — if set to `1` or `--simulate` is passed, the simulated sensor runs instead of serial bridge.
- `FORCE_START_BOT_ON_PI` — if running on a Raspberry Pi, `run_all.py` will skip starting the bot to avoid conflicts. Set this to `1` to override and force the bot to start on Pi.
- `ENABLE_PUBLIC_DASHBOARD` — set to `1` to expose the dashboard over the internet.
- `PUBLIC_TUNNEL_PROVIDER` — choose `cloudflare` or `ngrok` (default: `cloudflare`).
- `CLOUDFLARED_BIN` — optional full path to `cloudflared` if not in PATH.
- `NGROK_AUTHTOKEN` — optional ngrok token for better reliability and limits (only for ngrok provider).

Raspberry Pi auto-skip behavior:
- `run_all.py` includes a best-effort Pi detector. On Pi it will automatically skip starting the dashboard's Telegram bot unless `FORCE_START_BOT_ON_PI=1`.

Public internet access (Pi in garden, monitor from home):

You can expose the dashboard from the Raspberry Pi even when your phone/laptop is on a different network.

Option A (Cloudflare, one-time command):

```bash
python3 run_all.py --public
```

Option B (Cloudflare, explicit provider):

```bash
python3 run_all.py --public --public-provider cloudflare
```

Option C (via env):

```bash
export ENABLE_PUBLIC_DASHBOARD=1
export PUBLIC_TUNNEL_PROVIDER=cloudflare
python3 run_all.py
```

Option D (ngrok provider):

```bash
export ENABLE_PUBLIC_DASHBOARD=1
export PUBLIC_TUNNEL_PROVIDER=ngrok
export NGROK_AUTHTOKEN=<your-ngrok-token>   # optional but recommended
python3 run_all.py
```

When started, `run_all.py` prints a `Public dashboard URL` that you can open from anywhere.
Keep `DASHBOARD_API_KEY` private before sharing the link.

Cloudflare install note on Raspberry Pi:

Install `cloudflared` from Cloudflare docs for your distro/arch, then verify:

```bash
cloudflared --version
```

## `main.py` — usage and env

Purpose: run the Telegram bot, model loading (Keras/TFLite), and provide a Flask `/webhook` route for Telegram webhooks when using `USE_WEBHOOK=1`.

Usage (PowerShell example):

```powershell
# set bot token and run in webhook mode (creates ngrok tunnel)
$env:TELEGRAM_BOT_TOKEN = 'your_token_here'
$env:USE_WEBHOOK = '1'
python .\main.py
```

Or, run in polling/local mode (no webhook):

```powershell
$env:TELEGRAM_BOT_TOKEN = 'your_token_here'
# ensure USE_WEBHOOK is unset or '0'
$env:USE_WEBHOOK = '0'
python .\main.py
```

Key environment variables and files used by `main.py`:

- `TELEGRAM_BOT_TOKEN` — required for the Telegram bot.
- `USE_WEBHOOK` — when set to `1`, `main.py` opens an ngrok tunnel and registers a Telegram webhook; otherwise it uses polling/local mode.
- `FORCE_WEBHOOK_ON_PI` — even if `main.py` detects Raspberry Pi, setting this to `1` will allow webhook behavior on Pi (not recommended unless you know what you're doing).
- `DASHBOARD_API_BASE` — base URL of the dashboard API (default `http://127.0.0.1:8001`).
- `DASHBOARD_API_KEY` — API key used for dashboard requests (default `dev-token`).

Notes:
- `main.py` will attempt to load model artifacts from `model/` (look for `crop_rotation_model.keras`, `.h5`, or `.tflite`) and preprocessing artifacts (`scaler.save`, `label_encoder.save`).
- On Raspberry Pi the script detects the platform and will force `USE_WEBHOOK=0` by default (so it doesn't try to run ngrok/webhook on Pi). This behavior is intended to keep the Pi as the dashboard/serial host and run the bot elsewhere.

## `model_training.py` — short guide

Purpose: retrain the crop prediction model and write artifacts into `model/`.

Typical steps:

1. Prepare training data and preprocessing pipeline.
2. Run `model_training.py` (or open associated notebook if present) to train and export artifacts.

Note: the repository stores model artifacts in `model/`. The bot (`main.py`) expects preprocessing artifacts named `scaler.save` and `label_encoder.save` produced by the training pipeline.

## Example deployment (recommended)

1. On Raspberry Pi (sensor + dashboard): start dashboard and sensor bridge only — do NOT start bot there:

```bash
cd ~/CropRotationAI
# Ensure .env is set up under dashboard/ or project root
python3 run_all.py         # run_all will auto-skip the Telegram bot on Pi
```

2. On laptop (bot + webhook via ngrok): run `main.py` in webhook mode so Telegram reaches your laptop.

PowerShell example:

```powershell
cd 'C:\Users\adlir\CropRotationAI'
$env:TELEGRAM_BOT_TOKEN = 'your_token_here'
$env:USE_WEBHOOK = '1'
python .\main.py
```

This starts the Telegram bot on your laptop. `main.py` will create an ngrok tunnel and register the webhook with Telegram so updates are delivered to your laptop's Flask `/webhook` endpoint.

## Troubleshooting & tips

- If Telegram messages don't arrive, ensure only one process is handling updates for your bot token.
- If you prefer polling, set `USE_WEBHOOK=0` and ensure only one polling bot runs for the token.
- If `main.py` can't find model artifacts, run the training pipeline (`model_training.py`) and ensure artifacts are saved to the `model/` folder.
- To avoid the pyngrok dependency on Pi deployments entirely, either run `main.py` on a non-Pi or set `USE_WEBHOOK=0`.

## Contributing notes

- If you add new env vars, document them here and in `dashboard/.env.example`.
- When changing model artifact names/paths, update `main.py` so artifact detection matches the new names.

---

If you'd like, I can also:
- Add a short `dashboard/README.md` note describing the Pi auto-skip (or update it),
- Add a `CONTRIBUTING.md` with common developer commands,
- Or break this single README into per-script READMEs instead of a combined root README.

Which would you prefer?