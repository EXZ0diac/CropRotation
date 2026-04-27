"""Serial bridge for dashboard ingestion.

Supports three modes:
1) line mode (legacy): reads JSON/CSV lines from serial and forwards to API
2) modbus mode: actively polls Modbus RTU register(s) and forwards parsed value(s)
3) modbus_probe mode: scans register range(s) to discover available addresses

Environment variables:
- SERIAL_PORT (default: COM3)
- BAUDRATE (default: 9600)
- DASHBOARD_API_URL (default: http://127.0.0.1:8000/api/readings)
- DASHBOARD_API_KEY (default: dev-token)
- SERIAL_MODE: auto|line|modbus|modbus_probe (default: auto)

Modbus-specific:
- MODBUS_SLAVE_ID (default: 1)
- MODBUS_FUNCTION (default: 3)
- MODBUS_REGISTER (default: 10)
- MODBUS_COUNT (default: 1)
- MODBUS_SCALE (default: 10.0)
- MODBUS_FIELD (default: humidity)  # dashboard field to update
- MODBUS_MAP (optional): comma-separated map entries in format field:register:scale
    Example: humidity:10:10,temperature:11:10,ph:12:100
- MODBUS_PARITY (default: N)
- MODBUS_STOPBITS (default: 1)
- SERIAL_POLL_INTERVAL (default: 5)
- MODBUS_PROBE_START (default: 0)
- MODBUS_PROBE_END (default: 30)
- MODBUS_PROBE_FUNCTIONS (default: 3,4)
- MODBUS_PROBE_DELAY (default: 0.08)
"""
import json
import os
import time

import requests
import serial

SERIAL_PORT = os.getenv("SERIAL_PORT", "COM3")
BAUDRATE = int(os.getenv("BAUDRATE", "9600"))
API_URL = os.getenv("DASHBOARD_API_URL", "http://127.0.0.1:8000/api/readings")
API_KEY = os.getenv("DASHBOARD_API_KEY", "dev-token")

SERIAL_MODE = os.getenv("SERIAL_MODE", "auto").lower().strip()
POLL_INTERVAL = float(os.getenv("SERIAL_POLL_INTERVAL", "5"))

MODBUS_SLAVE_ID = int(os.getenv("MODBUS_SLAVE_ID", "1"))
MODBUS_FUNCTION = int(os.getenv("MODBUS_FUNCTION", "3"))
MODBUS_REGISTER = int(os.getenv("MODBUS_REGISTER", "10"))
MODBUS_COUNT = int(os.getenv("MODBUS_COUNT", "1"))
MODBUS_SCALE = float(os.getenv("MODBUS_SCALE", "10"))
MODBUS_FIELD = os.getenv("MODBUS_FIELD", "humidity").strip()
MODBUS_MAP = os.getenv("MODBUS_MAP", "").strip()
MODBUS_PARITY = os.getenv("MODBUS_PARITY", "N").upper().strip()
MODBUS_STOPBITS = int(os.getenv("MODBUS_STOPBITS", "1"))
MODBUS_PROBE_START = int(os.getenv("MODBUS_PROBE_START", "0"))
MODBUS_PROBE_END = int(os.getenv("MODBUS_PROBE_END", "30"))
MODBUS_PROBE_FUNCTIONS = os.getenv("MODBUS_PROBE_FUNCTIONS", "3,4").strip()
MODBUS_PROBE_DELAY = float(os.getenv("MODBUS_PROBE_DELAY", "0.08"))

ALL_FIELDS = ["np_n", "np_p", "np_k", "ph", "ec", "humidity", "temperature"]


def parse_line(line: str):
    line = line.strip()
    try:
        return json.loads(line)
    except Exception:
        parts = [p.strip() for p in line.split(",") if p.strip() != ""]
        if len(parts) >= 7:
            return {
                "np_n": float(parts[0]),
                "np_p": float(parts[1]),
                "np_k": float(parts[2]),
                "ph": float(parts[3]),
                "ec": float(parts[4]),
                "humidity": float(parts[5]),
                "temperature": float(parts[6]),
            }
    return None


