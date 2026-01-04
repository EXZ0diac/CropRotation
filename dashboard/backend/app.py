from fastapi import FastAPI, Depends, HTTPException, Header, Request
import logging
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional, List
import os
import threading
from pathlib import Path
try:
    from openpyxl import Workbook, load_workbook
    OPENPYXL_AVAILABLE = True
except Exception:
    OPENPYXL_AVAILABLE = False

from . import models
from .database import SessionLocal, init_db, engine
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from fastapi.responses import StreamingResponse
import asyncio
import json

# initialize DB (models are imported above so metadata is available)
init_db()

app = FastAPI(title="Soil Sensor Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv("DASHBOARD_API_KEY", "dev-token")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_api_key(x_api_key: Optional[str] = Header(None)):
    if x_api_key is None:
        raise HTTPException(status_code=401, detail="Missing API key")
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")


# Simple in-memory broadcaster for Server-Sent Events (SSE)
# Each client gets its own asyncio.Queue which the POST handler will put new readings into.
listeners: List[asyncio.Queue] = []
excel_lock = threading.Lock()
EXCEL_PATH = Path(__file__).resolve().parent.parent / "data" / "readings.xlsx"


def append_reading_to_excel(row: dict):
    """Append a reading dict to an Excel workbook. Creates file and header if missing.

    row keys expected: timestamp (datetime or str), np_n, np_p, np_k, ph, ec, humidity, temperature
    """
    if not OPENPYXL_AVAILABLE:
        # openpyxl not installed; skip writing to Excel but do not raise.
        logging.warning("openpyxl not available; skipping Excel write for readings")
        return

    EXCEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Normalize timestamp
    ts = row.get("timestamp")
    try:
        # If it's a string, attempt to split
        if isinstance(ts, str):
            # try to parse ISO-like string
            date_part = ts.split("T")[0] if "T" in ts else ts.split()[0]
            time_part = ts.split("T")[1] if "T" in ts and len(ts.split("T")) > 1 else (ts.split()[1] if len(ts.split()) > 1 else "")
        else:
            date_part = ts.date().isoformat()
            time_part = ts.time().strftime("%H:%M:%S")
    except Exception:
        date_part = str(ts)
        time_part = ""

    headers = ["Time", "Date", "N", "P", "K", "EC", "pH", "Humidity", "Temperature"]
    values = [time_part, date_part, row.get("np_n"), row.get("np_p"), row.get("np_k"), row.get("ec"), row.get("ph"), row.get("humidity"), row.get("temperature")]

    with excel_lock:
        if EXCEL_PATH.exists():
            try:
                wb = load_workbook(EXCEL_PATH)
                ws = wb.active
            except Exception:
                # If loading fails, create a fresh workbook
                wb = Workbook()
                ws = wb.active
                ws.append(headers)
        else:
            wb = Workbook()
            ws = wb.active
            ws.append(headers)

        ws.append(values)
        wb.save(EXCEL_PATH)


async def push_event(data: dict):
    payload = json.dumps(data, default=str)
    # deliver to all listeners; use copy to avoid mutation during iteration
    for q in list(listeners):
        try:
            await q.put(payload)
        except Exception:
            # ignore errors per-listener
            pass



@app.post("/api/readings", status_code=201)
async def post_reading(payload: dict, db: Session = Depends(get_db), _=Depends(require_api_key)):
    # Payload may contain keys: np_n, np_p, np_k, ph, ec, humidity, temperature
    r = models.Reading(
        np_n=payload.get("np_n"),
        np_p=payload.get("np_p"),
        np_k=payload.get("np_k"),
        ph=payload.get("ph"),
        ec=payload.get("ec"),
        humidity=payload.get("humidity"),
        temperature=payload.get("temperature"),
        raw=str(payload)
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    # Push event to SSE listeners asynchronously (schedule a background task)
    asyncio.create_task(push_event({
        "id": r.id,
        "timestamp": r.timestamp,
        "np_n": r.np_n,
        "np_p": r.np_p,
        "np_k": r.np_k,
        "ph": r.ph,
        "ec": r.ec,
        "humidity": r.humidity,
        "temperature": r.temperature,
    }))

    # Also append to Excel (run in thread so we don't block the event loop)
    try:
        row = {
            "timestamp": r.timestamp,
            "np_n": r.np_n,
            "np_p": r.np_p,
            "np_k": r.np_k,
            "ph": r.ph,
            "ec": r.ec,
            "humidity": r.humidity,
            "temperature": r.temperature,
        }
        asyncio.create_task(asyncio.to_thread(append_reading_to_excel, row))
    except Exception:
        # best-effort: do not fail the request if excel write fails
        pass
    return {"id": r.id}


@app.get('/api/stream')
def stream_readings(request: Request, api_key: Optional[str] = None, x_api_key: Optional[str] = Header(None)):
    """Server-Sent Events endpoint streaming new readings as they arrive.

    Browsers' EventSource cannot set custom headers, so this endpoint accepts an
    `api_key` query parameter (e.g. `/api/stream?api_key=dev-token`) in addition
    to the normal `x-api-key` header. The server will validate either.
    """
    # Validate provided api key (either query param or header)
    provided = api_key or x_api_key
    if provided is None:
        # If no API key provided, allow EventSource from clients on common
        # private/local networks (loopback and RFC1918 ranges). Browsers
        # cannot set headers on EventSource, and for local/LAN deployments
        # this is a practical convenience to avoid 401s. If you expose this
        # server publicly, consider setting DASHBOARD_API_KEY and not relying
        # on this fallback.
        client_host = getattr(request.client, 'host', None)
        if client_host:
            if (client_host.startswith('127.') or client_host == '::1' or
                    client_host.startswith('192.') or client_host.startswith('10.') or
                    client_host.startswith('172.')):
                logging.info(f"Allowing SSE connection from local client {client_host} without api_key")
                provided = API_KEY  # treat as authorized for this connection
            else:
                raise HTTPException(status_code=401, detail="Missing API key")
        else:
            raise HTTPException(status_code=401, detail="Missing API key")

    if provided != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")

    q: asyncio.Queue = asyncio.Queue()
    listeners.append(q)

    async def event_generator():
        try:
            while True:
                data = await q.get()
                yield f"data: {data}\n\n"
        except asyncio.CancelledError:
            return
        finally:
            # cleanup: remove our queue from listeners
            try:
                listeners.remove(q)
            except ValueError:
                pass

    return StreamingResponse(event_generator(), media_type='text/event-stream')


@app.get("/api/readings/latest")
def latest_reading(db: Session = Depends(get_db), _=Depends(require_api_key)):
    item = db.query(models.Reading).order_by(models.Reading.timestamp.desc()).first()
    if not item:
        raise HTTPException(status_code=404, detail="No readings available")
    return {
        "id": item.id,
        "timestamp": item.timestamp,
        "np_n": item.np_n,
        "np_p": item.np_p,
        "np_k": item.np_k,
        "ph": item.ph,
        "ec": item.ec,
        "humidity": item.humidity,
        "temperature": item.temperature,
    }


@app.get("/api/readings/history")
def history(limit: int = 100, db: Session = Depends(get_db), _=Depends(require_api_key)):
    items = db.query(models.Reading).order_by(models.Reading.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": it.id,
            "timestamp": it.timestamp,
            "np_n": it.np_n,
            "np_p": it.np_p,
            "np_k": it.np_k,
            "ph": it.ph,
            "ec": it.ec,
            "humidity": it.humidity,
            "temperature": it.temperature,
        }
        for it in items
    ]


@app.post("/api/command")
def send_command(cmd: dict, _=Depends(require_api_key)):
    # This endpoint is a placeholder to record commands sent from app/website.
    # Extend to forward commands to a device gateway if present.
    return {"status": "queued", "command": cmd}


# Serve frontend (PWA) static files from the `dashboard/frontend` directory.
# Mounting static after API routes so `/api/*` remains handled by the app.
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    # Mount at root so files like /app.js and /style.css are served as expected.
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
else:
    # If frontend folder missing, root index will return a simple message
    @app.get("/", include_in_schema=False)
    def _root_missing():
        return {"message": "Frontend not found. Place frontend files in dashboard/frontend."}
