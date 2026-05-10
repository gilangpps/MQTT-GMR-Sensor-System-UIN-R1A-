# MQTT-based Giant Magnetoresistance Sensor System (GMR-UIN-R1A)

## Abstract

This project presents a comprehensive implementation of a distributed data acquisition and monitoring system for Giant Magnetoresistance (GMR) sensor measurements. The system leverages MQTT (Message Queuing Telemetry Transport) protocol to enable real-time data streaming, processing, and visualization across networked devices. The architecture comprises an embedded data acquisition unit, cloud-compatible publisher module, and flexible subscriber interface for remote monitoring and analysis.

---

## Table of Contents

1. [Introduction](#introduction)
2. [System Architecture](#system-architecture)
3. [Hardware Requirements](#hardware-requirements)
4. [Software Dependencies](#software-dependencies)
5. [Installation Guide](#installation-guide)
6. [System Configuration](#system-configuration)
7. [Operating Instructions](#operating-instructions)
8. [Calibration Procedures](#calibration-procedures)
9. [Troubleshooting](#troubleshooting)
10. [Directory Structure](#directory-structure)
11. [License](#license)

---

## Introduction

The MQTT GMR Sensor System is designed for real-time acquisition, processing, and remote monitoring of magnetic field measurements using Giant Magnetoresistance sensors. This system integrates:

- **Embedded Data Acquisition Unit**: Arduino-based controller interfacing with ADS1115 analog-to-digital converter
- **Publisher Module**: Python application for serial communication and MQTT data dissemination
- **Subscriber Module**: Real-time visualization and monitoring interface with graphical data representation
- **Network Communication**: MQTT broker-based distributed architecture supporting multiple client connections

### Key Features

- Real-time data acquisition at configurable sampling rates
- MQTT-based publisher-subscriber messaging paradigm
- Graphical user interface for interactive monitoring
- Data logging and export capabilities (CSV format)
- Calibrated magnetic field conversion from raw sensor voltages
- Multi-threaded architecture for non-blocking I/O operations
- Support for dual operational modes: Full-featured and Light modes

---

## System Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    MQTT-GMR Sensor System                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────┐         ┌──────────────────────────────┐   │
│  │   Arduino Unit   │         │   MQTT Broker               │   │
│  │  + ADS1115 ADC   ├────────►├─  (Network accessible)      │   │
│  │  + GMR Sensor    │         │                             │   │
│  └──────────────────┘         └──────────────────────────────┘   │
│         ▲                               ▲                         │
│         │ Serial                        │ MQTT                   │
│         │ (COM7, 9600 baud)            │ (Port 1883)            │
│         │                               │                         │
│  ┌──────┴───────────────────┐  ┌──────┴──────────────────────┐  │
│  │   Publisher Module       │  │  Subscriber Module          │  │
│  │  (Full/Light versions)   │  │  (Full/Light versions)      │  │
│  │                          │  │                             │  │
│  │ • Serial Reading         │  │ • Real-time Graphing        │  │
│  │ • Calibration            │  │ • Data Visualization        │  │
│  │ • MQTT Publishing        │  │ • CSV Export                │  │
│  │ • Visualization          │  │ • Status Monitoring         │  │
│  └──────────────────────────┘  └─────────────────────────────┘  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### MQTT Topics

| Topic | Publisher | Subscriber | Description |
|-------|-----------|------------|-------------|
| `gmr/data` | Publisher | Subscriber | Sensor data (voltage, B-field, timestamp) |
| `gmr/status` | Publisher | Subscriber | System status and connectivity information |

---

## Hardware Requirements

### Microcontroller Unit

- **Arduino Board**: Arduino Uno, Mega, or compatible microcontroller with I²C interface
- **Analog-to-Digital Converter**: Adafruit ADS1115 (16-bit, I²C protocol)
- **Sensor**: Giant Magnetoresistance (GMR) sensor with appropriate signal conditioning
- **Communication**: USB/Serial adapter for PC connectivity
- **Power Supply**: 5V regulated power supply

### Computing Platform

- **Processor**: Intel/AMD x86-64 processor (minimum 1 GHz)
- **Memory**: Minimum 2 GB RAM
- **Operating System**: Windows 10/11, Linux, or macOS
- **Network**: Ethernet or WiFi interface for MQTT broker connectivity
- **USB Interface**: USB 2.0 or higher for serial communication

### Network Infrastructure

- **MQTT Broker**: Mosquitto, EMQ, or compatible MQTT server
- **Network**: TCP/IP LAN or WAN connectivity
- **Port Configuration**: MQTT default port 1883 (or alternative as configured)

---

## Software Dependencies

### Python Runtime

- **Python Version**: 3.8 or higher
- **Package Manager**: pip (Python Package Installer)

### Required Python Packages

| Package | Version | Purpose |
|---------|---------|---------|
| `paho-mqtt` | ≥2.0.0 | MQTT client library for Python |
| `pyserial` | ≥3.5 | Serial port communication |
| `matplotlib` | ≥3.5.0 | Data visualization and real-time plotting |
| `pandas` | ≥1.3.0 | Data manipulation and CSV export |
| `tkinter` | Built-in | Graphical User Interface framework |

### Arduino Libraries

- **Wire.h**: I²C communication (standard Arduino library)
- **Adafruit_ADS1X15**: ADS1115 driver library
  - Installation: Via Arduino IDE Library Manager or manual download

### System Requirements

- **Serial Driver**: CH340 or FTDI driver (depending on USB adapter)
- **MQTT Broker**: Accessible network location with port 1883 open

---

## Installation Guide

### Step 1: Python Environment Setup

#### Option A: Using Virtual Environment (Recommended)

```bash
# Navigate to project directory
cd path/to/MQTT-GMR-1A

# Create virtual environment
python -m venv gmr_env

# Activate virtual environment
# On Windows:
gmr_env\Scripts\activate
# On Linux/macOS:
source gmr_env/bin/activate
```

#### Option B: Direct Installation

Skip the virtual environment if preferred (not recommended for production).

### Step 2: Install Python Dependencies

```bash
# Install required packages from the dependency manifest
pip install -r requirements.txt

# Verify installation
pip list
```

### Step 3: Arduino Board Setup

1. **Install Arduino IDE** from official Arduino website (https://www.arduino.cc/en/software)

2. **Install Board Support** (if using non-standard board):
   - Open Arduino IDE → Preferences
   - Add board manager URL if needed
   - Tools → Board Manager → Install appropriate board

3. **Install Required Libraries**:
   - Sketch → Include Library → Manage Libraries
   - Search for "Adafruit ADS1X15"
   - Install latest version

4. **Connect Arduino Board**:
   - Connect via USB cable
   - Tools → Board → Select appropriate board
   - Tools → Port → Select corresponding COM port
   - Tools → Serial Monitor → Verify communication at 9600 baud

### Step 4: Upload Arduino Firmware

1. Open `/main/main.ino` in Arduino IDE
2. Configure settings:
   ```cpp
   #define BAUDRATE 9600        // Serial communication speed
   #define ADS_GAIN GAIN_TWO    // ADC gain setting (±2.048V)
   ```
3. Verify code: Sketch → Verify/Compile
4. Upload: Sketch → Upload
5. Monitor serial output: Tools → Serial Monitor

### Step 5: MQTT Broker Installation

#### Option A: Local Installation (Windows)

1. Download Mosquitto from https://mosquitto.org/download/
2. Install with default settings
3. Default configuration: Localhost, port 1883
4. Verify broker running: Command Prompt → `mosquitto -v`

#### Option B: Remote Broker

Configure broker IP address in Python scripts:
```python
MQTT_BROKER = '192.168.1.100'  # Replace with broker IP
```

---

## System Configuration

### Publisher Configuration

Edit `GMR-UIN-R1A-Publisher.py`:

```python
# Serial Configuration
SERIAL_PORT  = 'COM7'          # Adjust to your Arduino port
BAUD_RATE    = 9600            # Must match Arduino configuration

# MQTT Configuration
MQTT_BROKER  = '100.116.20.77' # Broker IP address
MQTT_PORT    = 1883            # Default MQTT port
MQTT_TOPIC_DATA  = 'gmr/data'
MQTT_TOPIC_STATUS = 'gmr/status'
MQTT_CLIENT_ID   = 'GMR-Publisher'

# Calibration Parameters
def tegangan_ke_b(v):
    return 5.3381 * v - 4.2983  # Voltage to Magnetic Field conversion
```

### Subscriber Configuration

Edit `GMR-UIN-R1A-Subscriber.py`:

```python
# MQTT Configuration
MQTT_BROKER      = 'localhost'  # Broker IP address
MQTT_PORT        = 1883
MQTT_TOPIC_DATA  = 'gmr/data'
MQTT_TOPIC_STATUS = 'gmr/status'
MQTT_CLIENT_ID   = 'GMR-Subscriber'
```

### Identify Serial Port

**Windows**:
```bash
# List COM ports
mode

# Or in Python:
import serial.tools.list_ports
ports = serial.tools.list_ports.comports()
for p in ports:
    print(p)
```

**Linux/macOS**:
```bash
ls /dev/tty*
```

---

## Operating Instructions

### Launch Publisher Module

```bash
# Activate virtual environment (if used)
gmr_env\Scripts\activate  # Windows
source gmr_env/bin/activate  # Linux/macOS

# Run publisher
python GMR-UIN-R1A-Publisher.py
```

### Launch Subscriber Module

In a separate terminal:

```bash
# Activate virtual environment
gmr_env\Scripts\activate  # Windows

# Run subscriber
python GMR-UIN-R1A-Subscriber.py
```

### Publisher GUI Operations

1. **Connect Arduino**: Click "Hubungkan Serial" (Connect Serial)
2. **Start Data Collection**: Click "Mulai Pengumpulan Data" (Start Collection)
3. **Monitor MQTT Status**: Observe connection indicator
4. **Export Data**: File → Export CSV to save measurements
5. **View Real-time Plot**: Graph updates automatically during collection

### Publisher GUI Preview

![Publisher GUI](src/publisher-GUI.png)

### Subscriber GUI Operations

1. **Connection Status**: Green indicator when connected to MQTT broker
2. **Real-time Plot**: Displays magnetic field (B) vs. time
3. **Data Table**: Shows latest measurements
4. **Export Function**: Save monitored data as CSV
5. **Publisher Status**: Displays connected/disconnected status

### Subscriber GUI Preview

![Subscriber GUI](src/subscriber-GUI.png)

### Light Mode Operation

For simplified, resource-efficient operation:

```bash
python light-mode/Light-Publisher.py
python light-mode/Light-Subscriber.py
```

---

## Calibration Procedures

### Magnetic Field Conversion

The system converts raw voltage measurements to magnetic field values using a linear calibration formula:

$$B = a \cdot V + b$$

Where:
- $B$ = Magnetic field (unit: Tesla or mT, as calibrated)
- $V$ = Sensor voltage (Volts)
- $a$ = Slope coefficient (default: 5.3381)
- $b$ = Intercept coefficient (default: -4.2983)

### Calibration Steps

1. **Obtain Reference Standards**: Use calibrated magnetic field sources (e.g., Helmholtz coil)

2. **Collect Reference Data**:
   - Apply known magnetic field strengths
   - Record corresponding sensor voltages
   - Generate minimum 5 data points covering measurement range

3. **Calculate Coefficients**:
   ```python
   import numpy as np
   
   # Reference data
   voltages = [0.8, 1.2, 1.6, 2.0, 2.4]  # Volts
   fields = [0.0, 2.5, 5.0, 7.5, 10.0]    # mT
   
   # Linear regression
   coeffs = np.polyfit(voltages, fields, 1)
   a = coeffs[0]  # Slope
   b = coeffs[1]  # Intercept
   ```

4. **Update Calibration**:
   ```python
   def tegangan_ke_b(v):
       return a * v + b  # Replace 'a' and 'b' with calculated values
   ```

5. **Validate**: Re-measure reference standards and verify accuracy

---

## Troubleshooting

### Serial Communication Issues

**Problem**: "Serial port not found" or "Port already in use"

**Solutions**:
- Verify Arduino connection: Check Device Manager (Windows) or `ls /dev/tty*` (Linux)
- Confirm correct COM port in configuration
- Ensure serial driver installed (CH340 or FTDI)
- Close other serial monitor applications
- Restart Arduino board

**Problem**: Garbled data or no data from serial

**Solutions**:
- Verify baud rate matches Arduino configuration (must be 9600)
- Check USB cable quality and connection
- Test with Arduino IDE Serial Monitor at 9600 baud
- Recompile and re-upload Arduino firmware

### MQTT Connection Issues

**Problem**: "Connection refused" or "Unable to connect to broker"

**Solutions**:
- Verify MQTT broker IP address in configuration
- Check broker is running: `mosquitto -v` (command line test)
- Verify network connectivity: `ping <broker_ip>`
- Check firewall allows port 1883
- Verify MQTT port matches configuration (default: 1883)

**Problem**: "No messages received" in Subscriber

**Solutions**:
- Confirm Publisher connected successfully (check status indicator)
- Verify MQTT topics match between Publisher and Subscriber
- Check MQTT broker is receiving messages:
  ```bash
  mosquitto_sub -h <broker_ip> -t "gmr/data"
  ```
- Restart both Publisher and Subscriber applications

### GUI/Display Issues

**Problem**: Graphs not updating or freezing interface

**Solutions**:
- Ensure matplotlib properly installed: `pip install --upgrade matplotlib`
- Check system resources (RAM, CPU usage)
- Reduce data collection rate
- Restart application

**Problem**: CSV export fails

**Solutions**:
- Verify write permissions in target directory
- Check available disk space
- Ensure pandas library installed: `pip install --upgrade pandas`

### Python Runtime Issues

**Problem**: Module import errors (e.g., "No module named 'paho'")

**Solutions**:
- Verify virtual environment activated
- Reinstall dependencies: `pip install -r requirements.txt`
- Check Python version: `python --version` (must be 3.8+)

---

## Directory Structure

```
MQTT-GMR-Sensor-System-UIN-R1A-/
├── README.md                      # This file
├── requirements.txt               # Python dependencies
├── main/
│   └── main.ino                   # Arduino firmware (ADS1115 interface)
├── patch1-0-0/
│   ├── dark-mode/
│   │   ├── GMR-UIN-R1A-Publisher.py      # Full-featured publisher module
│   │   └── GMR-UIN-R1A-Subscriber.py     # Full-featured subscriber module
│   └── light-mode/
│       ├── Light-Publisher.py            # Simplified publisher (low resource)
│       └── Light-Subscriber.py           # Simplified subscriber (low resource)
├── patch1-1/
│   ├── 1_GMR-UIN-R1A-Publisher.py        # Updated publisher module
│   └── 1_GMR-UIN-R1A-Subscriber.py       # Updated subscriber module
└── src/
    ├── publisher-GUI.png                 # Publisher GUI preview
    └── subscriber-GUI.png                # Subscriber GUI preview
```

### File Descriptions

| File | Purpose | Platform |
|------|---------|----------|
| `main/main.ino` | Arduino firmware for ADS1115 sensor reading | Arduino IDE |
| `patch1-0-0/dark-mode/GMR-UIN-R1A-Publisher.py` | Serial acquisition, MQTT publishing, GUI | Python (Windows/Linux/macOS) |
| `patch1-0-0/dark-mode/GMR-UIN-R1A-Subscriber.py` | MQTT subscription, real-time visualization | Python (Windows/Linux/macOS) |
| `patch1-0-0/light-mode/Light-Publisher.py` | Resource-optimized publisher variant | Python |
| `patch1-0-0/light-mode/Light-Subscriber.py` | Resource-optimized subscriber variant | Python |
| `patch1-1/1_GMR-UIN-R1A-Publisher.py` | Updated publisher module | Python |
| `patch1-1/1_GMR-UIN-R1A-Subscriber.py` | Updated subscriber module | Python |
| `src/publisher-GUI.png` | Screenshot of publisher GUI interface | Image |
| `src/subscriber-GUI.png` | Screenshot of subscriber GUI interface | Image |

---

## Contact & Support

For technical inquiries or contributions, please contact the project maintainers:

**Institution**: Universitas Islam Negeri Sunan Gunung Djati Bandung
**Department**: [Jurusan Fisika, Fakultas Sains dan Teknologi, UIN Sunan Gunung Djati Bandung]
**Last Updated**: May 8, 2026

---

## Citation

If you utilize this system in your research, please cite as follows:

```bibtex
@software{gmr_mqtt_2026,
  title   = {MQTT-based Giant Magnetoresistance Sensor System (GMR-UIN-R1A)},
  author  = {G8lang Pratama Putra Siswanto},
  year    = {2026},
  url     = {https://github.com/gilangpps/MQTT-GMR-Sensor-System-UIN-R1A-.git},
  organization = {Bex 7386 Mini-Techlab}
}
```

---

**Document Version**: 1.0
**Last Modified**: May 8, 2026
