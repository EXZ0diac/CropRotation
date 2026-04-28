# CropRotationAI

CropRotationAI is a toolkit for reading soil/sensor data, running a dashboard, and training/serving ML models to assist with crop-rotation and crop-prediction workflows.

This README provides a concise setup guide, quick run commands for the main components, and where to find artifacts.

## Quick summary
- Dashboard & sensor bridge: `run_all.py` (typically run on the device attached to sensors — e.g. Raspberry Pi).
- Model runner & utilities: `main.py` and other scripts (use these to run model-related tasks or integrations).
- Model training: training scripts such as `model_training.py` (produce artifacts in `model/`).

- ## Prerequisites
- Python 3.11.9 required (create a virtual environment using this exact version for compatibility with wheels and TensorFlow builds used by this project).
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

Note: TensorFlow is conditionally specified in `requirements.txt` for Python version compatibility. If you run into wheel availability issues, use the appropriate `tf-nightly` wheel or use the recommended Python version above.

## Configuration
Place environment variables in a `.env` file (project root or `dashboard/.env`) or export them in your shell. Common variables used by the dashboard and `run_all.py`:

- `DASHBOARD_API_KEY` — API key used by clients and scripts (default: `dev-token`).
- `DASHBOARD_HOST`, `DASHBOARD_PORT` — dashboard binding (defaults: `0.0.0.0:8001`).
- `SERIAL_PORT` — serial device path (e.g. `/dev/ttyUSB0` or `COM3`). On Raspberry Pi the code defaults to `/dev/ttyAMA0` when no serial port is configured.
- `SIMULATE_SENSOR` — set to `1` to prefer the simulated sensor when a real serial port is not configured.
- `ENABLE_PUBLIC_DASHBOARD`, `PUBLIC_TUNNEL_PROVIDER` — enable public dashboard access (`cloudflare` or `ngrok`).
- `NGROK_AUTHTOKEN` / `CLOUDFLARED_BIN` — provider-specific options for public tunnels.

Security note: the API accepts `x-api-key` headers for protected endpoints. For Server-Sent Events (SSE) the frontend adds the API key as an `api_key` query parameter because browsers' EventSource cannot set custom headers. For local/LAN use the server allows connections from RFC1918 addresses without an API key for convenience, but if you expose the dashboard publicly, set a strong `DASHBOARD_API_KEY`.

## Running the main components

1) Dashboard + sensor bridge (recommended on the device connected to sensors):

```bash
python run_all.py            # runs dashboard (uvicorn) + serial bridge; prefers real serial when available
python run_all.py --no-serial # skip starting the serial bridge
python run_all.py --simulate # run the simulator instead of real serial
python run_all.py --public   # enable public tunnel (cloudflare by default)
python run_all.py --public --public-provider ngrok  # force ngrok provider
python run_all.py --env dashboard/.env  # load a specific .env
```

2) Model runner / utilities (local or cloud)

```bash
python main.py   # run model utilities and other non-dashboard tasks
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
- `model/` — saved model files and preprocessing objects used by the model runner and API.
- `artifacts/` — exported analysis files (e.g. `correlation_matrix.csv`).
- `model_dataset_*` — various exported datasets and model snapshots.

## run_all.py — what it does (detailed)

`run_all.py` is the primary orchestration entrypoint used to run the dashboard and sensor bridge together. Key behaviors:

- Loads environment configuration from a `.env` file (project root or `dashboard/.env`) when present.
- Starts the FastAPI server via `uvicorn` pointing at `dashboard.backend.app:app` (this serves the REST API and static frontend files).
- Waits for the API docs endpoint `/docs` to become available before starting dependent processes.
- Optionally starts a serial bridge process that reads sensor data and posts readings to the API (`/api/readings`). The serial bridge is implemented in `dashboard/serial_reader.py`.
- Supports a simulator process (`dashboard/simulated_sensor.py`) when `--simulate` or `SIMULATE_SENSOR=1` is used.
- Provides options to expose the dashboard publicly via a tunnel: Cloudflare (`cloudflared`) or ngrok (via `pyngrok`). The public URL is exported as `DASHBOARD_PUBLIC_URL` when created.
- Defaults and platform-specific behavior: on Raspberry Pi it auto-detects the platform and defaults `SERIAL_PORT` to `/dev/ttyAMA0` if unset; it also avoids starting conflicting processes by design.

Command-line flags: `--no-serial`, `--simulate`, `--public`, `--public-provider`, and `--env` (path to a .env file).

Exit and cleanup: `run_all.py` terminates child processes and stops any public tunnel on Ctrl+C.

## Dashboard architecture (frontend / backend)

Overview:
- Backend: `dashboard/backend/app.py` — a FastAPI application exposing REST endpoints and Server-Sent Events (SSE) for live updates. It initializes a small SQLite database (`sqlite:///./dashboard.db`) via SQLAlchemy and stores readings and other models defined in `dashboard/backend/models.py`.
- Frontend: static Progressive Web App files in `dashboard/frontend/` (HTML, JS, CSS). The backend mounts this folder so the UI is served at the same host/port as the API.

How they interact:
- Data flow: the serial bridge (or simulator) POSTs readings to `POST /api/readings` with the `x-api-key` header. The backend saves the reading to the database and broadcasts it to connected browser clients via SSE at `/api/stream`.
- Live updates: the frontend uses EventSource to connect to `/api/stream` (with `api_key` query param when needed) and updates charts and latest-reading cards in real time.
- REST endpoints: the frontend calls endpoints such as `/api/readings/latest`, `/api/readings/history`, `/api/predict`, and `/api/commands/*` to populate UI views and send user commands.
- Prediction: prediction artifacts (scalers, label encoders, Keras/TensorFlow models) are loaded on demand by the backend from the `model/` directory (see `dashboard/backend/app.py` `_load_prediction_artifacts`). Model predictions are exposed via `/api/predict` and `/api/predict/history`.

Security & API keys:
- The backend protects sensitive endpoints with `DASHBOARD_API_KEY` (default `dev-token`). For development and LAN use the SSE endpoint allows local connections without a key to make the UI work conveniently on private networks; when you expose the dashboard publicly, set a strong `DASHBOARD_API_KEY`.

Frontend details:
- Files: `dashboard/frontend/index.html`, `app.js`, `prediction.js`, `style.css`, and pages like `history.html` and `prediction.html`.
- Behavior: `app.js` discovers `API_BASE` from a `meta` tag or the page origin, stores the API key in `localStorage`, polls endpoints for history and latest values, and uses SSE to receive live readings and push them into charts.

## Troubleshooting & tips
- If `dashboard/backend` logs complain about missing model artifacts, run the training scripts and ensure `model/` contains `scaler.save` and `label_encoder.save` (and model files) in the expected subdirectory.
- If SSE fails in the browser, check DevTools console for the SSE URL and ensure the `api_key` query param or header is correct.
- For a Raspberry Pi deployment, prefer Cloudflare tunnels (lower friction). If using ngrok, set `NGROK_AUTHTOKEN` for better stability.

## Next steps I can do for you
- Split this into per-component READMEs, add `CONTRIBUTING.md`, or add a short `dashboard/README.md` with Pi-specific notes. Tell me which you prefer.

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