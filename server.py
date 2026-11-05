"""
Smart Parking bridge: Arduino (USB serial) -> Wi-Fi -> phone browser.

Usage:
    pip install flask pyserial
    python server.py            # auto-detects the Arduino port
    python server.py COM5       # or give the port (Windows)
    python server.py /dev/ttyACM0   # Linux / /dev/cu.usbmodemXXXX on Mac

Then open the printed http://<laptop-ip>:5000 address on your phone
(phone and laptop must be on the same Wi-Fi / hotspot).

Lot layout (10 slots):
  - 2 slots are LIVE: they follow the two ultrasonic sensors (S1, S2).
    Their position on the screen is picked at random when the server starts
    (never in the same row, never side by side) and can be re-shuffled.
    Which slot a sensor is shown as is only a label - the physical sensors
    do not move.
  - the other 8 slots are SIMULATED: cars arrive and leave at random, so
    the "nearest free slot" has something to choose from.
"""
import os
import random
import socket
import sys
import threading
import time

import serial
import serial.tools.list_ports
from flask import Flask, jsonify, send_from_directory

BAUD = 9600
HTTP_PORT = 5000
STALE_AFTER_S = 3          # no data for this long -> show "Arduino disconnected"
PORT_ARG = sys.argv[1] if len(sys.argv) > 1 else None
HERE = os.path.dirname(os.path.abspath(__file__))

# ---- lot layout -------------------------------------------------------------
LEFT_SLOTS = [f"A{i}" for i in range(1, 6)]     # A1 (top) ... A5 (bottom)
RIGHT_SLOTS = [f"B{i}" for i in range(1, 6)]    # B1 (top) ... B5 (bottom)
ALL_SLOTS = LEFT_SLOTS + RIGHT_SLOTS
MIN_ROW_GAP = 2            # the two live slots are at least this many rows apart

# simulated slots: how long a simulated car stays / how long a slot stays free (seconds)
SIM_OCCUPIED_FOR = (15, 40)
SIM_FREE_FOR = (6, 20)
SIM_START_OCCUPIED = 0.7   # share of simulated slots that start occupied

state = {"slot1": False, "slot2": False, "d1": None, "d2": None, "updated": 0.0, "port": None}
lock = threading.Lock()
app = Flask(__name__)

live_map = {"S1": None, "S2": None}   # sensor -> slot id, e.g. {"S1": "A3", "S2": "B5"}
sim = {}                              # slot id -> {"occ": bool, "until": float}


def pick_live_slots(previous=None):
    """Return (slot for S1, slot for S2): one on each side, rows >= MIN_ROW_GAP apart.
    If `previous` is given, the new pair uses different positions."""
    for _ in range(500):
        left = LEFT_SLOTS[random.randrange(5)]
        right = RIGHT_SLOTS[random.randrange(5)]
        if abs(int(left[1:]) - int(right[1:])) < MIN_ROW_GAP:
            continue
        pair = (left, right) if random.random() < 0.5 else (right, left)
        if previous and set(pair) == set(previous):
            continue
        return pair
    return ("A2", "B5")    # unreachable in practice


def init_layout():
    now = time.time()
    pair = pick_live_slots(None)
    live_map["S1"], live_map["S2"] = pair
    for sid in ALL_SLOTS:
        occ = random.random() < SIM_START_OCCUPIED
        sim[sid] = {"occ": occ, "until": now + random.uniform(*(SIM_OCCUPIED_FOR if occ else SIM_FREE_FOR))}


def sim_step(now):
    """Flip simulated slots whose timer has run out (called under the lock)."""
    for s in sim.values():
        if now >= s["until"]:
            s["occ"] = not s["occ"]
            s["until"] = now + random.uniform(*(SIM_OCCUPIED_FOR if s["occ"] else SIM_FREE_FOR))


def find_arduino_port():
    ports = list(serial.tools.list_ports.comports())
    keywords = ("arduino", "ch340", "ch341", "usb serial", "usb-serial", "wch", "cp210", "ftdi")
    for p in ports:
        text = f"{p.description} {p.manufacturer}".lower()
        if any(k in text for k in keywords):
            return p.device
    return ports[0].device if ports else None


def to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def serial_reader():
    while True:
        port = PORT_ARG or find_arduino_port()
        if not port:
            print("No serial port found - is the Arduino plugged in? Retrying...")
            time.sleep(2)
            continue
        try:
            with serial.Serial(port, BAUD, timeout=2) as ser:
                print(f"Connected to Arduino on {port}")
                with lock:
                    state["port"] = port
                while True:
                    line = ser.readline().decode(errors="ignore").strip()
                    if not line.startswith("S1="):
                        continue
                    parts = dict(kv.split("=", 1) for kv in line.split(",") if "=" in kv)
                    with lock:
                        state["slot1"] = parts.get("S1") == "1"
                        state["slot2"] = parts.get("S2") == "1"
                        state["d1"] = to_int(parts.get("D1"))
                        state["d2"] = to_int(parts.get("D2"))
                        state["updated"] = time.time()
        except (serial.SerialException, OSError) as e:
            print(f"Serial error on {port}: {e}")
            print("(Close the Arduino IDE Serial Monitor if it is open.) Retrying in 2 s...")
            time.sleep(2)


@app.route("/")
def index():
    return send_from_directory(HERE, "index.html")


@app.route("/status")
def status():
    with lock:
        now = time.time()
        sim_step(now)
        age = now - state["updated"] if state["updated"] else None
        data = dict(state)
        slots = {}
        for sid in ALL_SLOTS:
            if sid == live_map["S1"]:
                slots[sid] = {"live": True, "sensor": "S1", "occ": state["slot1"], "dist": state["d1"]}
            elif sid == live_map["S2"]:
                slots[sid] = {"live": True, "sensor": "S2", "occ": state["slot2"], "dist": state["d2"]}
            else:
                slots[sid] = {"live": False, "sensor": None, "occ": sim[sid]["occ"], "dist": None}
        data["slots"] = slots
        data["liveMap"] = dict(live_map)
    data["age"] = age
    data["connected"] = age is not None and age < STALE_AFTER_S
    resp = jsonify(data)
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.route("/shuffle", methods=["POST"])
def shuffle():
    """Move the two sensor slots to new random positions (labels only)."""
    with lock:
        pair = pick_live_slots(previous=(live_map["S1"], live_map["S2"]))
        live_map["S1"], live_map["S2"] = pair
        result = dict(live_map)
    print(f"Shuffled: Sensor 1 = {result['S1']}, Sensor 2 = {result['S2']}")
    return jsonify(result)


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))   # no data is sent; just picks the Wi-Fi interface
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


init_layout()

if __name__ == "__main__":
    threading.Thread(target=serial_reader, daemon=True).start()
    print("=" * 52)
    print(f"  Open on your phone:  http://{lan_ip()}:{HTTP_PORT}")
    print(f"  Sensor 1 is shown as {live_map['S1']}, Sensor 2 as {live_map['S2']}")
    print("=" * 52)
    app.run(host="0.0.0.0", port=HTTP_PORT, debug=False, threaded=True)
