# CropRotationAI

CropRotationAI is a soil and crop workflow project that brings together sensor ingestion, a FastAPI dashboard backend, a browser frontend, and machine-learning utilities for crop prediction and crop-rotation analysis.

The project is designed to run well from WSL on a Windows machine, with the main orchestration happening through `run_all.py`.

## What This Project Does

At a high level, the project:
- reads soil and sensor measurements from a real serial device or a simulator
- stores readings in a local SQLite database
- serves a dashboard UI from a FastAPI backend
- streams live readings to the browser using Server-Sent Events
- loads trained model artifacts from `model/` to support crop prediction
- provides scripts for training and regenerating artifacts

## Repository Layout

Important top-level paths:
- `run_all.py` - starts the backend, sensor bridge, simulator, and public tunnel options
- `main.py` - model and utility entrypoint used by the project
- `dashboard/backend/` - FastAPI app, database layer, and API endpoints
- `dashboard/frontend/` - browser UI files served by the backend
- `dashboard/serial_reader.py` - reads from the serial sensor and posts readings to the API
- `dashboard/simulated_sensor.py` - emits synthetic readings for testing
- `model_training.py` - primary training script
- `train_*.py` - alternative training scripts for different datasets or workflows
- `model/` - stored model and preprocessing artifacts
- `artifacts/` - analysis outputs and generated reports
- `dashboard/data/` - exported dashboard data such as reading logs

## Requirements

- Python 3.11.9
- A virtual environment
- Packages from `requirements.txt`
- WSL recommended for day-to-day work in this repository

## WSL-First Setup

This repository is used mostly from WSL, so the examples below favor WSL/Linux commands.

### Recommended WSL workflow
- Open the repository in your WSL shell.
- Create the virtual environment inside WSL.
- Install dependencies inside WSL.
- Run `run_all.py` from WSL for the normal dashboard workflow.
- Use PowerShell only when you need a Windows-native tool or path.

### Install dependencies in WSL

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Install dependencies in PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Notes for WSL users
- Use Linux paths inside WSL, such as `/mnt/c/Users/...` when accessing Windows files.
- Keep the virtual environment in the repository so the same commands work every time.
- If you are switching between WSL and PowerShell, reactivate the correct virtual environment before running scripts.

## Configuration

Configuration is usually supplied through environment variables or a `.env` file.

Common files:
- project root `.env`
- `dashboard/.env`

Common variables:
- `DASHBOARD_API_KEY` - API key used by the backend and frontend for protected routes
- `DASHBOARD_HOST` - host for the backend server, default `0.0.0.0`
- `DASHBOARD_PORT` - backend port, default `8001`
- `SERIAL_PORT` - serial device path for the sensor bridge
- `SIMULATE_SENSOR` - set to `1` to prefer the simulated sensor when available
- `ENABLE_PUBLIC_DASHBOARD` - set to `1` to expose the dashboard publicly
- `PUBLIC_TUNNEL_PROVIDER` - select `cloudflare` or `ngrok`
- `CLOUDFLARED_BIN` - optional path to the Cloudflare tunnel executable
- `NGROK_AUTHTOKEN` - optional ngrok auth token
- `FORCE_START_BOT_ON_PI` - override the platform safety check if needed

## How `run_all.py` Works

`run_all.py` is the main entrypoint for the dashboard stack.

It performs these steps:
1. Loads environment variables from `.env` files when present.
2. Starts the FastAPI backend with `uvicorn`.
3. Waits for the backend to become ready.
4. Starts the serial reader when a serial port is configured.
5. Starts the simulator when `--simulate` is used.
6. Optionally exposes the dashboard through a public tunnel when `--public` is enabled.
7. Cleans up child processes and tunnels when the script exits.

Command-line flags supported by `run_all.py`:
- `--no-serial` - skip the serial bridge
- `--simulate` - use the simulator instead of a real sensor
- `--public` - open a public tunnel to the dashboard
- `--public-provider` - choose the tunnel provider
- `--env` - load a specific `.env` file

### Common `run_all.py` commands

Start the full dashboard stack:

```bash
python run_all.py
```

Start the simulator instead of the real sensor:

```bash
python run_all.py --simulate
```

Skip the serial bridge:

```bash
python run_all.py --no-serial
```

Open a public tunnel:

```bash
python run_all.py --public
```

Use a specific tunnel provider:

