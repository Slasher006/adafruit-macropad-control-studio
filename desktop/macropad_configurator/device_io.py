from __future__ import annotations

import getpass
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import serial
from serial.tools import list_ports

from .models import normalize_profile, normalize_project, save_json, validate_project


BOARD_ID = "adafruit_macropad_rp2040"
USB_VID = 0x239A
USB_PID = 0x8108
REQUIRED_DEVICE_FILES = (
    "code.py",
    "macropad_core.py",
    "lib/adafruit_macropad.mpy",
    "lib/adafruit_hid",
    "lib/adafruit_display_text",
    "lib/keyboard_layout_win_de.mpy",
    "lib/keycode_win_de.mpy",
)


class DeviceError(RuntimeError):
    pass


@dataclass(frozen=True)
class DeviceInfo:
    mount: Path
    uid: str = ""
    version: str = ""


def parse_boot_out(path: Path) -> DeviceInfo | None:
    boot_out = path / "boot_out.txt"
    try:
        text = boot_out.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if f"Board ID:{BOARD_ID}" not in text:
        return None
    uid = ""
    for line in text.splitlines():
        if line.startswith("UID:"):
            uid = line.partition(":")[2].strip()
    version = text.splitlines()[0] if text.splitlines() else ""
    return DeviceInfo(path, uid, version)


def candidate_mounts() -> list[Path]:
    candidates: list[Path] = []
    try:
        from PySide6.QtCore import QStorageInfo

        candidates.extend(Path(volume.rootPath()) for volume in QStorageInfo.mountedVolumes() if volume.isValid())
    except Exception:
        pass
    user = getpass.getuser()
    for base in (Path("/run/media") / user, Path("/media") / user, Path("/Volumes")):
        if base.is_dir():
            candidates.extend(path for path in base.iterdir() if path.is_dir())
    result: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path.resolve())
        if key not in seen:
            seen.add(key)
            result.append(path)
    return result


def discover_devices() -> list[DeviceInfo]:
    devices = [info for path in candidate_mounts() if (info := parse_boot_out(path))]
    return sorted(devices, key=lambda item: str(item.mount))


