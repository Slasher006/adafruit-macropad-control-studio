import json
from pathlib import Path

from macropad_configurator.models import normalize_project, validate_project


ROOT = Path(__file__).resolve().parents[1]
PROFILE_ROOT = ROOT / "device" / "profiles"
REQUESTED_PROFILE_IDS = {
    "vscode",
    "firefox",
    "reddit",
    "youtube",
    "instagram",
    "printables",
    "thingiverse",
    "nitter",
    "prime-video",
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
    "caja",
    "krita",
    "libreoffice",
    "blender",
    "live-controls",
}
FUNCTION_COLORS = {"#00FF66", "#B8FF00", "#FFD000", "#FF7A00", "#FF2020"}
AUTO_PROFILE_IDS = {
    "editing",
    "media",
    "vscode",
    "firefox",
    "reddit",
    "youtube",
    "instagram",
    "printables",
    "thingiverse",
    "nitter",
    "prime-video",
    "vlc",
    "discord",
    "lm-studio",
    "terminal-manjaro",
    "comfyui",
    "ssh",
    "audio-controls",
    "system-control",
    "caja",
    "krita",
    "libreoffice",
    "blender",
}


def test_builtin_profile_index_and_payloads_are_valid():
    index = json.loads((PROFILE_ROOT / "index.json").read_text(encoding="utf-8"))
    ids = {entry["id"] for entry in index["profiles"]}
    assert REQUESTED_PROFILE_IDS <= ids

    profiles = []
    for entry in index["profiles"]:
        profile = json.loads((PROFILE_ROOT / entry["file"]).read_text(encoding="utf-8"))
        assert profile["id"] == entry["id"]
        if profile["id"] == "options":
            assert profile["subprofiles"] == []
            assert profile["encoder_press"]["steps"] == []
            assert len(profile["keys"]) == 12
            profiles.append(profile)
            continue
        assert profile["brightness"] == 5
        expected_subprofiles = (
            7
            if profile["id"] == "live-controls"
            else (3 if profile["id"] in AUTO_PROFILE_IDS else 2)
        )
        assert len(profile["subprofiles"]) == expected_subprofiles
        if profile["id"] == "live-controls":
            assert profile["keys"] == []
            assert all(layout["keys"] == [] for layout in profile["subprofiles"])
            profiles.append(profile)
            continue
        if profile["id"] in AUTO_PROFILE_IDS:
            assert profile["subprofiles"][-1]["name"] == "In App"
        for layout in [profile] + profile["subprofiles"]:
            assert layout["brightness"] == 5
            assert len(layout["keys"]) == 12
            assert all(len(control["oled_label"]) <= 6 for control in layout["keys"])
            assert all(control["steps"] for control in layout["keys"])
            assert {
                control["idle_color"]
                for control in layout["keys"]
                if control.get("lighting_enabled", True)
            } <= FUNCTION_COLORS
        assert profile["encoder_press"]["steps"] == []
        profiles.append(profile)
    project = validate_project(normalize_project({"keyboard_layout": "us", "profiles": profiles}))

    assert len(project["profiles"]) == len(index["profiles"])
    assert all(
        profile["brightness"] == (3 if profile["id"] == "options" else 5)
        for profile in project["profiles"]
    )
    assert all(len(profile["keys"]) == 12 for profile in project["profiles"])
    assert all(len(control["oled_label"]) <= 6 for profile in project["profiles"] for control in profile["keys"])


def test_terminal_command_profiles_do_not_auto_execute():
    for filename in ("terminal-manjaro.json", "ssh.json"):
        profile = json.loads((PROFILE_ROOT / filename).read_text(encoding="utf-8"))
        for layout in [profile] + profile["subprofiles"]:
            for control in layout["keys"]:
                assert control["steps"]
                assert control["steps"][-1] != {"type": "hotkey", "keys": ["ENTER"]}


def test_manjaro_command_screens_open_terminal_and_type_safe_templates():
    profile = json.loads((PROFILE_ROOT / "terminal-manjaro.json").read_text(encoding="utf-8"))
    command_layouts = [profile] + profile["subprofiles"][:2]
    for layout in command_layouts:
        for control in layout["keys"]:
            assert control["steps"][0] == {
                "type": "hotkey",
                "keys": ["GUI", "ENTER"],
            }
            assert control["steps"][1] == {"type": "delay", "ms": 800}
            assert control["steps"][-1]["type"] == "text"

    package_commands = [control["steps"][-1]["text"] for control in profile["keys"]]
    pamac_commands = [command for command in package_commands if "pamac " in command]
    assert pamac_commands
    assert all(not command.startswith("sudo pamac ") for command in pamac_commands)
    assert "sudo pacman -Syu" in package_commands
    assert "sudo paccache -rk3" in package_commands


