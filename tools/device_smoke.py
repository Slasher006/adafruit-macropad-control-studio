#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "desktop"))

from macropad_configurator.device_io import (  # noqa: E402
    DeviceError,
    clear_preview,
    discover_devices,
    parse_boot_out,
    preview_lighting,
    read_device_project,
    send_command,
    sync_project,
)


def wait_for_layout(uid: str, layout: str, timeout: float = 20.0):
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            response = send_command({"cmd": "ping"}, uid, timeout=2.0)
            if response.get("layout") == layout:
                return response
        except DeviceError as exc:
            last_error = exc
        time.sleep(0.5)
    raise DeviceError(f"device did not restart with {layout!r} layout: {last_error}")


def wait_for_mount(mount: Path, timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if parse_boot_out(mount) is not None:
            return
        time.sleep(0.25)
    raise DeviceError(f"CIRCUITPY did not remount at {mount}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Non-destructive MacroPad hardware smoke test")
    parser.add_argument("--mount", type=Path)
    args = parser.parse_args()
    devices = discover_devices()
    if args.mount:
        devices = [device for device in devices if device.mount.resolve() == args.mount.resolve()]
    if not devices:
        parser.error("no matching MacroPad device found")
    device = devices[0]
    project = read_device_project(device)
    original_layout = project["keyboard_layout"]
    print(f"device {device.uid} at {device.mount}")
    print(f"imported {len(project['profiles'])} profiles")

    for layout in ("de", "us"):
        project["keyboard_layout"] = layout
        revision = sync_project(device, project)
        try:
            send_command({"cmd": "reload_config"}, device.uid, timeout=2.0)
        except DeviceError:
            pass
        response = wait_for_layout(device.uid, layout)
        wait_for_mount(device.mount)
        print(f"layout {layout}: revision {revision}, profile {response.get('profile')}")

    profile = project["profiles"][0]
    original_brightness = profile["brightness"]
    original_colors = [control["idle_color"] for control in profile["keys"]]
    profile["brightness"] = 8
    for control in profile["keys"]:
        control["idle_color"] = "#220044"
    preview_lighting(device, profile)
    time.sleep(0.5)
    clear_preview(device)
    profile["brightness"] = original_brightness
    for control, color in zip(profile["keys"], original_colors):
        control["idle_color"] = color
    print("RGB preview and clear: ok")

    project["keyboard_layout"] = original_layout
    sync_project(device, project)
    try:
        send_command({"cmd": "reload_config"}, device.uid, timeout=2.0)
    except DeviceError:
        pass
    wait_for_layout(device.uid, original_layout)
    wait_for_mount(device.mount)
    print(f"restored layout {original_layout}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
