# RP2350 Ethernet Servo Controller
![image](https://github.com/user-attachments/assets/ca048de4-cd8e-493e-a3e1-ab9dbf0fb050)

<img width="1678" alt="image" src="https://github.com/user-attachments/assets/1768c7a7-fa38-406a-8833-bc74d9c526a3" />


A web-based servo controller for the Raspberry Pi Pico (RP2350) with Ethernet connectivity using the CH9120 Ethernet module. 
https://www.waveshare.com/wiki/RP2350-ETH 
https://www.amazon.com/dp/B0C3R86WFB?ref=ppx_yo2ov_dt_b_fed_asin_title

## Overview

This project implements a web server on the RP2350 microcontroller that allows remote control of up to three servos (tilt, zoom, and focus) through a simple web interface. The system uses the CH9120 Ethernet module to provide network connectivity.

## Hardware Requirements

- Raspberry Pi Pico (RP2350)
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
-- Yaw Servo (external): GPIO5 

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
## First hardware usage - Setup
1. Connect USB-C cable from computer to module
2. Push and hold boot and reset buttons, then release reset, then release boot. A file volume will appear on your OS.
3. Drag and drop rp2-pico-20230209-unstable-v1.19.1.uf2 to the drive that shows up. The board will restart and the file volume disconnect.
4. Install mpremote: pip install mpremote
## Setup
Make sure to setup device with rp2-pico-20230209-unstable-v1.19.1.uf2
1. Flash the RP2350 with the provided firmware: mpremote cp main.py :main.py and mpremote cp ch9120.py :ch9120.py
2. Connect the servos according to the pin connections
3. Power on the system - if debugging, run main.py with mpremote run main.py (otherwise main.py runs on boot)
4. Access the web interface at http://192.168.2.42

## Dependencies

- MicroPython for RP2350
- CH9120 Ethernet module driver

## License

This project is open source and available under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 