def test_i3wm_has_expected_subprofile_names():
    profile = json.loads((PROFILE_ROOT / "i3wm.json").read_text(encoding="utf-8"))
    assert profile["subprofile_name"] == "Windows"
    assert [item["name"] for item in profile["subprofiles"]] == ["Workspaces", "Layout"]
    assert len(profile["keys"]) == 12
    assert all(len(item["keys"]) == 12 for item in profile["subprofiles"])
    assert all(control["steps"] for item in profile["subprofiles"] for control in item["keys"])
    assert profile["encoder_press"]["steps"] == []


def test_options_profile_is_a_visible_device_managed_screen():
    index = json.loads((PROFILE_ROOT / "index.json").read_text(encoding="utf-8"))
    assert index["profiles"][-1]["id"] == "options"
    profile = json.loads((PROFILE_ROOT / "options.json").read_text(encoding="utf-8"))
    assert profile["name"] == "Options"
    assert profile["subprofile_name"] == "Deck role"
    assert profile["encoder_press"]["name"] == "Next deck role"
    assert profile["keys"][0]["name"] == "Manual deck"
    assert profile["keys"][1]["name"] == "Profile deck"
    assert profile["keys"][2]["name"] == "App deck"


def test_live_controls_profile_has_all_dynamic_screens():
    profile = json.loads((PROFILE_ROOT / "live-controls.json").read_text(encoding="utf-8"))
    assert [profile["subprofile_name"]] + [
        item["name"] for item in profile["subprofiles"]
    ] == [
        "Status",
        "Programs",
        "App Audio",
        "Windows",
        "Clipboard",
        "Focus",
        "System",
        "Jobs",
    ]


def test_desktop_application_profiles_have_expected_layouts():
    expected = {
        "caja": ["Files", "Navigation", "View", "In App"],
        "krita": ["Painting", "Canvas", "Brush and Layers", "In App"],
        "libreoffice": ["General", "Writer", "Calc and Impress", "In App"],
        "blender": ["General", "Transform", "Viewport", "In App"],
    }
    for profile_id, layout_names in expected.items():
        profile = json.loads(
            (PROFILE_ROOT / f"{profile_id}.json").read_text(encoding="utf-8")
        )
        assert [profile["subprofile_name"]] + [
            item["name"] for item in profile["subprofiles"]
        ] == layout_names


def test_website_profiles_have_expected_layouts_and_contextual_keys():
    expected = {
        "reddit": ["Posts", "Media", "Browser", "In App"],
        "youtube": ["Playback", "Fine Playback", "Browser", "In App"],
        "instagram": ["Browse", "Keyboard Access", "Browser", "In App"],
        "printables": ["Browse", "Keyboard Access", "Browser", "In App"],
        "thingiverse": ["Browse", "Keyboard Access", "Browser", "In App"],
        "nitter": ["Browse", "Keyboard Access", "Browser", "In App"],
        "prime-video": ["Playback", "Keyboard Access", "Browser", "In App"],
    }
    for profile_id, layout_names in expected.items():
        profile = json.loads(
            (PROFILE_ROOT / f"{profile_id}.json").read_text(encoding="utf-8")
        )
        assert [profile["subprofile_name"]] + [
            item["name"] for item in profile["subprofiles"]
        ] == layout_names
        assert profile["subprofiles"][-1]["keys"] == profile["keys"]

    reddit = json.loads((PROFILE_ROOT / "reddit.json").read_text(encoding="utf-8"))
    youtube = json.loads((PROFILE_ROOT / "youtube.json").read_text(encoding="utf-8"))
    prime = json.loads((PROFILE_ROOT / "prime-video.json").read_text(encoding="utf-8"))
    assert [key["name"] for key in reddit["keys"][:6]] == [
        "Next post or comment",
        "Previous post or comment",
        "Copy item link",
        "Upvote",
        "Save or unsave",
        "Downvote",
    ]
    assert [key["name"] for key in youtube["keys"][:3]] == [
        "Rewind 10 seconds",
        "Play or pause",
        "Forward 10 seconds",
    ]
    assert [key["name"] for key in prime["keys"][7:10]] == [
        "Audio track",
        "Captions",
        "Previous control",
    ]


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
    assert [control["name"] for control in quicklaunch["keys"][6:]] == [
        "Launch VLC",
        "Audio mixer",
        "System settings",
        "Calculator",
        "Image editor",
        "System monitor",
    ]
    assert [control["name"] for control in system["keys"][:5]] == [
        "Restart i3",
        "Reboot computer",
        "Shutdown in 60 min",
        "Shutdown now",
        "Cancel shutdown",
    ]
    assert [control["name"] for control in system["keys"][5:]] == [
        "Lock screen",
        "Suspend",
        "Hibernate",
        "i3 logout prompt",
        "Reload i3 config",
        "Open terminal",
        "Application launcher",
    ]
