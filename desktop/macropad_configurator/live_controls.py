"""Live desktop state and host actions for the MacroPad Live Controls profile."""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


GREEN = "#00FF66"
LIME = "#B8FF00"
YELLOW = "#FFD000"
ORANGE = "#FF7A00"
RED = "#FF2020"
BLUE = "#2080FF"
DIM = "#102040"
WHITE = "#FFFFFF"

SCREENS = (
    "Status",
    "Programs",
    "App Audio",
    "Windows",
    "Clipboard",
    "Focus",
    "System",
    "Jobs",
)


def _label(value: Any, fallback: str = "-") -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return (text or fallback)[:6].upper()


def _run(
    argv: list[str],
    *,
    input_text: str | None = None,
    timeout: float = 2.0,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            argv,
            input=input_text,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return subprocess.CompletedProcess(argv, 127, "", "")


def _stdout(argv: list[str], timeout: float = 2.0) -> str:
    completed = _run(argv, timeout=timeout)
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def _window_nodes(tree: Any) -> list[dict[str, Any]]:
    if not isinstance(tree, dict):
        return []
    result: list[dict[str, Any]] = []
    stack = [tree]
    while stack:
        node = stack.pop()
        properties = node.get("window_properties") or {}
        window_class = str(properties.get("class") or node.get("app_id") or "")
        if (
            (properties or node.get("app_id"))
            and node.get("id") is not None
            and window_class.casefold() not in {"i3bar", "polybar", "waybar"}
        ):
            result.append(
                {
                    "id": int(node["id"]),
                    "focused": bool(node.get("focused")),
                    "title": str(properties.get("title") or node.get("name") or ""),
                    "class": window_class,
                    "fullscreen": bool(node.get("fullscreen_mode")),
                    "floating": str(node.get("type", "")) == "floating_con"
                    or str(node.get("floating", "")).startswith("user"),
                }
            )
        stack.extend(reversed(node.get("floating_nodes") or []))
        stack.extend(reversed(node.get("nodes") or []))
    return result


def parse_sink_inputs(text: str) -> list[dict[str, Any]]:
    try:
        values = json.loads(text)
    except (TypeError, ValueError):
        return []
    if not isinstance(values, list):
        return []
    result = []
    for item in values:
        if not isinstance(item, dict) or item.get("index") is None:
            continue
        properties = item.get("properties") or {}
        volume = item.get("volume") or {}
        first_channel = next(iter(volume.values()), {}) if isinstance(volume, dict) else {}
        percent = str(first_channel.get("value_percent", "?")).strip()
        result.append(
            {
                "index": int(item["index"]),
                "name": str(
                    properties.get("application.name")
                    or properties.get("media.name")
                    or "Audio"
                ),
                "mute": bool(item.get("mute")),
                "volume": percent,
            }
        )
    return result


def is_job_process(command: str, arguments: str) -> bool:
    """Recognize foreground work without matching keywords in parent paths."""
    command = command.casefold()
    arguments = arguments.casefold()
    if command in {
        "wget",
        "curl",
        "aria2c",
        "ffmpeg",
        "make",
        "ninja",
        "cargo",
        "pytest",
        "pacman",
        "pamac",
        "yay",
    }:
        return True
    if command == "git":
        return bool(re.search(r"(^|\s)clone(\s|$)", arguments))
    if command == "blender":
        return any(flag in arguments.split() for flag in ("-a", "-b", "-f", "--background"))
    if command.startswith(("python", "pypy", "node")):
        try:
            executable_args = arguments.split()[1:4]
        except (AttributeError, IndexError):
            return False
        if executable_args and executable_args[0] in {"-c", "-e", "--eval"}:
            return False
        if len(executable_args) >= 2 and executable_args[0] == "-m":
            return executable_args[1] in {"pytest", "build"}
        script = next((value for value in executable_args if not value.startswith("-")), "")
        return bool(
            re.search(
                r"(render|download|build|comfyui)",
                Path(script).name,
                re.IGNORECASE,
            )
        )
    return False


@dataclass
class LiveLayout:
    screen: str
    title: str
    labels: list[str]
    colors: list[str]
    actions: list[dict[str, Any] | None]
    details: list[str]

    def __post_init__(self) -> None:
        for values, fallback in (
            (self.labels, ""),
            (self.colors, DIM),
            (self.actions, None),
            (self.details, ""),
        ):
            while len(values) < 12:
                values.append(fallback)
            del values[12:]

    def payload(self) -> dict[str, Any]:
        return {
            "cmd": "set_live_layout",
            "profile": "live-controls",
            "screen": self.screen,
            "title": self.title[:20],
            "labels": [_label(value, "") for value in self.labels],
            "colors": self.colors,
        }


class LiveControls:
    """Build live layouts and execute their bounded host-side actions."""

    def __init__(self) -> None:
        self.tree: dict[str, Any] = {}
        self.clipboard: list[str] = []
        self.last_clipboard = ""
        self.focus_until = 0.0
        self.focus_label = ""
        self.meeting_mode = False
        self.dnd_enabled = False
        self._meeting_previous_mic: bool | None = None
        self._meeting_previous_dnd: bool | None = None
        self._timer_announced = False
        self._cpu_sample: tuple[int, int] | None = None
        self._cache: dict[str, tuple[float, Any]] = {}

    def update_tree(self, tree: dict[str, Any]) -> None:
        self.tree = tree

    def _cached(self, key: str, seconds: float, factory):
        now = time.monotonic()
        cached = self._cache.get(key)
        if cached and now - cached[0] < seconds:
            return cached[1]
        value = factory()
        self._cache[key] = (now, value)
        return value

    def build(self, screen: str) -> LiveLayout:
        builders = {
            "Status": self._status,
            "Programs": self._programs,
            "App Audio": self._audio,
            "Windows": self._windows,
            "Clipboard": self._clipboard,
            "Focus": self._focus,
            "System": self._system,
            "Jobs": self._jobs,
        }
        return builders.get(screen, self._status)()

    def _mute_state(self, target: str) -> bool | None:
        output = _stdout(["pactl", f"get-{target}-mute", f"@DEFAULT_{target.upper()}@"])
        if not output:
            return None
        return output.casefold().endswith("yes")

    def _vpn(self) -> tuple[bool, str]:
        output = _stdout(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show", "--active"])
        for line in output.splitlines():
            name, _, connection_type = line.rpartition(":")
            if connection_type in ("vpn", "wireguard"):
                return True, name
        return False, ""

    def _caps_lock(self) -> bool | None:
        output = _stdout(["xset", "q"])
        match = re.search(r"Caps Lock:\s+(on|off)", output, re.IGNORECASE)
        return None if not match else match.group(1).casefold() == "on"

    def _recording(self) -> bool:
        output = _stdout(["pgrep", "-afi", "obs|ffmpeg|simplescreenrecorder"])
        return bool(output)

    def _update_count(self) -> int | None:
        def check() -> int | None:
            completed = _run(["checkupdates"], timeout=4.0)
            if completed.returncode not in (0, 2):
                return None
            return len([line for line in completed.stdout.splitlines() if line.strip()])

        return self._cached("updates", 300.0, check)

    def _status(self) -> LiveLayout:
        speaker = self._mute_state("sink")
        microphone = self._mute_state("source")
        vpn, vpn_name = self._vpn()
        caps = self._caps_lock()
        recording = self._recording()
        connected = "connected" in _stdout(["nmcli", "-t", "-f", "STATE", "general"]).casefold()
        updates = self._update_count()
        focus = self._remaining()
        labels = [
            "SPKOFF" if speaker else "SPKON",
            "MICOFF" if microphone else "MICON",
            "PLAY",
            "PREV",
            "NEXT",
            "VPNON" if vpn else "VPNOFF",
            focus or "FOCUS",
            "CAPSON" if caps else "CAPSOF",
            "REC" if recording else "NOREC",
            "NETON" if connected else "NETOFF",
            f"UP{updates}" if updates is not None else "UPD?",
            "REFR",
        ]
        colors = [
            RED if speaker else GREEN,
            RED if microphone else GREEN,
            BLUE,
            BLUE,
            BLUE,
            GREEN if vpn else DIM,
            YELLOW if focus else BLUE,
            YELLOW if caps else DIM,
            RED if recording else DIM,
            GREEN if connected else RED,
            ORANGE if updates else GREEN,
            BLUE,
        ]
        actions = [
            {"type": "command", "argv": ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"]},
            {"type": "command", "argv": ["pactl", "set-source-mute", "@DEFAULT_SOURCE@", "toggle"]},
            {"type": "device", "steps": [{"type": "consumer", "code": "PLAY_PAUSE"}]},
            {"type": "device", "steps": [{"type": "consumer", "code": "SCAN_PREVIOUS_TRACK"}]},
            {"type": "device", "steps": [{"type": "consumer", "code": "SCAN_NEXT_TRACK"}]},
            {"type": "vpn", "name": vpn_name},
            {"type": "timer", "minutes": 25},
            {"type": "device", "steps": [{"type": "hotkey", "keys": ["CAPS_LOCK"]}]},
            None,
            None,
            {"type": "terminal", "command": "checkupdates; printf '\\nPress Enter'; read"},
            {"type": "refresh"},
        ]
        details = [
            "Toggle speaker mute",
            "Toggle microphone mute",
            "Play or pause media",
            "Previous media track",
            "Next media track",
            f"VPN {vpn_name or 'disconnected'}",
            "Start a 25 minute focus timer",
            "Toggle Caps Lock",
            "Recording process detected" if recording else "No recorder detected",
            "Network connected" if connected else "Network disconnected",
            f"{updates} updates" if updates is not None else "Update count unavailable",
            "Refresh live state",
        ]
        return LiveLayout("Status", "Live Status", labels, colors, actions, details)

    def _programs(self) -> LiveLayout:
        windows = _window_nodes(self.tree)
        labels, colors, actions, details = [], [], [], []
        for window in windows[:12]:
            name = window["class"] or window["title"]
            labels.append(_label(name))
            colors.append(GREEN if window["focused"] else BLUE)
            actions.append(
                {
                    "type": "window",
                    "id": window["id"],
                    "long": {"type": "window_close", "id": window["id"]},
                }
            )
            details.append(f"Focus {name}; hold to close")
        return LiveLayout(
            "Programs",
            f"Programs {len(windows)}",
            labels,
            colors,
            actions,
            details,
        )

    def _sink_inputs(self) -> list[dict[str, Any]]:
        output = _stdout(["pactl", "-f", "json", "list", "sink-inputs"])
        return parse_sink_inputs(output)

    def _audio(self) -> LiveLayout:
        streams = self._sink_inputs()[:4]
        labels, colors, actions, details = [], [], [], []
        for stream in streams:
            index = stream["index"]
            name = stream["name"]
            labels.extend([_label(name), "VOL-", "VOL+"])
            colors.extend([RED if stream["mute"] else GREEN, BLUE, BLUE])
            actions.extend(
                [
                    {
                        "type": "command",
                        "argv": ["pactl", "set-sink-input-mute", str(index), "toggle"],
                    },
                    {
                        "type": "command",
                        "argv": ["pactl", "set-sink-input-volume", str(index), "-5%"],
                    },
                    {
                        "type": "command",
                        "argv": ["pactl", "set-sink-input-volume", str(index), "+5%"],
                    },
                ]
            )
            details.extend(
                [
                    f"{name}: {stream['volume']}; toggle mute",
                    f"{name}: volume down",
                    f"{name}: volume up",
                ]
            )
        return LiveLayout(
            "App Audio",
            f"App Audio {len(streams)}",
            labels,
            colors,
            actions,
            details,
        )

    def _windows(self) -> LiveLayout:
        focused = next((item for item in _window_nodes(self.tree) if item["focused"]), {})
        labels = [
            "WSPREV", "WSNEXT", "MVPRV", "MVNXT", "OUTL", "OUTR",
            "FULL", "FLOAT", "SPLITH", "SPLITV", "TABBED", "CLOSE",
        ]
        colors = [
            BLUE, BLUE, ORANGE, ORANGE, ORANGE, ORANGE,
            GREEN if focused.get("fullscreen") else BLUE,
            GREEN if focused.get("floating") else BLUE,
            YELLOW, YELLOW, YELLOW, RED,
        ]
        commands = [
            "workspace prev", "workspace next",
            "move container to workspace prev", "move container to workspace next",
            "move container to output left", "move container to output right",
            "fullscreen toggle", "floating toggle", "split h", "split v",
            "layout tabbed", "kill",
        ]
        details = [
            "Previous workspace", "Next workspace", "Move window to previous workspace",
            "Move window to next workspace", "Move window to left output",
            "Move window to right output", "Toggle fullscreen", "Toggle floating",
            "Horizontal split", "Vertical split", "Tabbed layout", "Close focused window",
        ]
        actions = [{"type": "i3", "command": value} for value in commands]
        return LiveLayout("Windows", "Window Tools", labels, colors, actions, details)

    def _sample_clipboard(self) -> None:
        value = _stdout(["xclip", "-selection", "clipboard", "-o"], timeout=0.5)
        if not value or value == self.last_clipboard or len(value) > 2000:
            return
        self.last_clipboard = value
        self.clipboard = [value] + [item for item in self.clipboard if item != value]
        del self.clipboard[10:]

    def _clipboard(self) -> LiveLayout:
        self._sample_clipboard()
        labels, colors, actions, details = [], [], [], []
        for index, text in enumerate(self.clipboard):
            preview = re.sub(r"\s+", " ", text).strip()
            labels.append(_label(preview, f"CLIP{index + 1}"))
            colors.append(GREEN if index == 0 else BLUE)
            actions.append(
                {
                    "type": "clipboard",
                    "text": text,
                    "long": {"type": "clipboard_remove", "index": index},
                }
            )
            details.append(f"Paste: {preview[:60]}; hold to remove")
        while len(labels) < 10:
            labels.append(f"CLIP{len(labels) + 1}")
            colors.append(DIM)
            actions.append(None)
            details.append("Empty clipboard slot")
        labels.extend(["CLEAR", "CAPTUR"])
        colors.extend([RED, ORANGE])
        actions.extend([{"type": "clipboard_clear"}, {"type": "clipboard_capture"}])
        details.extend(["Clear in-memory clipboard history", "Capture the current clipboard"])
        return LiveLayout(
            "Clipboard",
            f"Clipboard {len(self.clipboard)}",
            labels,
            colors,
            actions,
            details,
        )

    def _remaining(self) -> str:
        seconds = max(0, int(self.focus_until - time.monotonic()))
        if not seconds:
            if self.focus_until and not self._timer_announced:
                _run(["notify-send", "MacroPad", "Focus timer complete"])
                self._timer_announced = True
            return ""
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    def _focus(self) -> LiveLayout:
        remaining = self._remaining()
        current_dnd = self._dnd_state()
        if current_dnd is not None:
            self.dnd_enabled = current_dnd
        labels = [
            "25MIN", "50MIN", "5BREAK", "STOP", "MEET", "DND",
            "MICTOG", "SPKTOG", remaining or "TIMER", "ADD5", "SUB5", "LOCK",
        ]
        colors = [
            BLUE, BLUE, GREEN, RED,
            GREEN if self.meeting_mode else ORANGE,
            GREEN if self.dnd_enabled else DIM,
            BLUE, BLUE, YELLOW if remaining else DIM, BLUE, BLUE, RED,
        ]
        actions = [
            {"type": "timer", "minutes": 25, "label": "Focus"},
            {"type": "timer", "minutes": 50, "label": "Deep focus"},
            {"type": "timer", "minutes": 5, "label": "Break"},
            {"type": "timer_stop"},
            {"type": "meeting"},
            {"type": "dnd"},
            {"type": "command", "argv": ["pactl", "set-source-mute", "@DEFAULT_SOURCE@", "toggle"]},
            {"type": "command", "argv": ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"]},
            None,
            {"type": "timer_adjust", "minutes": 5},
            {"type": "timer_adjust", "minutes": -5},
            {"type": "command", "argv": ["loginctl", "lock-session"]},
        ]
        details = [
            "Start 25 minute focus", "Start 50 minute deep focus", "Start 5 minute break",
            "Stop timer", "Toggle meeting mode", "Toggle notification pause",
            "Toggle microphone mute", "Toggle speaker mute", remaining or "No timer running",
            "Add five minutes", "Subtract five minutes", "Lock this session",
        ]
        return LiveLayout(
            "Focus",
            f"Focus {remaining or 'idle'}",
            labels,
            colors,
            actions,
            details,
        )

    def _cpu_percent(self) -> int:
        try:
            values = [int(value) for value in Path("/proc/stat").read_text().splitlines()[0].split()[1:]]
        except (OSError, ValueError):
            return 0
        idle = values[3] + (values[4] if len(values) > 4 else 0)
        total = sum(values)
        previous = self._cpu_sample
        self._cpu_sample = (idle, total)
        if not previous or total == previous[1]:
            return 0
        return max(0, min(100, int(100 * (1 - (idle - previous[0]) / (total - previous[1])))))

    def _system(self) -> LiveLayout:
        cpu = self._cpu_percent()
        try:
            memory_text = Path("/proc/meminfo").read_text()
            total = int(re.search(r"MemTotal:\s+(\d+)", memory_text).group(1))
            available = int(re.search(r"MemAvailable:\s+(\d+)", memory_text).group(1))
            memory = int(100 * (total - available) / total)
        except (AttributeError, OSError, ValueError, ZeroDivisionError):
            memory = 0
        disk = shutil.disk_usage("/")
        disk_percent = int(100 * disk.used / disk.total)
        temperature_output = _stdout(["sensors"])
        temperatures = []
        for line in temperature_output.splitlines():
            match = re.search(r"^[^:]+:\s+\+([0-9.]+)°C", line)
            if match:
                temperatures.append(float(match.group(1)))
        temperature = int(max(temperatures)) if temperatures else 0
        gpu_output = _stdout(
            ["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"]
        )
        gpu_values = re.findall(r"\d+", gpu_output)
        gpu = int(gpu_values[0]) if gpu_values else 0
        gpu_temp = int(gpu_values[1]) if len(gpu_values) > 1 else 0
        uptime = int(float(Path("/proc/uptime").read_text().split()[0]) // 3600)
        ip = [
            value.split("/", 1)[0]
            for value in _stdout(
                ["nmcli", "-g", "IP4.ADDRESS", "device", "show"]
            ).splitlines()
            if value and not value.startswith("127.")
        ]
        ip_label = (
            "IP{}".format(ip[0].rsplit(".", 1)[-1])
            if ip and "." in ip[0]
            else _label(ip[0] if ip else "NOIP")
        )
        jobs = len(self._job_rows())
        labels = [
            f"CPU{cpu}", f"RAM{memory}", f"DSK{disk_percent}", f"TMP{temperature}",
            f"GPU{gpu}", f"GT{gpu_temp}", f"UP{uptime}H", _label(ip_label),
            f"JOB{jobs}", "TASKS", "HTOP", "REFR",
        ]
        colors = [
            RED if cpu > 85 else GREEN, RED if memory > 85 else GREEN,
            RED if disk_percent > 90 else GREEN, RED if temperature > 85 else GREEN,
            RED if gpu > 90 else GREEN, RED if gpu_temp > 85 else GREEN,
            BLUE, BLUE, ORANGE if jobs else DIM, BLUE, BLUE, BLUE,
        ]
        actions = [
            None, None, None, None, None, None, None, None, None,
            {"type": "launch", "argv": ["xfce4-taskmanager"]},
            {"type": "terminal", "command": "htop"},
            {"type": "refresh"},
        ]
        details = [
            f"CPU {cpu} percent", f"Memory {memory} percent", f"Disk {disk_percent} percent",
            f"Maximum sensor temperature {temperature} C", f"GPU {gpu} percent",
            f"GPU temperature {gpu_temp} C", f"Uptime {uptime} hours",
            f"IP address {ip[0] if ip else 'unavailable'}", f"{jobs} tracked jobs",
            "Open task manager", "Open htop", "Refresh system data",
        ]
        return LiveLayout("System", "System Monitor", labels, colors, actions, details)

    def _job_rows(self) -> list[dict[str, Any]]:
        output = _stdout(["ps", "-eo", "pid=,comm=,etimes=,pcpu=,args="])
        rows = []
        for line in output.splitlines():
            parts = line.strip().split(None, 4)
            if len(parts) < 5 or not is_job_process(parts[1], parts[4]):
                continue
            try:
                rows.append(
                    {
                        "pid": int(parts[0]),
                        "name": parts[1],
                        "seconds": int(parts[2]),
                        "cpu": float(parts[3]),
                        "args": parts[4],
                    }
                )
            except ValueError:
                continue
        return rows

    def _jobs(self) -> LiveLayout:
        jobs = self._job_rows()[:10]
        labels, colors, actions, details = [], [], [], []
        for job in jobs:
            labels.append(_label(job["name"]))
            colors.append(ORANGE if job["cpu"] < 80 else RED)
            actions.append(
                {
                    "type": "job_info",
                    "job": job,
                    "long": {
                        "type": "terminate",
                        "pid": job["pid"],
                        "args": job["args"],
                    },
                }
            )
            details.append(
                f"PID {job['pid']}; {job['seconds']} seconds; {job['cpu']} percent CPU; hold to stop"
            )
        while len(labels) < 10:
            labels.append("IDLE")
            colors.append(DIM)
            actions.append(None)
            details.append("No tracked job")
        labels.extend(["TASKS", "REFR"])
        colors.extend([BLUE, BLUE])
        actions.extend(
            [
                {"type": "launch", "argv": ["xfce4-taskmanager"]},
                {"type": "refresh"},
            ]
        )
        details.extend(["Open task manager", "Refresh job list"])
        return LiveLayout("Jobs", f"Jobs {len(jobs)}", labels, colors, actions, details)

    def handle(self, action: dict[str, Any] | None, long_press: bool = False) -> dict[str, Any] | None:
        if not action:
            return None
        if long_press and isinstance(action.get("long"), dict):
            action = action["long"]
        action_type = action.get("type")
        if action_type == "command":
            _run([str(value) for value in action.get("argv", [])])
        elif action_type == "device":
            return {"cmd": "test_steps", "name": "Live control", "steps": action.get("steps", [])}
        elif action_type == "i3":
            _run(["i3-msg", str(action.get("command", ""))])
        elif action_type == "window":
            _run(["i3-msg", f"[con_id={int(action['id'])}]", "focus"])
        elif action_type == "window_close":
            _run(["i3-msg", f"[con_id={int(action['id'])}]", "kill"])
        elif action_type == "launch":
            argv = [str(value) for value in action.get("argv", [])]
            if argv:
                subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif action_type == "terminal":
            command = str(action.get("command", ""))
            _run(["i3-msg", "exec", "--", "kitty", "-e", "sh", "-lc", command])
        elif action_type == "clipboard":
            text = str(action.get("text", ""))
            _run(["xclip", "-selection", "clipboard"], input_text=text)
            return {"cmd": "test_steps", "name": "Paste clipboard", "steps": [{"type": "hotkey", "keys": ["CONTROL", "V"]}]}
        elif action_type == "clipboard_remove":
            index = int(action.get("index", -1))
            if 0 <= index < len(self.clipboard):
                self.clipboard.pop(index)
        elif action_type == "clipboard_clear":
            self.clipboard = []
            self.last_clipboard = ""
        elif action_type == "clipboard_capture":
            self.last_clipboard = ""
            self._sample_clipboard()
        elif action_type == "timer":
            minutes = max(1, int(action.get("minutes", 25)))
            self.focus_until = time.monotonic() + minutes * 60
            self.focus_label = str(action.get("label", "Focus"))
            self._timer_announced = False
        elif action_type == "timer_stop":
            self.focus_until = 0.0
            self.focus_label = ""
        elif action_type == "timer_adjust":
            if self.focus_until:
                self.focus_until = max(
                    time.monotonic(),
                    self.focus_until + int(action.get("minutes", 0)) * 60,
                )
        elif action_type == "dnd":
            self._toggle_dnd()
        elif action_type == "meeting":
            if not self.meeting_mode:
                self._meeting_previous_mic = self._mute_state("source")
                self._meeting_previous_dnd = self._dnd_state()
                _run(["pactl", "set-source-mute", "@DEFAULT_SOURCE@", "1"])
                if self._meeting_previous_dnd is False:
                    _run(["dunstctl", "set-paused", "true"])
                self.meeting_mode = True
            else:
                if self._meeting_previous_mic is False:
                    _run(["pactl", "set-source-mute", "@DEFAULT_SOURCE@", "0"])
                if self._meeting_previous_dnd is False:
                    _run(["dunstctl", "set-paused", "false"])
                self.meeting_mode = False
                self._meeting_previous_mic = None
                self._meeting_previous_dnd = None
        elif action_type == "vpn":
            active_name = str(action.get("name", ""))
            if active_name:
                _run(["nmcli", "connection", "down", active_name], timeout=8.0)
            else:
                saved = _stdout(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"])
                vpn_name = next(
                    (
                        line.rpartition(":")[0]
                        for line in saved.splitlines()
                        if line.rpartition(":")[2] in ("vpn", "wireguard")
                    ),
                    "",
                )
                if vpn_name:
                    _run(["nmcli", "connection", "up", vpn_name], timeout=12.0)
        elif action_type == "job_info":
            job = action.get("job") or {}
            _run(["notify-send", "MacroPad job", str(job.get("args", ""))[:200]])
        elif action_type == "terminate":
            try:
                pid = int(action.get("pid", -1))
                expected = " ".join(str(action.get("args", "")).split())
                current = (
                    Path("/proc/{}/cmdline".format(pid))
                    .read_bytes()
                    .replace(b"\0", b" ")
                    .decode("utf-8", "replace")
                    .strip()
                )
                if expected and " ".join(current.split()) == expected:
                    os.kill(pid, signal.SIGTERM)
            except (OSError, ValueError):
                pass
        self._cache.clear()
        return None

    def _toggle_dnd(self) -> None:
        if not _command_exists("dunstctl"):
            _run(["notify-send", "MacroPad", "dunstctl is not installed; DND unavailable"])
            self.dnd_enabled = False
            return
        _run(["dunstctl", "set-paused", "toggle"])
        self.dnd_enabled = self._dnd_state() is True

    def _dnd_state(self) -> bool | None:
        if not _command_exists("dunstctl"):
            return None
        output = _stdout(["dunstctl", "is-paused"]).casefold()
        if output not in ("true", "false"):
            return None
        return output == "true"
