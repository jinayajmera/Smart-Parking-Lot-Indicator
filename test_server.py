"""Tests for the gateway (server.py): slot placement, simulation, /status, /shuffle and the serial reader."""
import sys
import time
from pathlib import Path

import pytest
import serial

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.argv = ["server.py"]          # keep pytest's own arguments out of PORT_ARG
import server                     # noqa: E402


@pytest.fixture()
def client():
    server.init_layout()
    server.state.update(slot1=False, slot2=False, d1=None, d2=None, updated=0.0)
    return server.app.test_client()


def test_to_int():
    assert server.to_int("28") == 28
    assert server.to_int(None) is None
    assert server.to_int("abc") is None


def test_pick_live_slots_rules():
    seen = set()
    for _ in range(3000):
        a, b = server.pick_live_slots()
        sides = {a[0], b[0]}
        assert sides == {"A", "B"}                              # one on each side
        assert abs(int(a[1]) - int(b[1])) >= server.MIN_ROW_GAP  # never close together
        seen.add(frozenset((a, b)))
    assert len(seen) == 12                                      # all 12 allowed pairs occur


def test_pick_live_slots_moves_on_shuffle():
    prev = ("A1", "B4")
    for _ in range(500):
        assert set(server.pick_live_slots(previous=prev)) != set(prev)


def test_sim_step_flips_expired_slots():
    server.init_layout()
    now = time.time()
    for s in server.sim.values():
        s["until"] = now - 1
    before = {k: v["occ"] for k, v in server.sim.items()}
    server.sim_step(now)
    assert all(server.sim[k]["occ"] != before[k] for k in before)
    assert all(v["until"] > now for v in server.sim.values())


def test_status_shape_and_live_slots(client):
    server.state.update(slot1=True, slot2=False, d1=28, d2=140, updated=time.time())
    r = client.get("/status")
    data = r.get_json()
    assert r.headers["Cache-Control"] == "no-store"
    assert len(data["slots"]) == 10
    assert data["connected"] is True
    s1, s2 = server.live_map["S1"], server.live_map["S2"]
    assert data["slots"][s1] == {"live": True, "sensor": "S1", "occ": True, "dist": 28}
    assert data["slots"][s2] == {"live": True, "sensor": "S2", "occ": False, "dist": 140}
    assert sum(1 for v in data["slots"].values() if v["live"]) == 2
    for key in ("slot1", "slot2", "d1", "d2", "liveMap", "age"):
        assert key in data


def test_status_goes_offline_when_data_is_stale(client):
    server.state.update(updated=time.time() - (server.STALE_AFTER_S + 1))
    assert client.get("/status").get_json()["connected"] is False
    server.state.update(updated=0.0)
    assert client.get("/status").get_json()["connected"] is False


def test_shuffle_moves_live_slots(client):
    before = dict(server.live_map)
    r = client.post("/shuffle")
    assert r.status_code == 200
    assert set(r.get_json().values()) != set(before.values())
    assert client.get("/shuffle").status_code == 405


def test_index_is_served(client):
    r = client.get("/")
    assert r.status_code == 200 and b"Smart Parking" in r.data
    r.close()


class _Stop(BaseException):
    """Raised from the patched sleep() to leave serial_reader's endless loop."""


def test_serial_reader_parses_lines(monkeypatch):
    lines = [b"BOOT\n", b"garbage\n", b"S1=1,S2=0,D1=28,D2=140\n", b"S1=0,S2=1,D1=999,D2=33\n"]

    class FakeSerial:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def readline(self):
            if lines:
                return lines.pop(0)
            raise serial.SerialException("unplugged")

    def stop(_):
        raise _Stop()

    monkeypatch.setattr(server.serial, "Serial", FakeSerial)
    monkeypatch.setattr(server.time, "sleep", stop)
    monkeypatch.setattr(server, "PORT_ARG", "COM_TEST")
    with pytest.raises(_Stop):
        server.serial_reader()
    assert server.state["slot1"] is False and server.state["slot2"] is True
    assert server.state["d1"] == 999 and server.state["d2"] == 33
    assert server.state["port"] == "COM_TEST"
