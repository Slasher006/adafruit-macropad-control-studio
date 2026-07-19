import json
import subprocess

import macropad_configurator.live_controls as live_controls
import macropad_configurator.profile_switcher as profile_switcher
from macropad_configurator.live_controls import (
    LiveControls,
    SCREENS,
    is_job_process,
    parse_sink_inputs,
)


def test_parse_sink_inputs_extracts_application_volume_and_mute():
    payload = json.dumps(
        [
            {
                "index": 42,
                "mute": True,
                "properties": {"application.name": "Firefox"},
                "volume": {"front-left": {"value_percent": "37%"}},
            }
        ]
    )
    assert parse_sink_inputs(payload) == [
        {"index": 42, "name": "Firefox", "mute": True, "volume": "37%"}
    ]
    assert parse_sink_inputs("not json") == []


def test_job_detection_uses_the_executable_not_parent_path_keywords():
    assert is_job_process("ffmpeg", "ffmpeg -i input.mp4 output.webm")
    assert is_job_process("git", "git clone https://example.invalid/repo")
    assert is_job_process("python3", "python3 /work/download_models.py")
    assert is_job_process("python", "python -m pytest -q")
    assert not is_job_process(
        "node",
        "node /home/user/.cache/yay/project/node_modules/.bin/mcp-server",
    )
    assert not is_job_process("python", "python -c manager.build('Jobs')")


def test_every_live_screen_builds_a_complete_device_payload(monkeypatch):
    def stdout(argv, timeout=2.0):
        command = " ".join(argv)
        if "get-sink-mute" in command or "get-source-mute" in command:
            return "Mute: no"
        if "nmcli" in command and "general" in command:
            return "connected"
        if "xset q" in command:
            return "Caps Lock: off"
        if "pactl -f json" in command:
            return "[]"
        if "IP4.ADDRESS" in command:
            return "192.0.2.10/24"
        if "nvidia-smi" in command:
            return "12, 45"
        if "sensors" in command:
            return "CPU: +51.0°C"
        if "xclip" in command:
            return "copied text"
        if "ps -eo" in command:
            return ""
        return ""

    monkeypatch.setattr(live_controls, "_stdout", stdout)
    monkeypatch.setattr(
        live_controls,
        "_run",
        lambda argv, **kwargs: subprocess.CompletedProcess(argv, 0, "", ""),
    )
    manager = LiveControls()
    manager.update_tree(
        {
            "nodes": [
                {
                    "id": 7,
                    "focused": True,
                    "name": "Editor",
                    "window_properties": {"class": "Code", "title": "Editor"},
                }
            ]
        }
    )

    for screen in SCREENS:
        layout = manager.build(screen)
        assert len(layout.labels) == 12
        assert len(layout.colors) == 12
        assert len(layout.actions) == 12
        payload = layout.payload()
        assert payload["cmd"] == "set_live_layout"
        assert payload["screen"] == screen
        assert len(payload["labels"]) == 12
        assert all(len(label) <= 6 for label in payload["labels"])

    programs = manager.build("Programs")
    assert programs.labels[0] == "CODE"
    assert programs.actions[0]["id"] == 7
    assert programs.actions[0]["long"]["type"] == "window_close"


def test_clipboard_history_is_memory_only_and_returns_device_paste(monkeypatch):
    clipboard = {"value": "first item"}
    monkeypatch.setattr(
        live_controls,
        "_stdout",
        lambda argv, timeout=2.0: clipboard["value"] if argv[0] == "xclip" else "",
    )
    calls = []

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(live_controls, "_run", run)
    manager = LiveControls()
    layout = manager.build("Clipboard")
    assert manager.clipboard == ["first item"]
    result = manager.handle(layout.actions[0])
    assert result["cmd"] == "test_steps"
    assert result["steps"] == [{"type": "hotkey", "keys": ["CONTROL", "V"]}]
    assert calls[-1][1]["input_text"] == "first item"

    manager.handle(layout.actions[0], long_press=True)
    assert manager.clipboard == []


def test_focus_timer_updates_dynamic_label(monkeypatch):
    now = {"value": 100.0}
    monkeypatch.setattr(live_controls.time, "monotonic", lambda: now["value"])
    monkeypatch.setattr(
        live_controls,
        "_run",
        lambda argv, **kwargs: subprocess.CompletedProcess(argv, 0, "", ""),
    )
    manager = LiveControls()
    manager.handle({"type": "timer", "minutes": 25})
    assert manager.build("Focus").labels[8] == "25:00"
    now["value"] += 60
    assert manager.build("Focus").labels[8] == "24:00"
    manager.handle({"type": "timer_adjust", "minutes": -5})
    assert manager.build("Focus").labels[8] == "19:00"
    manager.handle({"type": "timer_stop"})
    assert manager.build("Focus").labels[8] == "TIMER"


