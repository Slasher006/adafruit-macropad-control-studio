#!/usr/bin/env python3
"""Install current firmware and source profiles while preserving each device layout."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "desktop"))

from macropad_configurator.device_io import (  # noqa: E402
    backup_device,
    device_health,
    discover_devices,
    read_device_project,
    send_command,
    sync_project,
)
from macropad_configurator.models import normalize_project  # noqa: E402


def source_profiles() -> list[dict]:
    profile_root = ROOT / "device" / "profiles"
    index = json.loads((profile_root / "index.json").read_text(encoding="utf-8"))
    return [
        json.loads((profile_root / entry["file"]).read_text(encoding="utf-8"))
        for entry in index["profiles"]
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uid", action="append", help="Only sync this device UID; repeat for multiple devices")
    parser.add_argument("--backup-root", type=Path, default=Path("/tmp/macropad-sync-backups"))
    args = parser.parse_args()

    wanted = {uid.upper() for uid in args.uid or []}
    devices = [device for device in discover_devices() if not wanted or device.uid.upper() in wanted]
    if wanted != {device.uid.upper() for device in devices} and wanted:
        missing = sorted(wanted - {device.uid.upper() for device in devices})
        parser.error("device UID not found: " + ", ".join(missing))
    if not devices:
        parser.error("no MacroPad devices found")

    profiles = source_profiles()
    for device in devices:
        health = device_health(device)
        if health["missing"]:
            parser.error(f"{device.uid} is missing required libraries: {', '.join(health['missing'])}")
        current = read_device_project(device)
        backup = backup_device(device, args.backup_root)
        project = normalize_project(
            {
                "schema_version": 1,
                "keyboard_layout": current["keyboard_layout"],
                "profiles": profiles,
            }
        )
        revision = sync_project(device, project)
        shutil.copy2(ROOT / "device" / "macropad_core.py", device.mount / "macropad_core.py")
        shutil.copy2(ROOT / "device" / "code.py", device.mount / "code.py")
        if hasattr(os, "sync"):
            os.sync()
        try:
            send_command({"cmd": "reload_config"}, device.uid, timeout=3.0)
        except Exception:
            pass
        print(
            f"synced uid={device.uid} layout={project['keyboard_layout']} "
            f"profiles={len(project['profiles'])} revision={revision} backup={backup}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
