#!/usr/bin/env python3
"""Install and enable the MacroPad active-profile systemd user service."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "active-profile-map.json"
PYTHON = ROOT / ".venv" / "bin" / "python"
CONFIG_PATH = Path.home() / ".config" / "macropad-profile-switcher.json"
UNIT_PATH = Path.home() / ".config" / "systemd" / "user" / "macropad-profile-switcher.service"


def unit_text():
    return f"""[Unit]
Description=Automatically select MacroPad profiles from the focused i3 window
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart={PYTHON} -m macropad_configurator.profile_switcher --config %h/.config/macropad-profile-switcher.json
Restart=on-failure
RestartSec=2
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--replace-config",
        action="store_true",
        help="Replace the user's existing app-to-profile rules",
    )
    parser.add_argument("--no-start", action="store_true")
    args = parser.parse_args()
    if not PYTHON.exists():
        parser.error(f"project environment is missing: {PYTHON}")

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    UNIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if args.replace_config or not CONFIG_PATH.exists():
        shutil.copy2(DEFAULT_CONFIG, CONFIG_PATH)
    UNIT_PATH.write_text(unit_text(), encoding="utf-8")

    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    if not args.no_start:
        subprocess.run(
            ["systemctl", "--user", "enable", "--now", UNIT_PATH.name],
            check=True,
        )
    print(f"config: {CONFIG_PATH}")
    print(f"unit: {UNIT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
