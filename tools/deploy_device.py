#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import serial
from serial.tools import list_ports


ROOT = Path(__file__).resolve().parents[1]
DEVICE_SOURCE = ROOT / "device"


def is_macropad(mount: Path) -> bool:
    try:
        return "Board ID:adafruit_macropad_rp2040" in (mount / "boot_out.txt").read_text(
            encoding="utf-8", errors="replace"
        )
    except OSError:
        return False


def discover() -> Path | None:
    user_media = Path("/run/media")
    if user_media.is_dir():
        for boot_out in user_media.glob("*/*/boot_out.txt"):
            if is_macropad(boot_out.parent):
                return boot_out.parent
    return None


def install_libraries(mount: Path) -> None:
    adjacent = Path(sys.executable).with_name("circup")
    circup = str(adjacent) if adjacent.exists() else shutil.which("circup")
    if not circup:
        raise RuntimeError("circup is not installed; install it in the project venv first")
    subprocess.run(
        [circup, "bundle-add", "Neradoc/Circuitpython_Keyboard_Layouts"],
        check=False,
    )
    subprocess.run(
        [
            circup,
            "--path",
            str(mount),
            "install",
            "adafruit_macropad",
            "keyboard_layout_win_de",
            "keycode_win_de",
        ],
        check=True,
    )
    bundled_lib = DEVICE_SOURCE / "lib"
    if bundled_lib.is_dir():
        destination = mount / "lib"
        destination.mkdir(exist_ok=True)
        for source in bundled_lib.iterdir():
            target = destination / source.name
            if source.is_dir():
                shutil.copytree(source, target, dirs_exist_ok=True)
            else:
                shutil.copy2(source, target)


def reset_device(mount: Path) -> bool:
    uid = ""
    try:
        for line in (mount / "boot_out.txt").read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("UID:"):
                uid = line.partition(":")[2].strip().upper()
    except OSError:
        return False
    port_name = None
    for port in list_ports.comports():
        if port.vid == 0x239A and port.pid == 0x8108:
            if not uid or (port.serial_number or "").upper() == uid:
                port_name = port.device
                break
    if not port_name:
        return False
    try:
        with serial.Serial(port_name, 115200, timeout=0.2, write_timeout=1.0) as connection:
            time.sleep(0.25)
            connection.write(b"\x03")
            connection.flush()
            time.sleep(0.15)
            connection.write(b"\x04")
            connection.flush()
        return True
    except (OSError, serial.SerialException):
        return False


def deploy(mount: Path, with_libraries: bool = True, reset: bool = True) -> None:
    if not is_macropad(mount):
        raise RuntimeError(f"{mount} is not an Adafruit MacroPad CIRCUITPY drive")
    if with_libraries:
        install_libraries(mount)
    for filename in ("macropad_core.py", "device_config.json"):
        shutil.copy2(DEVICE_SOURCE / filename, mount / filename)
    profiles = mount / "profiles"
    profiles.mkdir(exist_ok=True)
    for source in (DEVICE_SOURCE / "profiles").iterdir():
        if source.is_file():
            shutil.copy2(source, profiles / source.name)
    # code.py is deliberately last so a previously blank board cannot start halfway through deployment.
    shutil.copy2(DEVICE_SOURCE / "code.py", mount / "code.py")
    # USB mass-storage writes can still be queued when copy2 returns.  Flush the
    # host's FAT writes before asking CircuitPython to remount the filesystem.
    if hasattr(os, "sync"):
        os.sync()
    if reset and not reset_device(mount):
        print("warning: firmware copied, but automatic soft reset was unavailable", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy the MacroPad configurator firmware")
    parser.add_argument("--mount", type=Path, help="Path to the MacroPad CIRCUITPY drive")
    parser.add_argument("--skip-libraries", action="store_true", help="Do not run circup")
    parser.add_argument("--skip-reset", action="store_true", help="Do not soft-reset the board after copying")
    args = parser.parse_args()
    mount = args.mount or discover()
    if not mount:
        parser.error("no MacroPad CIRCUITPY drive found; pass --mount")
    try:
        deploy(mount, not args.skip_libraries, not args.skip_reset)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"deploy failed: {exc}", file=sys.stderr)
        return 1
    print(f"deployed MacroPad firmware to {mount}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