def crc16_modbus(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def build_modbus_request(slave: int, function_code: int, register: int, count: int) -> bytes:
    payload = bytes(
        [
            slave & 0xFF,
            function_code & 0xFF,
            (register >> 8) & 0xFF,
            register & 0xFF,
            (count >> 8) & 0xFF,
            count & 0xFF,
        ]
    )
    crc = crc16_modbus(payload)
    return payload + bytes([crc & 0xFF, (crc >> 8) & 0xFF])


def parse_modbus_response(resp: bytes, slave: int, function_code: int):
    if len(resp) < 5:
        return None, "short response"
    if resp[0] != slave:
        return None, f"unexpected slave {resp[0]}"
    if resp[1] & 0x80:
        if len(resp) >= 5:
            return None, f"modbus exception code {resp[2]}"
        return None, "modbus exception"
    if resp[1] != function_code:
        return None, f"unexpected function {resp[1]}"

    recv_crc = resp[-2] | (resp[-1] << 8)
    calc_crc = crc16_modbus(resp[:-2])
    if recv_crc != calc_crc:
        return None, "crc mismatch"

    byte_count = resp[2]
    data = resp[3:-2]
    if byte_count != len(data):
        return None, "byte count mismatch"

    regs = []
    for i in range(0, len(data), 2):
        regs.append((data[i] << 8) | data[i + 1])
    return regs, None


def read_exact(ser: serial.Serial, nbytes: int, timeout_s: float):
    deadline = time.time() + timeout_s
    out = bytearray()
    while len(out) < nbytes and time.time() < deadline:
        chunk = ser.read(nbytes - len(out))
        if chunk:
            out.extend(chunk)
        else:
            time.sleep(0.002)
    return bytes(out)


def serial_parity_from_env(value: str):
    mapping = {
        "N": serial.PARITY_NONE,
        "E": serial.PARITY_EVEN,
        "O": serial.PARITY_ODD,
    }
    return mapping.get(value, serial.PARITY_NONE)


def parse_modbus_map(value: str):
    """Parse MODBUS_MAP string into a list of mapping dicts.

    Expected format:
        field:register:scale,field:register:scale
    Example:
        humidity:10:10,temperature:11:10
    """
    mappings = []
    if not value:
        return mappings

    for entry in value.split(","):
        entry = entry.strip()
        if not entry:
            continue
        parts = [p.strip() for p in entry.split(":")]
        if len(parts) != 3:
            print(f"Ignoring invalid MODBUS_MAP entry: {entry}")
            continue
        field, register_str, scale_str = parts
        if field not in ALL_FIELDS:
            print(f"Ignoring unknown field in MODBUS_MAP: {field}")
            continue
        try:
            register = int(register_str)
            scale = float(scale_str)
        except ValueError:
            print(f"Ignoring non-numeric MODBUS_MAP entry: {entry}")
            continue
        mappings.append({"field": field, "register": register, "scale": scale})

    return mappings


def post_payload(payload: dict):
    resp = requests.post(API_URL, json=payload, headers={"x-api-key": API_KEY}, timeout=10)
    print("POST", resp.status_code, resp.text)


def run_line_mode():
    print(f"[line] Opening serial port {SERIAL_PORT} @ {BAUDRATE}")
    with serial.Serial(SERIAL_PORT, BAUDRATE, timeout=2) as ser:
        while True:
            try:
                raw = ser.readline().decode("utf-8", errors="ignore")
                if not raw:
                    time.sleep(0.2)
                    continue
                print("RX:", raw.strip())
                payload = parse_line(raw)
                if not payload:
                    print("Could not parse line")
                    continue
                post_payload(payload)
            except Exception as e:
                print("Error:", e)
                time.sleep(2)


def run_modbus_mode():
    parity = serial_parity_from_env(MODBUS_PARITY)
    modbus_map = parse_modbus_map(MODBUS_MAP)
    if not modbus_map:
        # Backward-compatible single-field mapping
        modbus_map = [{"field": MODBUS_FIELD, "register": MODBUS_REGISTER, "scale": MODBUS_SCALE}]

    print(
        f"[modbus] port={SERIAL_PORT} baud={BAUDRATE} slave={MODBUS_SLAVE_ID} "
        f"fc={MODBUS_FUNCTION} parity={MODBUS_PARITY} stopbits={MODBUS_STOPBITS}"
    )
    print(f"[modbus] field map: {modbus_map}")

    with serial.Serial(
        SERIAL_PORT,
        BAUDRATE,
        bytesize=8,
        parity=parity,
        stopbits=MODBUS_STOPBITS,
        timeout=0.2,
    ) as ser:
        while True:
            try:
                payload = {}
                raw_debug = {}

                for item in modbus_map:
                    req = build_modbus_request(MODBUS_SLAVE_ID, MODBUS_FUNCTION, item["register"], MODBUS_COUNT)
                    expected_len = 5 + (2 * MODBUS_COUNT)

                    ser.reset_input_buffer()
                    ser.write(req)
                    ser.flush()
                    time.sleep(MODBUS_PROBE_DELAY)
                    resp = read_exact(ser, expected_len, 1.2)

                    regs, err = parse_modbus_response(resp, MODBUS_SLAVE_ID, MODBUS_FUNCTION)
                    if regs is None:
                        print(
                            f"Modbus read failed field={item['field']} reg={item['register']}: "
                            f"{err} | raw={resp.hex(' ')}"
                        )
                        continue

                    raw_value = regs[0]
                    scale = item["scale"]
                    scaled = raw_value / scale if scale != 0 else float(raw_value)
                    payload[item["field"]] = scaled
                    raw_debug[item["field"]] = {
                        "register": item["register"],
                        "raw_value": raw_value,
                        "scaled": scaled,
                        "regs": regs,
                    }

                if not payload:
                    time.sleep(POLL_INTERVAL)
                    continue

                payload["raw"] = raw_debug
                print(f"Modbus OK payload={payload}")
                post_payload(payload)
                time.sleep(POLL_INTERVAL)
            except Exception as e:
                print("Error:", e)
                time.sleep(2)


def parse_probe_functions(value: str):
    out = []
    for token in value.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            fn = int(token)
        except ValueError:
            continue
        if fn in (3, 4):
            out.append(fn)
    if not out:
        out = [3, 4]
    return out


def read_modbus_register(ser: serial.Serial, function_code: int, register: int, count: int = 1):
    req = build_modbus_request(MODBUS_SLAVE_ID, function_code, register, count)
    expected_len = 5 + (2 * count)
    ser.reset_input_buffer()
    ser.write(req)
    ser.flush()
    time.sleep(MODBUS_PROBE_DELAY)
    resp = read_exact(ser, expected_len, 1.2)
    return parse_modbus_response(resp, MODBUS_SLAVE_ID, function_code), resp


def run_modbus_probe_mode():
    parity = serial_parity_from_env(MODBUS_PARITY)
    start_reg = min(MODBUS_PROBE_START, MODBUS_PROBE_END)
    end_reg = max(MODBUS_PROBE_START, MODBUS_PROBE_END)
    functions = parse_probe_functions(MODBUS_PROBE_FUNCTIONS)

    print(
        f"[modbus_probe] port={SERIAL_PORT} baud={BAUDRATE} slave={MODBUS_SLAVE_ID} "
        f"parity={MODBUS_PARITY} stopbits={MODBUS_STOPBITS} range={start_reg}-{end_reg} "
        f"functions={functions}"
    )

    with serial.Serial(
        SERIAL_PORT,
        BAUDRATE,
        bytesize=8,
        parity=parity,
        stopbits=MODBUS_STOPBITS,
        timeout=0.2,
    ) as ser:
        found = []
        for fn in functions:
            print(f"[modbus_probe] scanning function {fn}")
            for reg in range(start_reg, end_reg + 1):
                (regs, err), raw = read_modbus_register(ser, fn, reg, 1)
                if regs is None:
                    continue
                value = regs[0]
                found.append((fn, reg, value))
                print(f"[modbus_probe] OK fc={fn} reg={reg} raw={value}")

        if not found:
            print("[modbus_probe] no readable registers found in requested range")
            return

        print("[modbus_probe] summary")
        for fn, reg, value in found:
            print(f"  fc={fn} reg={reg} raw={value}")

        print(
            "[modbus_probe] next step: map candidate regs in MODBUS_MAP and restart with SERIAL_MODE=modbus"
        )


def choose_mode():
    if SERIAL_MODE in ("line", "modbus", "modbus_probe"):
        return SERIAL_MODE
    # auto mode: prefer modbus on Linux serial devices, keep line mode on COM ports
    if SERIAL_PORT.startswith("/dev/"):
        return "modbus"
    return "line"


def main():
    mode = choose_mode()
    if mode == "modbus":
        run_modbus_mode()
    elif mode == "modbus_probe":
        run_modbus_probe_mode()
    else:
        run_line_mode()


if __name__ == "__main__":
    main()
