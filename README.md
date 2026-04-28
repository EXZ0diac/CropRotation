# CropRotationAI

CropRotationAI is a toolkit for reading soil/sensor data, running a dashboard, and training/serving ML models to assist with crop-rotation and crop-prediction workflows.

This README provides a concise setup guide, quick run commands for the main components, and where to find artifacts.

## Quick summary
- Dashboard & sensor bridge: `run_all.py` (typically run on the device attached to sensors — e.g. Raspberry Pi).
- Telegram bot & model runner: `main.py` (run on a reachable machine or cloud instance; supports webhook via ngrok/cloudflare).
- Model training: training scripts such as `model_training.py` (produce artifacts in `model/`).

## Prerequisites
- Python 3.10–3.12 recommended.
- Create and activate a virtual environment and install dependencies:

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Note: TensorFlow is conditionally specified in `requirements.txt` for Python version compatibility. If you run into wheel availability issues, use the appropriate `tf-nightly` wheel or a supported Python version.

## Configuration
Place environment variables in a `.env` file or export them in your shell. Common variables:

- `TELEGRAM_BOT_TOKEN` — Telegram bot token (required for bot).
- `USE_WEBHOOK` — set to `1` to use webhook mode (requires a public tunnel), otherwise polling is used.
- `DASHBOARD_HOST`, `DASHBOARD_PORT` — dashboard binding (defaults: `0.0.0.0:8001`).
- `SERIAL_PORT` — serial device path (e.g. `/dev/ttyUSB0` or `COM3`).
- `SIMULATE_SENSOR` — set to `1` to use the simulated sensor.
- `ENABLE_PUBLIC_DASHBOARD`, `PUBLIC_TUNNEL_PROVIDER` — set to enable public dashboard access (`cloudflare` or `ngrok`).

## Running the main components

1) Dashboard + sensor bridge (recommended on the device connected to sensors):

```bash
python run_all.py            # runs dashboard + sensor bridge; auto-skips bot on Raspberry Pi
python run_all.py --no-bot   # skip the dashboard bot
python run_all.py --simulate # run the simulator instead of real serial
```

2) Telegram bot & model runner (run on a laptop or cloud instance):

Webhook mode (creates a tunnel and registers webhook):

```powershell
$env:TELEGRAM_BOT_TOKEN='your_token'
$env:USE_WEBHOOK='1'
python main.py
```

Polling/local mode:

```powershell
$env:TELEGRAM_BOT_TOKEN='your_token'
$env:USE_WEBHOOK='0'
python main.py
```

3) Train models / create artifacts:

```bash
python model_training.py
python train_on_prepared.py
```

Training scripts write model and preprocessing artifacts to `model/` (e.g. `crop_rotation_model.keras`, `scaler.save`, `label_encoder.save`). `main.py` loads these artifacts at startup.

## Tests
Run unit tests (virtualenv active):

```bash
python -m pytest -q
```

## Artifacts & locations
- `model/` — saved model files and preprocessing objects used by the bot.
- `artifacts/` — exported analysis files (e.g. `correlation_matrix.csv`).
- `model_dataset_*` — various exported datasets and model snapshots.

## Troubleshooting
- Make sure only one process uses the same Telegram token (do not run two bots for the same token).
- If `main.py` reports missing artifacts, regenerate them with the training scripts and confirm they are in `model/`.
- Prefer Cloudflare for Pi-based public tunnels; ngrok is supported but may require an auth token.

## Next steps I can do for you
- Split this into per-component READMEs, add `CONTRIBUTING.md`, or add a short `dashboard/README.md` with Pi-specific notes. Tell me which you prefer.

---

File: [README.md](README.md)

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