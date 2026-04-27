#!/usr/bin/env python3
"""
Sensor test with direction control for MAX485.
Toggles RE/DE pin via GPIO18 to enable/disable receiver.

Run on Raspberry Pi:
    python3 test_sensor_with_direction.py

Press Ctrl+C to stop.
"""
import serial
import time
import RPi.GPIO as GPIO

PORT = '/dev/serial0'
BAUDRATE = 9600
TIMEOUT = 2
RE_DE_PIN = 18  # GPIO18 controls RE and DE together

def setup_gpio():
    """Configure GPIO for direction control."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RE_DE_PIN, GPIO.OUT)
    GPIO.output(RE_DE_PIN, GPIO.LOW)  # Start in receive mode
    print(f"✓ GPIO{RE_DE_PIN} configured (receive mode)")

def set_receive_mode():
    """Set to receive mode: RE/DE LOW"""
    GPIO.output(RE_DE_PIN, GPIO.LOW)

def set_transmit_mode():
    """Set to transmit mode: RE/DE HIGH"""
    GPIO.output(RE_DE_PIN, GPIO.HIGH)

print(f"Opening {PORT} @ {BAUDRATE} baud...")
try:
    setup_gpio()
    
    ser = serial.Serial(PORT, BAUDRATE, timeout=TIMEOUT)
    print("✓ Serial port opened successfully")
    print("Waiting for sensor data... (Press Ctrl+C to stop)\n")
    
    set_receive_mode()  # Listen for data
    
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
    
    print("\nCleaning up...")
    GPIO.cleanup()
    ser.close()
    print("Done.")
    
except FileNotFoundError:
    print(f"✗ Error: Port {PORT} not found.")
    print("  - Check if UART is enabled: raspi-config > Interface Options > Serial Port")
    print("  - Try: ls /dev/serial0 /dev/ttyAMA0 /dev/ttyUSB*")
except ImportError:
    print("✗ RPi.GPIO not installed. Run: pip install RPi.GPIO")
except RuntimeError as e:
    print(f"✗ GPIO Error: {e}")
    print("  - Run script with sudo if needed: sudo python3 test_sensor_with_direction.py")
except serial.SerialException as e:
    print(f"✗ Serial Error: {e}")
except Exception as e:
    print(f"✗ Unexpected error: {e}")
finally:
    try:
        GPIO.cleanup()
    except:
        pass
