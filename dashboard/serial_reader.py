"""
Serial (RS485) bridge to read sensor output and POST to the dashboard API.

Expected formats:
- JSON per-line, e.g. {"np_n":1.2,"np_p":0.5,"np_k":0.3,"ph":6.5,"ec":1.1,"humidity":45,"temperature":22.3}
- CSV per-line in the order: N,P,K,pH,EC,Humidity,Temperature

Configure SERIAL_PORT, BAUDRATE, and API_URL via environment or command-line.
"""
import os
import time
import json
import requests
import serial

SERIAL_PORT = os.getenv('SERIAL_PORT','COM3')
BAUDRATE = int(os.getenv('BAUDRATE', '9600'))
API_URL = os.getenv('DASHBOARD_API_URL','http://127.0.0.1:8000/api/readings')
API_KEY = os.getenv('DASHBOARD_API_KEY','dev-token')


def parse_line(line:str):
    line = line.strip()
    try:
        return json.loads(line)
    except Exception:
        parts = [p.strip() for p in line.split(',') if p.strip()!='']
        if len(parts) >= 7:
            return {
                'np_n': float(parts[0]),
                'np_p': float(parts[1]),
                'np_k': float(parts[2]),
                'ph': float(parts[3]),
                'ec': float(parts[4]),
                'humidity': float(parts[5]),
                'temperature': float(parts[6]),
            }
    return None


def main():
    print(f"Opening serial port {SERIAL_PORT} @ {BAUDRATE}")
    with serial.Serial(SERIAL_PORT, BAUDRATE, timeout=2) as ser:
        while True:
            try:
                raw = ser.readline().decode('utf-8', errors='ignore')
                if not raw:
                    time.sleep(0.2)
                    continue
                print('RX:', raw.strip())
                payload = parse_line(raw)
                if not payload:
                    print('Could not parse line')
                    continue
                resp = requests.post(API_URL, json=payload, headers={'x-api-key':API_KEY})
                print('POST', resp.status_code, resp.text)
            except Exception as e:
                print('Error:', e)
                time.sleep(2)


if __name__ == '__main__':
    main()