```bash
python run_all.py --public --public-provider ngrok
```

Load a specific environment file:

```bash
python run_all.py --env dashboard/.env
```

## Dashboard Architecture

The dashboard is split into two main parts:

### Backend
The backend lives in `dashboard/backend/app.py` and uses FastAPI. It is responsible for:
- exposing REST endpoints for readings, predictions, soil commands, and plant history
- storing incoming sensor data in SQLite through SQLAlchemy
- emitting live updates through Server-Sent Events
- loading prediction artifacts from `model/` on demand
- serving the frontend static files from `dashboard/frontend/`

Database behavior:
- `dashboard/backend/database.py` configures the SQLite connection
- readings are stored locally in `dashboard.db`
- the schema is initialized automatically at startup

### Frontend
The frontend lives in `dashboard/frontend/` and is served as static files by the backend.

Frontend files include:
- `index.html` - main dashboard page
- `history.html` - reading history page
- `prediction.html` - prediction page
- `commands.html` - command and management page
- `app.js` - shared dashboard logic, charts, live updates, and data loading
- `prediction.js` - prediction page behavior
- `commands.js` - command page behavior
- `style.css` - shared styling
- `manifest.json` - PWA manifest

Frontend behavior:
- it reads the API base URL from the page or current origin
- it calls backend endpoints to fetch readings and predictions
- it uses Server-Sent Events for live updates
- it updates charts, cards, and tables in the browser without page reloads

### Data flow between frontend and backend
1. The sensor bridge or simulator sends a reading to `POST /api/readings`.
2. The backend validates and stores the reading in SQLite.
3. The backend broadcasts the new reading to connected browsers through `/api/stream`.
4. The frontend receives the event and updates the UI immediately.
5. The frontend can also request history, latest readings, and predictions using REST endpoints.

## Backend API Overview

The backend provides several useful routes:

- `POST /api/readings` - store a new sensor reading
- `GET /api/readings/latest` - return the newest reading
- `GET /api/readings/history` - return recent readings for tables and charts
- `GET /api/stream` - Server-Sent Events stream for live updates
- `POST /api/predict` - predict the most suitable crop from soil values
- `GET /api/predict/history` - predict crops for recent readings
- `POST /api/commands/soil` - store a soil entry
- `GET /api/commands/soil` - list stored soil entries
- `DELETE /api/commands/soil/{soil_id}` - delete a stored soil entry
- `POST /api/commands/soil/{soil_id}/suitability` - evaluate suitability for a crop
- `POST /api/commands/soil/test-crops` - test multiple crops at once
- `GET /api/commands/plants` - get plant history
- `POST /api/commands/plants/previous` - update the previous plant
- `POST /api/commands/plants/next` - update the next plant
- `GET /api/commands/status` - fetch the latest sensor status

## Model Artifacts and Prediction

The backend loads prediction assets from `model/` when crop prediction endpoints are used.

Typical artifacts include:
- a saved model file such as `.keras` or `.h5`
- `scaler.save`
- `label_encoder.save`

If prediction fails because artifacts are missing:
1. Re-run the training scripts.
2. Confirm the files were written into the correct `model/` directory.
3. Restart the dashboard stack.

## Training and Regenerating Artifacts

Use the training scripts when you need new model files or preprocessing artifacts.

Examples:

```bash
python model_training.py
python train_on_prepared.py
python train_filtered.py
python train_trimmed_ann.py
```

The exact script depends on the dataset or experiment you want to reproduce.

## Run Examples

Full dashboard stack:

```bash
python run_all.py
```

Dashboard with simulator:

```bash
python run_all.py --simulate
```

Public dashboard:

```bash
python run_all.py --public
```

## Troubleshooting

- If the backend does not start, check that the virtual environment is active and `uvicorn` is installed.
- If live readings do not appear, confirm the serial bridge or simulator is running and that the backend is reachable.
- If the frontend shows stale data, refresh the page and confirm the browser can reach `/api/stream`.
- If model predictions fail, verify the expected files exist in `model/`.
- If you are on WSL and a Windows path does not work, convert it to a WSL path under `/mnt/c/...`.

## Notes

- The frontend and backend share the same host and port when started by `run_all.py`.
- The dashboard is meant to provide live monitoring, historical data, and prediction tools in one place.
- WSL is the preferred environment for running the project on this machine.