def test_i3_action_runs_exactly_once(monkeypatch):
    calls = []
    monkeypatch.setattr(
        live_controls,
        "_run",
        lambda argv, **kwargs: calls.append(argv)
        or subprocess.CompletedProcess(argv, 0, "", ""),
    )
    LiveControls().handle({"type": "i3", "command": "workspace next"})
    assert calls == [["i3-msg", "workspace next"]]


def test_meeting_mode_restores_previous_mic_and_dnd_state(monkeypatch):
    calls = []
    states = {"mic": False, "dnd": False}

    def stdout(argv, timeout=2.0):
        if argv[:2] == ["pactl", "get-source-mute"]:
            return "Mute: yes" if states["mic"] else "Mute: no"
        if argv == ["dunstctl", "is-paused"]:
            return "true" if states["dnd"] else "false"
        return ""

    def run(argv, **kwargs):
        calls.append(argv)
        if argv[:3] == ["pactl", "set-source-mute", "@DEFAULT_SOURCE@"]:
            states["mic"] = argv[3] == "1"
        if argv[:2] == ["dunstctl", "set-paused"]:
            states["dnd"] = argv[2] == "true"
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(live_controls, "_stdout", stdout)
    monkeypatch.setattr(live_controls, "_run", run)
    monkeypatch.setattr(live_controls, "_command_exists", lambda name: name == "dunstctl")

    manager = LiveControls()
    manager.handle({"type": "meeting"})
    assert states == {"mic": True, "dnd": True}
    manager.handle({"type": "meeting"})
    assert states == {"mic": False, "dnd": False}
    assert ["pactl", "set-source-mute", "@DEFAULT_SOURCE@", "0"] in calls
    assert ["dunstctl", "set-paused", "false"] in calls


def test_job_stop_verifies_process_identity_before_signalling(monkeypatch):
    signals = []
    monkeypatch.setattr(
        live_controls.Path,
        "read_bytes",
        lambda path: b"ffmpeg\0-i\0input.mp4\0",
    )
    monkeypatch.setattr(
        live_controls.os,
        "kill",
        lambda pid, value: signals.append((pid, value)),
    )
    manager = LiveControls()
    manager.handle(
        {
            "type": "terminate",
            "pid": 42,
            "args": "ffmpeg -i input.mp4",
        }
    )
    manager.handle(
        {
            "type": "terminate",
            "pid": 42,
            "args": "different process",
        }
    )
    assert signals == [(42, live_controls.signal.SIGTERM)]


class FakeSerial:
    def __init__(self):
        self.lines = []
        self.writes = []
        self.closed = False

    def reset_input_buffer(self):
        self.lines = []

    def write(self, value):
        self.writes.append(json.loads(value.decode("utf-8")))
        command = self.writes[-1]["cmd"]
        self.lines.extend(
            [
                b'{"event":"host_key","key":2,"subprofile":"Status","duration_ms":40}\n',
                (json.dumps({"event": "response", "cmd": command, "ok": True}) + "\n").encode(),
            ]
        )

    def flush(self):
        pass

    def readline(self):
        return self.lines.pop(0) if self.lines else b""

    def close(self):
        self.closed = True


def test_persistent_device_session_preserves_events_seen_during_command(monkeypatch):
    fake = FakeSerial()
    monkeypatch.setattr(profile_switcher.serial, "Serial", lambda *args, **kwargs: fake)
    session = profile_switcher.DeviceSession("/dev/fake")
    response = session.command({"cmd": "status"})
    assert response == {"event": "response", "cmd": "status", "ok": True}
    assert session.poll() == [
        {
            "event": "host_key",
            "key": 2,
            "subprofile": "Status",
            "duration_ms": 40,
        }
    ]
    session.close()
    assert fake.closed


def test_persistent_device_session_reassembles_fragmented_json(monkeypatch):
    fake = FakeSerial()

    def write(value):
        fake.writes.append(json.loads(value.decode("utf-8")))
        fake.lines.extend(
            [
                b'{"event":"response",',
                b'"cmd":"status","ok":true}\n',
            ]
        )

    fake.write = write
    monkeypatch.setattr(profile_switcher.serial, "Serial", lambda *args, **kwargs: fake)
    session = profile_switcher.DeviceSession("/dev/fake")
    assert session.command({"cmd": "status"})["ok"] is True
