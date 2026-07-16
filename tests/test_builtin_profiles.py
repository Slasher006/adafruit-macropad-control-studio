import json
from pathlib import Path

from macropad_configurator.models import normalize_project, validate_project


ROOT = Path(__file__).resolve().parents[1]
PROFILE_ROOT = ROOT / "device" / "profiles"
REQUESTED_PROFILE_IDS = {
    "vscode",
    "firefox",
    "vlc",
    "i3wm",
    "discord",
    "lm-studio",
    "terminal-manjaro",
    "comfyui",
    "ssh",
    "audio-controls",
    "quicklaunch",
    "system-control",
}
FUNCTION_COLORS = {"#00FF66", "#B8FF00", "#FFD000", "#FF7A00", "#FF2020"}


def test_builtin_profile_index_and_payloads_are_valid():
    index = json.loads((PROFILE_ROOT / "index.json").read_text(encoding="utf-8"))
    ids = {entry["id"] for entry in index["profiles"]}
    assert REQUESTED_PROFILE_IDS <= ids

    profiles = []
    for entry in index["profiles"]:
        profile = json.loads((PROFILE_ROOT / entry["file"]).read_text(encoding="utf-8"))
        assert profile["id"] == entry["id"]
        assert profile["brightness"] == 5
        assert len(profile["keys"]) == 12
        assert all(len(control["oled_label"]) <= 6 for control in profile["keys"])
        assert {
            control["idle_color"]
            for control in profile["keys"]
            if control.get("lighting_enabled", True)
        } <= FUNCTION_COLORS
        profiles.append(profile)
    project = validate_project(normalize_project({"keyboard_layout": "us", "profiles": profiles}))

    assert len(project["profiles"]) == len(index["profiles"])
    assert all(profile["brightness"] == 5 for profile in project["profiles"])
    assert all(len(profile["keys"]) == 12 for profile in project["profiles"])
    assert all(len(control["oled_label"]) <= 6 for profile in project["profiles"] for control in profile["keys"])


def test_terminal_command_profiles_do_not_auto_execute():
    for filename in ("terminal-manjaro.json", "ssh.json"):
        profile = json.loads((PROFILE_ROOT / filename).read_text(encoding="utf-8"))
        for control in profile["keys"]:
            assert control["steps"]
            assert control["steps"][-1] != {"type": "hotkey", "keys": ["ENTER"]}


def test_quicklaunch_and_system_control_assignments():
    quicklaunch = json.loads((PROFILE_ROOT / "quicklaunch.json").read_text(encoding="utf-8"))
    system = json.loads((PROFILE_ROOT / "system-control.json").read_text(encoding="utf-8"))

    assert [control["name"] for control in quicklaunch["keys"][:6]] == [
        "Launch Firefox",
        "Launch Terminal",
        "Launch VS Code",
        "Launch Caja",
        "Launch Discord",
        "Launch LM Studio",
    ]
    assert all(not control["lighting_enabled"] for control in quicklaunch["keys"][6:])
    assert [control["name"] for control in system["keys"][:5]] == [
        "Restart i3",
        "Reboot computer",
        "Shutdown in 60 min",
        "Shutdown now",
        "Cancel shutdown",
    ]
    assert all(not control["lighting_enabled"] for control in system["keys"][5:])
