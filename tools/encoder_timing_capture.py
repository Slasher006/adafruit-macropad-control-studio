#!/usr/bin/env python3
"""Capture live MacroPad encoder edge and profile-load timings."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import serial


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "desktop"))

from macropad_configurator.device_io import find_serial_port, parse_serial_json  # noqa: E402


def send(connection: serial.Serial, payload: dict) -> None:
    connection.write((json.dumps(payload) + "\n").encode("utf-8"))
    connection.flush()


def summarize(events: list[dict]) -> None:
    edges = [event for event in events if event.get("phase") == "edge"]
    loads = [event for event in events if event.get("phase") == "loaded"]
    intervals = [event["since_previous_ms"] for event in edges if event.get("since_previous_ms") is not None]
    load_times = [event["load_ms"] for event in loads]
    print("\nSUMMARY")
    print(f"edges={len(edges)} accepted={sum(bool(event.get('accepted')) for event in edges)} loads={len(loads)}")
    if intervals:
        print(
            "edge_interval_ms="
            f"min:{min(intervals)} median:{int(statistics.median(intervals))} max:{max(intervals)}"
        )
    if load_times:
        print(
            "profile_load_ms="
            f"min:{min(load_times)} median:{int(statistics.median(load_times))} max:{max(load_times)}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=float, default=20.0)
    args = parser.parse_args()
    port = find_serial_port()
    if not port:
        parser.error("MacroPad serial port not found")

    events: list[dict] = []
    with serial.Serial(port, 115200, timeout=0.1, write_timeout=1.0) as connection:
        time.sleep(0.25)
        connection.reset_input_buffer()
        send(connection, {"cmd": "encoder_trace", "enabled": True})
        print(f"TRACE READY — turn the encoder for {args.duration:g} seconds", flush=True)
        deadline = time.monotonic() + args.duration
        try:
            while time.monotonic() < deadline:
                payload = parse_serial_json(connection.readline().decode("utf-8", "replace"))
                if payload and payload.get("event") == "encoder_trace":
                    events.append(payload)
                    print(json.dumps(payload, sort_keys=True), flush=True)
        finally:
            send(connection, {"cmd": "encoder_trace", "enabled": False})

    summarize(events)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
