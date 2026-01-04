# Flowchart for `run_all.py`

High-level flow: orchestrates backend, simulator/serial bridge, and bot processes with flags.

```mermaid
flowchart TD
  Start([Start run_all])
  Start --> ParseArgs["Parse CLI flags: --simulate, --no-bot, --no-serial, etc."]
  ParseArgs --> ConfigureEnv["Load .env, set defaults (API keys, ports)"]
  ConfigureEnv --> StartBackend["Start FastAPI uvicorn server (in subprocess)"]
  StartBackend --> WaitReady["Wait for server readiness (healthcheck)"]
  WaitReady --> DecideSerial{SERIAL_PORT set?}
  DecideSerial -->|yes| StartSerial["Start serial_reader process to read RS485 sensor"]
  DecideSerial -->|no| SerialSkip["Skip serial reader"]
  ParseArgs --> DecideSim{--simulate or SIMULATE_SENSOR=1?}
  DecideSim -->|yes| StartSim["Start simulated_sensor process (posts readings periodically)"]
  DecideSim -->|no| SimSkip["No simulator"]
  StartBackend --> DecideBot{--no-bot?}
  DecideBot -->|no| StartBot["Start Telegram bot process (webhook or polling based on env) "]
  DecideBot -->|yes| BotSkip["Skip bot"]
  StartSerial --> Monitor["Monitor child processes, restart on failure or shutdown on CTRL+C"]
  StartSim --> Monitor
  StartBot --> Monitor
  Monitor --> Stop([Shutdown all subprocesses])
```

Notes:
- `run_all.py` ensures ordering: server must be ready before simulator/serial/bot start.
- It accepts env overrides and flags to control which components to run.
- Useful improvements: add health endpoints and exponential backoff for restarts.
