"""Compiles the real .ino on the host with a mocked Arduino core and runs the checks."""
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).parent / "firmware"


@pytest.mark.skipif(shutil.which("g++") is None, reason="g++ not installed")
def test_firmware_logic(tmp_path):
    exe = tmp_path / "test_firmware"
    build = subprocess.run(
        ["g++", "-std=c++17", "-Wall", "-o", str(exe), str(HERE / "test_firmware.cpp")],
        capture_output=True, text=True)
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(exe)], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
