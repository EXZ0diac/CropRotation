#!/usr/bin/env python3
"""
Sensor test with separate RE/DE pin control for MAX485.

Pin configuration:
- RE (Receiver Enable) -> GPIO17 (pin 11) - LOW to enable receiver
- DE (Driver Enable) -> GPIO18 (pin 12) - LOW to enable receiver mode

Run on Raspberry Pi with sudo:
    sudo python3 test_sensor_separate_pins.py

Press Ctrl+C to stop.
"""
import serial
import time
import RPi.GPIO as GPIO

PORT = '/dev/serial0'
BAUDRATE = 9600
TIMEOUT = 2
RE_PIN = 17  # GPIO17 for Receiver Enable
DE_PIN = 18  # GPIO18 for Driver Enable

def setup_gpio():
    """Configure GPIO for direction control."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RE_PIN, GPIO.OUT)
    GPIO.setup(DE_PIN, GPIO.OUT)
    set_receive_mode()
    print(f"✓ GPIO{RE_PIN} (RE) and GPIO{DE_PIN} (DE) configured for receive mode")

def set_receive_mode():
    """Set to receive mode: RE=LOW, DE=LOW"""
    GPIO.output(RE_PIN, GPIO.LOW)   # Enable receiver
    GPIO.output(DE_PIN, GPIO.LOW)   # Disable driver
    print("  → Receive mode enabled")

def set_transmit_mode():
    """Set to transmit mode: RE=HIGH, DE=HIGH"""
    GPIO.output(RE_PIN, GPIO.HIGH)  # Disable receiver
    GPIO.output(DE_PIN, GPIO.HIGH)  # Enable driver
    print("  → Transmit mode enabled")

print(f"Opening {PORT} @ {BAUDRATE} baud...")
try:
    setup_gpio()
    
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
                print("(no data)")
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
except ImportError:
    print("✗ RPi.GPIO not installed. Run: pip install RPi.GPIO")
except RuntimeError as e:
    print(f"✗ GPIO Error: {e}")
    print("  - Script must run with sudo: sudo python3 test_sensor_separate_pins.py")
except serial.SerialException as e:
    print(f"✗ Serial Error: {e}")
except Exception as e:
    print(f"✗ Unexpected error: {e}")
finally:
    try:
        GPIO.cleanup()
    except:
        pass
