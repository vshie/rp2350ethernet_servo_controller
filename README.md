# RP2350 Ethernet Servo Controller
<img width="410" alt="image" src="https://github.com/user-attachments/assets/e1f43057-8154-4782-b9f7-2954efc5299f" />


A web-based servo controller for the Raspberry Pi Pico (RP2040) with Ethernet connectivity using the CH9120 Ethernet module.

## Overview

This project implements a web server on the RP2040 microcontroller that allows remote control of up to three servos (tilt, zoom, and focus) through a simple web interface. The system uses the CH9120 Ethernet module to provide network connectivity.

## Hardware Requirements

- Raspberry Pi Pico (RP2040)
- CH9120 Ethernet Module
- 3 Servo Motors
- Power supply for servos
- Jumper wires

## Pin Connections

### CH9120 Module
- TX: GPIO20
- RX: GPIO21
- CFG: GPIO18
- RST: GPIO19

### Servo Motors
- Tilt Servo: GPIO2
- Zoom Servo: GPIO3
- Focus Servo: GPIO4

## Features

- Web-based control interface
- Real-time servo position adjustment
- Persistent storage of servo positions
- Support for three independent servos
- Simple HTTP API for integration

## Web Interface

The web interface provides sliders for each servo with the following features:
- Range: 1000-2000 μs
- Real-time position updates
- Numeric input option
- Automatic position saving

## API Endpoints

- `GET /` - Serves the web interface
- `GET /set?{servo}={value}` - Sets servo position
  - Parameters:
    - `servo`: tilt, zoom, or focus
    - `value`: position in microseconds (1000-2000)

## Setup

1. Flash the RP2040 with the provided firmware
2. Connect the CH9120 module and servos according to the pin connections
3. Power on the system
4. Access the web interface at http://192.168.2.42

## Dependencies

- MicroPython for RP2040
- CH9120 Ethernet module driver

## License

This project is open source and available under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 
