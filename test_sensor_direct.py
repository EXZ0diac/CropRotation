#!/usr/bin/env python3
"""
Simple sensor test: reads raw data from RS485 serial port.
Use this to verify if your sensor is sending data correctly.

Run on Raspberry Pi:
    python3 test_sensor_direct.py

Press Ctrl+C to stop.
"""
import serial
import time

PORT = '/dev/serial0'
BAUDRATE = 9600
TIMEOUT = 2

print(f"Opening {PORT} @ {BAUDRATE} baud...")
try:
    ser = serial.Serial(PORT, BAUDRATE, timeout=TIMEOUT)
    print("✓ Serial port opened successfully")
    print("Waiting for sensor data... (Press Ctrl+C to stop)\n")
    
    while True:
        try:
            line = ser.readline()
            if line:
                decoded = line.decode('utf-8', errors='ignore').strip()
                print(f"RX: {decoded}")
            else:
                print("(no data received)")
            time.sleep(0.5)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error reading: {e}")
            time.sleep(1)
    
    print("\nClosing port...")
    ser.close()
    print("Done.")
    
except FileNotFoundError:
    print(f"✗ Error: Port {PORT} not found.")
    print("  - Check if UART is enabled: raspi-config > Interface Options > Serial Port")
    print("  - Try: ls /dev/serial0 /dev/ttyAMA0 /dev/ttyUSB*")
except serial.SerialException as e:
    print(f"✗ Error: {e}")
    print("  - Check if port is already in use")
    print("  - Try: sudo usermod -a -G dialout $USER")
except Exception as e:
    print(f"✗ Unexpected error: {e}")
