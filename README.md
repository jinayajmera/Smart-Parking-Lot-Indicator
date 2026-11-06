# Smart Parking Lot Indicator

[![tests](https://github.com/jinayajmera/smart-parking-lot-indicator/actions/workflows/ci.yml/badge.svg)](https://github.com/jinayajmera/smart-parking-lot-indicator/actions/workflows/ci.yml)
![Arduino Uno](https://img.shields.io/badge/board-Arduino%20Uno-00979D)
![Python](https://img.shields.io/badge/python-3.8%2B-3776AB)
![License](https://img.shields.io/badge/license-MIT-green)

An Arduino Uno parking indicator with a live phone display. Two ultrasonic sensors watch two bays and drive red and green LEDs on their own, and the same readings are streamed over USB to a small Python gateway that serves a live ten-bay map to a phone. The map shows the **nearest free bay**, an **estimated distance** and **animated arrows** from the entry to it.

<p align="center">
  <img src="docs/images/prototype.jpg" alt="The prototype: Arduino, two HC-SR04 sensors, LEDs and the live display on the laptop" width="720">
</p>

## Features

- **Stand-alone indication.** The Uno decides full or empty and drives the LEDs itself: a red/green pair per live bay, and an entry pair that turns red when both live bays are full. No laptop is needed for this part.
- **Stable readings.** Median of three readings per sensor plus a 50 / 55 cm hysteresis band, so a bad echo or a car resting at the threshold does not make a lamp flicker.
- **Live ten-bay map.** Two bays follow the real sensors; the other eight are simulated so the lot behaves like a busy one. The two live bays appear at random, non-adjacent positions and can be re-shuffled.
- **Nearest free bay and distance**, from the entry gate or the building door.
- **Arrow guidance** up the lane and into the bay, with a sentence such as "Go straight up the lane, pass 1 row, then turn right into B4". If the bay is taken on the way, the route moves and a notice says which bay was taken.
- **Connection pill** showing **Live**, **Offline** or **Demo**.
- **No cloud, no accounts, no extra hardware.** The page has no external dependencies, and opening `index.html` directly runs a demo mode with no Arduino.

<p align="center">
  <img src="docs/images/display.png" alt="Phone display with nearest slot, distance and arrow route" width="300"><br>
  <em>The display page with sample readings</em>
</p>

## How it works

<p align="center"><img src="docs/images/architecture.png" alt="Sensors, Arduino, USB serial, Python gateway, phone browser" width="720"></p>

1. **Arduino Uno** (`arduino/smart_parking/smart_parking.ino`) reads both HC-SR04 sensors, filters the readings, applies the hysteresis rule, switches the LEDs and prints one line per cycle, for example `S1=1,S2=0,D1=28,D2=140`.
2. **Gateway** (`server.py`) reads that line from the USB serial port in a background thread, keeps the latest state, adds the eight simulated bays, and serves the page and a JSON endpoint with Flask.
3. **Display** (`index.html`) is a single page that asks `/status` about every 0.4 s, draws the lot, picks the nearest free bay and animates the route.

The lot has ten bays: **A1-A5** on the left of the lane and **B1-B5** on the right, row 1 at the top (near the building) and row 5 at the bottom (near the entry gate). The distance to a bay uses a small model of the lot: 6 m from the start to the first row, 2.7 m per row passed and 5.5 m across the lane, so `distance = 6 + (p + 0.5) × 2.7 + 5.5` metres for `p` rows passed. Ties go to the left side.

## Hardware

| Part | Qty | Notes |
|---|---|---|
| Arduino Uno | 1 | Powered and read over USB |
| HC-SR04 ultrasonic sensor | 2 | One per live bay |
| LED, green / red | 3 / 3 | Slot 1, slot 2, entry |
| Resistors | 6 | One in series with each LED (220 Ω is a typical value) |
| Breadboard, jumper wires, USB cable | - | |

<p align="center"><img src="docs/images/wiring.png" alt="Arduino Uno pin allocation" width="480"></p>

| Arduino pin | Connected to |
|---|---|
| D4 / D5 | Slot 1 green / red LED |
| D6 / D7 | Slot 2 green / red LED |
| D8 / D9 | Entry green / red LED |
| D10 / D11 | Sensor 1 TRIG / ECHO |
| D12 / D13 | Sensor 2 TRIG / ECHO |

Sensor VCC goes to 5 V and GND to GND; each LED goes through a resistor to GND. Point each sensor at where the car stops: a reading **below 50 cm** marks the bay full, and it is released only when the reading is **above 55 cm**. The sensors are read one at a time with a 40 ms gap so they do not disturb each other, and one pass of the loop takes roughly 0.2 to 0.4 s.

## Quick start

**You need:** Python 3.8+, the Arduino IDE and a USB cable. The laptop and the phone should be on the same Wi-Fi (a phone hotspot works well).

1. **Upload the firmware.** Open `arduino/smart_parking/smart_parking.ino` in the Arduino IDE, choose *Tools → Board → Arduino Uno* and your port, then click *Upload*.
2. **Close the Serial Monitor.** Only one program can use the USB port at a time.
3. **Start the gateway.**
   - Windows: double-click `run.bat` (or `run.bat COM5` to choose the port).
   - macOS / Linux: `bash run.sh` (or `bash run.sh /dev/ttyACM0`).
   - Manually: `pip install -r requirements.txt`, then `python server.py [PORT]`.

   It prints something like:
   ```
   Open on your phone:  http://192.168.43.120:5000
   Sensor 1 is shown as A3, Sensor 2 as B5
   Connected to Arduino on COM5
   ```
4. **Open the printed address** (with `http://` and `:5000`) on the phone. The pill at the top right should say **Live**.

**No Arduino?** Double-click `index.html` to open it in **Demo** mode with two tappable bays.

## Project structure

```
├── arduino/smart_parking/smart_parking.ino   # firmware for the Uno
├── server.py                                 # gateway: serial reader + Flask server
├── index.html                                # phone display (served by server.py; keep it next to it)
├── run.bat / run.sh                          # one-step start for Windows / macOS-Linux
├── requirements.txt                          # flask, pyserial
├── tests/                                    # pytest suite (gateway + real firmware logic)
└── docs/images/                              # images used in this README
```

## Configuration

| What | Where | Default |
|---|---|---|
| Bay becomes **full** below | `FULL_BELOW_CM` in the `.ino` | 50 cm |
| Bay becomes **empty** above | `EMPTY_ABOVE_CM` in the `.ino` | 55 cm |
| Echo time-out | `pulseIn(..., 30000UL)` in the `.ino` | 30 ms (about 5 m) |
| Serial speed | `Serial.begin` / `BAUD` | 9600 |
| Data is "stale" after | `STALE_AFTER_S` in `server.py` | 3 s |
| Web port | `HTTP_PORT` in `server.py` | 5000 |
| Simulated bay timings | `SIM_OCCUPIED_FOR`, `SIM_FREE_FOR`, `SIM_START_OCCUPIED` | 15-40 s, 6-20 s, 70 % |
| Lot scale for distances | `SCALE` in `index.html` | 6 m, 2.7 m per row, 5.5 m |
| Poll interval | `POLL_MS` in `index.html` | 400 ms |

## Serial protocol and HTTP API

The Arduino prints one line per cycle at 9600 baud: `S1=1,S2=0,D1=28,D2=140`. `S1`, `S2` are the bay states (1 full, 0 empty) and `D1`, `D2` the distance in cm after the median filter (`999` = no echo). The gateway ignores any line that does not start with `S1=`.

| Route | Method | Returns |
|---|---|---|
| `/` | GET | The display page |
| `/status` | GET | The whole lot as JSON: both sensors, all ten bays, which bay each sensor is shown as, the age of the last reading and a `connected` flag (true while the last line is under 3 s old) |
| `/shuffle` | POST | Moves the two live sensors to new random bay positions |

```json
{
  "connected": true, "age": 0.01,
  "slot1": true, "slot2": false, "d1": 28, "d2": 140,
  "liveMap": { "S1": "A2", "S2": "B4" },
  "slots": {
    "A1": { "live": false, "sensor": null, "occ": true,  "dist": null },
    "A2": { "live": true,  "sensor": "S1", "occ": true,  "dist": 28 },
    "B4": { "live": true,  "sensor": "S2", "occ": false, "dist": 140 }
  }
}
```
*(abridged: the real reply lists all ten bays)*

## Tests

```bash
pip install -r requirements.txt pytest
pytest -q
```

The suite checks the gateway (live-bay placement rules, simulation, `/status`, `/shuffle`, serial line parsing) and compiles the unchanged `.ino` on the PC with a mocked Arduino core (needs `g++`) to check the distance conversion, median filter, hysteresis rule, LED logic and printed line.

## Troubleshooting

| Problem | Fix |
|---|---|
| "Access is denied" / cannot open port | Close the Arduino IDE Serial Monitor, wait 2 s |
| Wrong COM port picked | `run.bat COM5` (or `bash run.sh /dev/ttyACM0`) |
| Phone page does not load | Put both devices on the same Wi-Fi; allow Python through Windows Firewall on Private networks |
| Page says it needs the new `server.py` | An old server is still running; close it and start again |
| No data from the Arduino / pill says **Offline** | Check the cable and port, that the sketch is uploaded, and that nothing else holds the port |

## Notes

- Two bays on screen follow the real sensors; the other eight are simulated (tagged **SIM**). "Shuffle sensor slots" only changes which bays the sensors are shown as.
- Distances are estimates from an assumed lot scale, and the arrows are drawn from the map rather than by tracking a car.
- The phone is a display only; it does not reserve or control anything.

## Roadmap

- Sensors on the remaining eight bays in place of the simulated ones
- A temperature sensor to correct the speed of sound in the distance formula
- Wi-Fi on the board itself (for example an ESP32) so the page can be served without a laptop
- Entry and exit counters and a log of how long each bay stays occupied

## License

[MIT](LICENSE) © Jinay Ajmera
