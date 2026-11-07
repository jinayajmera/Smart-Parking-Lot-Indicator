#!/usr/bin/env bash
# Starts the Smart Parking gateway on macOS / Linux.
# Optional: bash run.sh /dev/ttyACM0   to choose the Arduino port.
cd "$(dirname "$0")" || exit 1
python3 -m pip install -r requirements.txt
python3 server.py "$@"
