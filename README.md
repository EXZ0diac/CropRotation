# CropRotationAI

CropRotationAI is a toolkit for reading soil and sensor data, running a dashboard, and training or serving machine-learning models for crop-rotation and crop-prediction workflows.

## Quick Summary
- `run_all.py` starts the dashboard backend, serves the frontend, and launches the sensor bridge or simulator.
- `main.py` and the training scripts support model-related tasks and artifact generation.
- `model_training.py` and the other `train_*.py` scripts generate model artifacts saved in `model/`.

## Requirements
- Python 3.11.9
- A virtual environment
- Dependencies from `requirements.txt`

## WSL First
This project is used mostly from WSL, so the commands below are written with that in mind.

Recommended WSL workflow:
- Open the repo from your WSL shell.
- Create and activate the virtual environment inside WSL.
- Run `run_all.py` from WSL for the dashboard, backend, and sensor bridge.
- Use PowerShell only when you specifically need Windows-native tools or paths.

## Setup

WSL / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If you use a `.env` file, place it in the project root or in `dashboard/.env`.

## What `run_all.py` Does
`run_all.py` is the main orchestration entrypoint.

It does the following:
- loads environment values from `.env` files when present
- starts the FastAPI backend through `uvicorn` using `dashboard.backend.app:app`
- waits for the backend to become ready before starting other processes
- starts the serial sensor bridge when a serial port is available
- can start the simulator instead of the real sensor when `--simulate` is used
- can expose the dashboard publicly when `--public` is enabled
- cleans up child processes and tunnels on exit

Useful flags:
- `--no-serial` skips the serial bridge
- `--simulate` uses the simulated sensor
- `--public` enables a public tunnel for the dashboard
- `--public-provider` selects `cloudflare` or `ngrok`
- `--env` loads a specific `.env` file

Example commands:

```bash
python run_all.py
python run_all.py --simulate
python run_all.py --no-serial
python run_all.py --public
python run_all.py --public --public-provider ngrok
python run_all.py --env dashboard/.env
```

When running in WSL, prefer the `python3` command and Linux paths. If you need to access Windows-mounted files, use the `/mnt/c/...` path style.

## Dashboard Architecture

### Backend
The backend lives in `dashboard/backend/app.py` and is built with FastAPI. It:
- exposes REST endpoints for readings, predictions, soil commands, and plant history
- stores sensor data in a SQLite database through SQLAlchemy
- streams live sensor updates using Server-Sent Events
- loads prediction artifacts from `model/` when crop predictions are requested

### Frontend
The frontend lives in `dashboard/frontend/` and is a static web app served by the backend. It includes:
- `index.html`
- `history.html`
- `prediction.html`
- `commands.html`
- `app.js`
- `prediction.js`
- `commands.js`
- `style.css`

The frontend:
- reads the API base URL from the page or the current origin
- calls backend endpoints to load readings and prediction data
- listens to the live SSE stream for real-time updates
- updates charts, tables, and prediction panels in the browser

### How they work together
1. The sensor bridge or simulator sends readings to `POST /api/readings`.
2. The backend saves the reading to SQLite and broadcasts it over `/api/stream`.
3. The frontend receives the event stream and updates the dashboard live.
4. The frontend can also request history, latest readings, and crop predictions from the REST API.

## Run Options

Start the dashboard and sensor bridge:

```bash
python run_all.py
```

From WSL, this is the preferred way to run the project.

Use the simulated sensor:

```bash
python run_all.py --simulate
```

Expose the dashboard publicly:

```bash
python run_all.py --public
```

Train or regenerate model artifacts:

```bash
python model_training.py
python train_on_prepared.py
```

## Data and Artifacts
- `model/` stores trained model files and preprocessing artifacts.
- `artifacts/` stores analysis outputs such as correlation data.
- `dashboard/data/` stores dashboard data files such as readings exports.

## Troubleshooting
- If the backend cannot find model artifacts, rerun the training scripts and confirm the expected files exist in `model/`.
- If live updates do not appear, check the browser console and confirm the frontend can reach `/api/stream`.
- If you expose the dashboard publicly, make sure `DASHBOARD_API_KEY` is set to a strong value.

## Notes
- The project is designed to run the dashboard, backend, and sensor bridge together.
- The frontend and backend share the same host and port when served by `run_all.py`.
- The dashboard is intended to provide live monitoring, history, and crop prediction tools in one place.
