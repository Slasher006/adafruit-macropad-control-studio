"""Automatically select MacroPad profiles from the focused i3/Sway window."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import serial
from serial.tools import list_ports


USB_VID = 0x239A
USB_PID = 0x8108


@dataclass(frozen=True)
class FocusedWindow:
    title: str = ""
    window_class: str = ""
    instance: str = ""
    app_id: str = ""

    @property
    def signature(self) -> tuple[str, str, str, str]:
        return (self.title, self.window_class, self.instance, self.app_id)


@dataclass(frozen=True)
class ProfileTarget:
    profile: str
    subprofile: str | None = None


def find_focused_window(tree: Any) -> FocusedWindow | None:
    if not isinstance(tree, dict):
        return None
    stack = [tree]
    while stack:
        node = stack.pop()
        if node.get("focused"):
            properties = node.get("window_properties") or {}
            return FocusedWindow(
                title=str(properties.get("title") or node.get("name") or ""),
                window_class=str(properties.get("class") or ""),
                instance=str(properties.get("instance") or ""),
                app_id=str(node.get("app_id") or ""),
            )
        stack.extend(reversed(node.get("floating_nodes") or []))
        stack.extend(reversed(node.get("nodes") or []))
    return None


def find_open_windows(tree: Any) -> list[FocusedWindow]:
    if not isinstance(tree, dict):
        return []
    windows: list[FocusedWindow] = []
    stack = [tree]
    while stack:
        node = stack.pop()
        properties = node.get("window_properties") or {}
        if properties or node.get("app_id"):
            windows.append(
                FocusedWindow(
                    title=str(properties.get("title") or node.get("name") or ""),
                    window_class=str(properties.get("class") or ""),
                    instance=str(properties.get("instance") or ""),
                    app_id=str(node.get("app_id") or ""),
                )
            )
        stack.extend(reversed(node.get("floating_nodes") or []))
        stack.extend(reversed(node.get("nodes") or []))
    return windows


def _values(rule: dict[str, Any], key: str) -> list[str]:
    values = rule.get(key, [])
    if isinstance(values, str):
        values = [values]
    return [str(value).casefold() for value in values if str(value).strip()]


def rule_matches(rule: dict[str, Any], window: FocusedWindow) -> bool:
    fields = {
        "class_contains": window.window_class.casefold(),
        "instance_contains": window.instance.casefold(),
        "title_contains": window.title.casefold(),
        "app_id_contains": window.app_id.casefold(),
    }
    used = False
    for selector, actual in fields.items():
        expected = _values(rule, selector)
        if not expected:
            continue
        used = True
        if not any(value in actual for value in expected):
            return False
    return used


def choose_profile(config: dict[str, Any], window: FocusedWindow | None) -> str | None:
    target = choose_target(config, window)
    return target.profile if target else None


def choose_rule_target(
    config: dict[str, Any],
    window: FocusedWindow,
) -> ProfileTarget | None:
    for rule in config.get("rules", []):
        if isinstance(rule, dict) and rule_matches(rule, window):
            profile = str(rule.get("profile", "")).strip()
            if profile:
                subprofile = str(rule.get("subprofile", "")).strip() or None
                return ProfileTarget(profile, subprofile)
    return None


def choose_target(
    config: dict[str, Any],
    window: FocusedWindow | None,
) -> ProfileTarget | None:
    if window is None:
        value = config.get("desktop_profile")
        return ProfileTarget(str(value)) if value else None
    target = choose_rule_target(config, window)
    if target:
        return target
    value = config.get("default_profile")
    if not value:
        return None
    subprofile = str(config.get("default_subprofile", "")).strip() or None
    return ProfileTarget(str(value), subprofile)


def choose_visible_profiles(
    config: dict[str, Any],
    windows: list[FocusedWindow],
    selected_profile: str | None = None,
) -> tuple[str, ...]:
    if config.get("filter_open_apps", False) is not True:
        return ()
    result: list[str] = []
    pinned = config.get("pinned_profiles", [])
    if not isinstance(pinned, list):
        pinned = []
    desktop_profile = str(config.get("desktop_profile", "")).strip()
    for value in [desktop_profile, *pinned, selected_profile]:
        if value is None:
            continue
        profile = str(value).strip()
        if profile and profile not in result:
            result.append(profile)
    for rule in config.get("rules", []):
        if not isinstance(rule, dict):
            continue
        profile = str(rule.get("profile", "")).strip()
        if (
            profile
            and profile not in result
            and any(rule_matches(rule, window) for window in windows)
        ):
            result.append(profile)
    return tuple(result)


def _i3_socket_candidates() -> list[Path]:
    """Return live-looking i3/Sway IPC sockets, newest first."""
    candidates: list[Path] = []
    seen: set[str] = set()

    for variable in ("I3SOCK", "SWAYSOCK"):
        value = os.environ.get(variable, "").strip()
        if value and value not in seen:
            candidates.append(Path(value))
            seen.add(value)

    runtime_value = os.environ.get("XDG_RUNTIME_DIR", "").strip()
    if runtime_value:
        runtime = Path(runtime_value)
        discovered = list((runtime / "i3").glob("ipc-socket.*"))
        discovered.extend(runtime.glob("sway-ipc.*.sock"))

        def modified_at(path: Path) -> float:
            try:
                return path.stat().st_mtime
            except OSError:
                return 0.0

        for path in sorted(discovered, key=modified_at, reverse=True):
            value = str(path)
            if value not in seen:
                candidates.append(path)
                seen.add(value)
    return candidates


def query_i3_tree() -> dict[str, Any]:
    commands: list[list[str]] = []
    if any(os.environ.get(name) for name in ("DISPLAY", "I3SOCK", "SWAYSOCK")):
        commands.append(["i3-msg", "-t", "get_tree"])
    commands.extend(
        ["i3-msg", "-s", str(socket), "-t", "get_tree"]
        for socket in _i3_socket_candidates()
    )
    if not commands:
        raise RuntimeError("i3 IPC socket is not available yet")

    failures: list[str] = []
    for command in commands:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=3.0,
        )
        if completed.returncode:
            detail = completed.stderr.strip() or f"exit status {completed.returncode}"
            failures.append(detail)
            continue
        try:
            value = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            failures.append(f"invalid JSON: {exc}")
            continue
        if isinstance(value, dict):
            return value
        failures.append("invalid tree")

    detail = failures[-1] if failures else "no usable IPC socket"
    raise RuntimeError(f"cannot query i3 tree: {detail}")


def parse_serial_json(line: str) -> dict[str, Any] | None:
    start = line.find("{")
    if start < 0:
        return None
    try:
        value = json.loads(line[start:])
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def send_command_to_port(
    port_name: str,
    command: dict[str, Any],
    expected_command: str,
    timeout: float = 2.0,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    with serial.Serial(port_name, 115200, timeout=0.1, write_timeout=1.0) as connection:
        connection.reset_input_buffer()
        connection.write((json.dumps(command) + "\n").encode("utf-8"))
        connection.flush()
        while time.monotonic() < deadline:
            response = parse_serial_json(connection.readline().decode("utf-8", "replace").strip())
            if response is None:
                continue
            if response.get("event") == "response" and response.get("cmd") == expected_command:
                if not response.get("ok"):
                    raise RuntimeError(str(response.get("error", "device command failed")))
                return response
    raise RuntimeError(f"device did not respond to {expected_command}")


def send_to_port(
    port_name: str,
    profile_id: str,
    subprofile: str | None = None,
    timeout: float = 2.0,
) -> dict[str, Any]:
    command = {"cmd": "set_profile", "id": profile_id, "automatic": True}
    if subprofile:
        command["subprofile"] = subprofile
    return send_command_to_port(port_name, command, "set_profile", timeout)


def send_visible_profiles_to_port(
    port_name: str,
    profile_ids: tuple[str, ...],
    timeout: float = 2.0,
) -> dict[str, Any]:
    return send_command_to_port(
        port_name,
        {"cmd": "set_visible_profiles", "ids": list(profile_ids)},
        "set_visible_profiles",
        timeout,
    )


def macropad_ports():
    return [
        port
        for port in list_ports.comports()
        if port.vid == USB_VID and port.pid == USB_PID
    ]


class ActiveProfileService:
    def __init__(self, config: dict[str, Any], dry_run: bool = False):
        self.config = config
        self.dry_run = dry_run
        self.sent_profiles: dict[str, ProfileTarget] = {}
        self.sent_visible_profiles: dict[str, tuple[str, ...]] = {}
        self.retry_at: dict[str, float] = {}
        self.disabled_devices: set[str] = set()
        self.options_devices: set[str] = set()
        self.last_window_signature: tuple[str, str, str, str] | None = None
        self.last_desired: ProfileTarget | None = None
        self.last_visible_profiles: tuple[str, ...] | None = None

    def tick(self) -> str | None:
        tree = query_i3_tree()
        window = find_focused_window(tree)
        desired = choose_target(self.config, window)
        visible_profiles = choose_visible_profiles(
            self.config,
            find_open_windows(tree),
            desired.profile if desired else None,
        )
        signature = window.signature if window else ("", "", "", "")
        previous_identity = (
            self.last_window_signature[1:] if self.last_window_signature is not None else None
        )
        if previous_identity != signature[1:] or desired != self.last_desired:
            label = window.window_class or window.app_id or "desktop"
            title = window.title if window else ""
            print(
                f"focus class={label!r} title={title!r} "
                f"profile={desired.profile!r} subprofile={desired.subprofile!r}",
                flush=True,
            )
        self.last_window_signature = signature
        self.last_desired = desired
        if visible_profiles != self.last_visible_profiles:
            label = ", ".join(visible_profiles) if visible_profiles else "all"
            print(f"visible profiles: {label}", flush=True)
        self.last_visible_profiles = visible_profiles
        if not desired:
            return None
        if self.dry_run:
            return desired.profile

        now = time.monotonic()
        live_devices: set[str] = set()
        for port in macropad_ports():
            device_id = str(port.serial_number or port.device)
            live_devices.add(device_id)
            visible_changed = (
                self.sent_visible_profiles.get(device_id) != visible_profiles
            )
            target_changed = self.sent_profiles.get(device_id) != desired
            if not visible_changed and not target_changed:
                continue
            if now < self.retry_at.get(device_id, 0.0):
                continue
            if visible_changed:
                try:
                    response = send_visible_profiles_to_port(
                        port.device,
                        visible_profiles,
                    )
                except (OSError, serial.SerialException, RuntimeError) as exc:
                    self.retry_at[device_id] = now + 2.0
                    print(f"device {device_id}: {exc}; retrying", flush=True)
                    continue
                self.sent_visible_profiles[device_id] = visible_profiles
                print(
                    f"device {device_id}: visible_profiles="
                    f"{response.get('profile_count', len(visible_profiles))}",
                    flush=True,
                )
            if not target_changed:
                self.retry_at.pop(device_id, None)
                continue
            try:
                response = send_to_port(
                    port.device,
                    desired.profile,
                    desired.subprofile,
                )
            except (OSError, serial.SerialException, RuntimeError) as exc:
                self.retry_at[device_id] = now + 2.0
                print(f"device {device_id}: {exc}; retrying", flush=True)
                continue
            if response.get("ignored"):
                self.retry_at[device_id] = now + 2.0
                if response.get("automatic_switching", True) is not False:
                    if device_id not in self.options_devices:
                        print(
                            f"device {device_id}: Options screen is open; waiting",
                            flush=True,
                        )
                    self.options_devices.add(device_id)
                    continue
                if device_id not in self.disabled_devices:
                    print(
                        f"device {device_id}: role=MANUAL; keeping encoder-selected profile",
                        flush=True,
                    )
                self.disabled_devices.add(device_id)
                self.sent_profiles.pop(device_id, None)
                continue
            if device_id in self.disabled_devices:
                role = str(response.get("deck_role", "app")).upper()
                print(
                    f"device {device_id}: role={role}; following focused application",
                    flush=True,
                )
            self.disabled_devices.discard(device_id)
            self.options_devices.discard(device_id)
            self.retry_at.pop(device_id, None)
            self.sent_profiles[device_id] = desired
            print(
                f"device {device_id}: profile={response.get('profile')} "
                f"subprofile={response.get('subprofile')} "
                f"role={str(response.get('deck_role', 'app')).upper()}",
                flush=True,
            )

        known_devices = set(self.sent_profiles) | set(self.sent_visible_profiles)
        for device_id in known_devices - live_devices:
            self.sent_profiles.pop(device_id, None)
            self.sent_visible_profiles.pop(device_id, None)
            self.retry_at.pop(device_id, None)
            self.disabled_devices.discard(device_id)
            self.options_devices.discard(device_id)
        return desired.profile


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict) or not isinstance(value.get("rules", []), list):
        raise ValueError("profile switcher config must contain a rules list")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    service = ActiveProfileService(config, args.dry_run)
    poll_interval = max(0.2, float(config.get("poll_interval", 0.5)))
    while True:
        try:
            service.tick()
        except (
            OSError,
            ValueError,
            json.JSONDecodeError,
            subprocess.SubprocessError,
            RuntimeError,
        ) as exc:
            print(f"focus detection failed: {exc}", flush=True)
        if args.once:
            return 0
        time.sleep(poll_interval)


if __name__ == "__main__":
    raise SystemExit(main())