def read_device_project(device: DeviceInfo) -> dict[str, Any]:
    root = device.mount
    try:
        config = json.loads((root / "device_config.json").read_text(encoding="utf-8"))
        index = json.loads((root / "profiles" / "index.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DeviceError(f"Cannot read device configuration: {exc}") from exc
    profiles: list[dict[str, Any]] = []
    for entry in index.get("profiles", []):
        profile_id = str(entry.get("id", ""))
        filename = str(entry.get("file", f"{profile_id}.json"))
        try:
            raw = json.loads((root / "profiles" / filename).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise DeviceError(f"Cannot read profile {profile_id}: {exc}") from exc
        profiles.append(normalize_profile(raw, profile_id))
    return normalize_project(
        {
            "schema_version": 1,
            "keyboard_layout": config.get("keyboard_layout", "us"),
            "profiles": profiles,
        }
    )


def project_fingerprint(project: dict[str, Any]) -> str:
    normalized = validate_project(project)
    return json.dumps(normalized, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def compare_projects(local: dict[str, Any], remote: dict[str, Any]) -> list[str]:
    local = validate_project(local)
    remote = validate_project(remote)
    changes: list[str] = []
    if local["keyboard_layout"] != remote["keyboard_layout"]:
        changes.append(f"Keyboard layout: {remote['keyboard_layout'].upper()} → {local['keyboard_layout'].upper()}")
    local_ids = [profile["id"] for profile in local["profiles"]]
    remote_ids = [profile["id"] for profile in remote["profiles"]]
    if local_ids != remote_ids:
        changes.append("Profile order or membership changed")
    remote_by_id = {profile["id"]: profile for profile in remote["profiles"]}
    for profile in local["profiles"]:
        old = remote_by_id.get(profile["id"])
        if old is None:
            changes.append(f"Add profile: {profile['name']}")
            continue
        if profile["name"] != old["name"] or profile.get("icon", "") != old.get("icon", ""):
            changes.append(f"Rename/update profile: {old['name']} → {profile['name']}")
        if profile["brightness"] != old["brightness"]:
            changes.append(f"{profile['name']}: brightness {old['brightness']}% → {profile['brightness']}%")
        changed_controls = 0
        for new_control, old_control in zip(
            profile["keys"] + [profile["encoder_press"]],
            old["keys"] + [old["encoder_press"]],
        ):
            if new_control != old_control:
                changed_controls += 1
        if changed_controls:
            changes.append(f"{profile['name']}: {changed_controls} control(s) changed")
    for profile in remote["profiles"]:
        if profile["id"] not in local_ids:
            changes.append(f"Remove profile: {profile['name']}")
    return changes


def backup_device(device: DeviceInfo, backup_root: Path) -> Path:
    project = read_device_project(device)
    folder = backup_root / (device.uid or "unknown-device")
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    path = folder / f"{timestamp}-{time.time_ns() % 1_000_000_000:09d}.json"
    save_json(path, project)
    return path


def list_device_backups(backup_root: Path, uid: str) -> list[Path]:
    return sorted((backup_root / (uid or "unknown-device")).glob("*.json"), reverse=True)


def export_library_archive(path: Path, project: dict[str, Any], palette: list[str] | None = None) -> None:
    project = validate_project(project)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("library.json", json.dumps(project, indent=2, ensure_ascii=False) + "\n")
        archive.writestr(
            "manifest.json",
            json.dumps({"format": "macropad-library", "version": 1, "palette": palette or []}, indent=2) + "\n",
        )


def import_library_archive(path: Path) -> tuple[dict[str, Any], list[str]]:
    try:
        with zipfile.ZipFile(path, "r") as archive:
            project = normalize_project(json.loads(archive.read("library.json").decode("utf-8")))
            try:
                manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
            except (KeyError, ValueError):
                manifest = {}
    except (KeyError, zipfile.BadZipFile) as exc:
        raise DeviceError(f"Invalid MacroPad library archive: {exc}") from exc
    palette = [str(color) for color in manifest.get("palette", []) if isinstance(color, str)]
    return validate_project(project), palette


def device_health(device: DeviceInfo) -> dict[str, Any]:
    missing = [relative for relative in REQUIRED_DEVICE_FILES if not (device.mount / relative).exists()]
    status: dict[str, Any] = {"missing": missing, "healthy": not missing}
    try:
        status.update(send_command({"cmd": "status"}, device.uid, timeout=2.0))
    except DeviceError as exc:
        status["serial_error"] = str(exc)
        status["healthy"] = False
    return status


def repair_firmware(device: DeviceInfo, device_source: Path) -> None:
    adjacent = Path(sys.executable).with_name("circup")
    circup = str(adjacent) if adjacent.exists() else shutil.which("circup")
    if not circup:
        raise DeviceError("circup is not installed in the application environment")
    try:
        subprocess.run(
            [circup, "bundle-add", "Neradoc/Circuitpython_Keyboard_Layouts"],
            check=False,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            [circup, "--path", str(device.mount), "install", "adafruit_macropad", "keyboard_layout_win_de", "keycode_win_de"],
            check=True,
        )
        for filename in ("macropad_core.py", "code.py"):
            shutil.copy2(device_source / filename, device.mount / filename)
        if not (device.mount / "device_config.json").exists():
            shutil.copy2(device_source / "device_config.json", device.mount / "device_config.json")
        if not (device.mount / "profiles" / "index.json").exists():
            shutil.copytree(device_source / "profiles", device.mount / "profiles", dirs_exist_ok=True)
        if hasattr(os, "sync"):
            os.sync()
        try:
            send_command({"cmd": "reload_config"}, device.uid, timeout=2.0)
        except DeviceError:
            pass
    except (OSError, subprocess.CalledProcessError) as exc:
        raise DeviceError(f"Firmware repair failed: {exc}") from exc


def _write_json_temp(destination: Path, data: Any) -> Path:
    temporary = destination.with_name(destination.name + ".new")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    return temporary


def sync_project(device: DeviceInfo, project: dict[str, Any]) -> str:
    project = validate_project(project)
    root = device.mount
    if parse_boot_out(root) is None:
        raise DeviceError("The selected CIRCUITPY mount is no longer the MacroPad")
    profiles_dir = root / "profiles"
    profiles_dir.mkdir(exist_ok=True)
    revision = str(time.time_ns())
    wanted: set[str] = set()
    index_entries: list[dict[str, str]] = []
    try:
        for profile in project["profiles"]:
            filename = f"{profile['id']}.{revision}.json"
            wanted.add(filename)
            index_entries.append({"id": profile["id"], "name": profile["name"], "file": filename})
            destination = profiles_dir / filename
            temporary = _write_json_temp(destination, profile)
            os.replace(temporary, destination)

        config = {
            "schema_version": 1,
            "keyboard_layout": project["keyboard_layout"],
            "revision": revision,
        }
        config_path = root / "device_config.json"
        os.replace(_write_json_temp(config_path, config), config_path)

        index = {
            "schema_version": 1,
            "profiles": index_entries,
        }
        index_path = profiles_dir / "index.json"
        os.replace(_write_json_temp(index_path, index), index_path)

        revision_path = profiles_dir / "revision.txt"
        revision_temp = revision_path.with_name("revision.txt.new")
        with revision_temp.open("w", encoding="ascii", newline="\n") as handle:
            handle.write(revision + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(revision_temp, revision_path)

        for existing in profiles_dir.glob("*.json"):
            if existing.name != "index.json" and existing.name not in wanted:
                existing.unlink()
        # Renames and FAT directory entries must reach the device before firmware resets it.
        # Per-file fsync is not sufficient for a USB mass-storage filesystem.
        if hasattr(os, "sync"):
            os.sync()
    except OSError as exc:
        raise DeviceError(f"Device sync was interrupted: {exc}") from exc
    return revision


def install_project_files(device: DeviceInfo, device_source: Path) -> None:
    root = device.mount
    for filename in ("code.py", "macropad_core.py", "device_config.json"):
        shutil.copy2(device_source / filename, root / filename)
    destination_profiles = root / "profiles"
    destination_profiles.mkdir(exist_ok=True)
    for source in (device_source / "profiles").glob("*"):
        if source.is_file():
            shutil.copy2(source, destination_profiles / source.name)


def find_serial_port(uid: str = "") -> str | None:
    matches = []
    for port in list_ports.comports():
        if port.vid == USB_VID and port.pid == USB_PID:
            if uid and (port.serial_number or "").upper() == uid.upper():
                return port.device
            matches.append(port.device)
    return matches[0] if matches else None


def parse_serial_json(line: str) -> dict[str, Any] | None:
    start = line.find("{")
    if start < 0:
        return None
    try:
        value = json.loads(line[start:])
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def send_command(command: dict[str, Any], uid: str = "", timeout: float = 1.5) -> dict[str, Any]:
    port = find_serial_port(uid)
    if not port:
        raise DeviceError("MacroPad serial port not found")
    name = str(command.get("cmd", ""))
    deadline = time.monotonic() + timeout
    try:
        with serial.Serial(port, 115200, timeout=0.1, write_timeout=1.0) as connection:
            connection.reset_input_buffer()
            connection.write((json.dumps(command) + "\n").encode("utf-8"))
            connection.flush()
            while time.monotonic() < deadline:
                line = connection.readline().decode("utf-8", "replace").strip()
                response = parse_serial_json(line)
                if response is None:
                    continue
                if response.get("event") == "response" and response.get("cmd") == name:
                    if not response.get("ok"):
                        raise DeviceError(str(response.get("error", "device command failed")))
                    return response
    except (OSError, serial.SerialException) as exc:
        raise DeviceError(f"Serial command failed: {exc}") from exc
    raise DeviceError(f"No response to {name!r} from MacroPad")


def preview_lighting(device: DeviceInfo, profile: dict[str, Any]) -> dict[str, Any]:
    return send_command(
        {
            "cmd": "preview_lighting",
            "brightness": profile["brightness"],
            "colors": [
                control["idle_color"] if control.get("lighting_enabled", True) else "#000000"
                for control in profile["keys"]
            ],
        },
        device.uid,
    )


def clear_preview(device: DeviceInfo) -> dict[str, Any]:
    return send_command({"cmd": "clear_preview"}, device.uid)


def save_local_project(path: Path, project: dict[str, Any]) -> None:
    save_json(path, validate_project(project))
