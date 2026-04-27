#!/usr/bin/env python3
"""
Active Modbus RTU poll test for RS485 soil sensors via MAX485 on Raspberry Pi.

This script:
- Controls separate RE and DE pins (manual direction MAX485)
- Sends Modbus requests (function 0x03)
- Tries common baud rates and slave IDs automatically
- Prints raw register values when a valid response is found

Run on Raspberry Pi (sudo required for GPIO access):
    sudo python3 test_sensor_modbus_poll.py

Optional manual settings:
    sudo python3 test_sensor_modbus_poll.py --baud 9600 --slave 1 --start 0 --count 7
"""

import argparse
import serial
import time
import RPi.GPIO as GPIO

# Hardware defaults for your separate RE/DE MAX485 module
PORT = "/dev/serial0"
RE_PIN = 17  # Receiver Enable (LOW = receive enabled)
DE_PIN = 18  # Driver Enable (HIGH = transmit enabled)


def crc16_modbus(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def add_crc(frame: bytes) -> bytes:
    crc = crc16_modbus(frame)
    return frame + bytes([crc & 0xFF, (crc >> 8) & 0xFF])


def set_receive_mode():
    # Receive mode: receiver enabled, driver disabled
    GPIO.output(RE_PIN, GPIO.LOW)
    GPIO.output(DE_PIN, GPIO.LOW)


def set_transmit_mode():
    # Transmit mode: receiver disabled, driver enabled
    GPIO.output(RE_PIN, GPIO.HIGH)
    GPIO.output(DE_PIN, GPIO.HIGH)


def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RE_PIN, GPIO.OUT)
    GPIO.setup(DE_PIN, GPIO.OUT)
    set_receive_mode()


def read_exact(ser: serial.Serial, nbytes: int, timeout_s: float) -> bytes:
    deadline = time.time() + timeout_s
    out = bytearray()
    while len(out) < nbytes and time.time() < deadline:
        chunk = ser.read(nbytes - len(out))
        if chunk:
            out.extend(chunk)
        else:
            time.sleep(0.002)
    return bytes(out)


def modbus_read_holding(ser: serial.Serial, slave: int, start: int, count: int, timeout_s: float = 1.2):
    # Request: [slave][0x03][start_hi][start_lo][count_hi][count_lo][crc_lo][crc_hi]
    req = bytes([
        slave & 0xFF,
        0x03,
        (start >> 8) & 0xFF,
        start & 0xFF,
        (count >> 8) & 0xFF,
        count & 0xFF,
    ])
    req = add_crc(req)

    ser.reset_input_buffer()
    ser.reset_output_buffer()

    # Send request
    set_transmit_mode()
    time.sleep(0.002)
    ser.write(req)
    ser.flush()
    # Small turnaround delay so line settles before receive
    time.sleep(0.004)

    # Receive response
    set_receive_mode()

    # Expected response length for function 0x03:
    # [slave][func][byte_count][data...][crc_lo][crc_hi]
    expected_len = 5 + (2 * count)
    resp = read_exact(ser, expected_len, timeout_s)
    if len(resp) < 5:
        return None, f"short response ({len(resp)} bytes)"

    # Validate CRC
    recv_crc = resp[-2] | (resp[-1] << 8)
    calc_crc = crc16_modbus(resp[:-2])
    if recv_crc != calc_crc:
        return None, f"crc mismatch recv=0x{recv_crc:04X} calc=0x{calc_crc:04X}"

    # Basic header validation
    if resp[0] != slave:
        return None, f"unexpected slave {resp[0]}"
    if resp[1] & 0x80:
        # Modbus exception
        code = resp[2] if len(resp) > 2 else None
        return None, f"modbus exception code {code}"
    if resp[1] != 0x03:
        return None, f"unexpected function {resp[1]}"

    byte_count = resp[2]
    data = resp[3:-2]
    if byte_count != len(data):
        return None, f"byte_count mismatch {byte_count}!={len(data)}"

    regs = []
    for i in range(0, len(data), 2):
        regs.append((data[i] << 8) | data[i + 1])

    return regs, None


def open_serial(port: str, baud: int) -> serial.Serial:
    return serial.Serial(
        port=port,
        baudrate=baud,
        bytesize=8,
        parity=serial.PARITY_NONE,
        stopbits=1,
        timeout=0.2,
    )


def auto_detect(port: str, bauds, slaves, starts, count: int):
    print("Auto-detect mode: trying common baud/slave/start combos...")
    for baud in bauds:
        try:
            with open_serial(port, baud) as ser:
                for slave in slaves:
                    for start in starts:
                        regs, err = modbus_read_holding(ser, slave, start, count)
                        if regs is not None:
                            print(f"SUCCESS baud={baud} slave={slave} start={start} count={count}")
                            print("Registers:", regs)
                            return baud, slave, start
                        else:
                            print(f"no reply: baud={baud} slave={slave} start={start} ({err})")
        except Exception as e:
            print(f"serial open failed @ {baud}: {e}")
    return None, None, None


def main():
    parser = argparse.ArgumentParser(description="MAX485 Modbus poll test")
    parser.add_argument("--port", default=PORT)
    parser.add_argument("--baud", type=int, default=None, help="Set baud directly")
    parser.add_argument("--slave", type=int, default=None, help="Set Modbus slave ID directly")
    parser.add_argument("--start", type=int, default=0, help="Start register")
    parser.add_argument("--count", type=int, default=7, help="Register count")
    parser.add_argument("--interval", type=float, default=5.0, help="Polling interval seconds")
    args = parser.parse_args()

    setup_gpio()
    print(f"GPIO setup OK (RE=GPIO{RE_PIN}, DE=GPIO{DE_PIN})")

    try:
        baud = args.baud
        slave = args.slave
        start = args.start
        count = args.count

        if baud is None or slave is None:
            bauds = [9600, 4800, 2400, 19200]
            slaves = [1, 2, 3, 4, 5]
            starts = [0, 1, 2, 10]
            detected = auto_detect(args.port, bauds, slaves, starts, count)
            baud, slave, start = detected
            if baud is None:
                print("\nNo valid Modbus response detected.")
                print("Check: sensor power, A/B wiring, RE/DE wiring, slave ID, baud, and sensor protocol.")
                return

        print(f"\nPolling started: port={args.port} baud={baud} slave={slave} start={start} count={count}")
        with open_serial(args.port, baud) as ser:
            while True:
                regs, err = modbus_read_holding(ser, slave, start, count)
                if regs is not None:
                    print(f"OK regs={regs}")
                else:
                    print(f"No data: {err}")
                time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nStopped by user")
    finally:
        try:
            set_receive_mode()
            GPIO.cleanup()
        except Exception:
            pass


if __name__ == "__main__":
    main()
