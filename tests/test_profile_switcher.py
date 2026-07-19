from types import SimpleNamespace

import macropad_configurator.profile_switcher as profile_switcher
from macropad_configurator.profile_switcher import (
    FocusedWindow,
    ProfileTarget,
    choose_profile,
    choose_visible_profiles,
    choose_target,
    find_focused_window,
    find_open_windows,
    query_i3_tree,
    rule_matches,
)


CONFIG = {
    "desktop_profile": "i3wm",
    "default_profile": "editing",
    "rules": [
        {"profile": "comfyui", "subprofile": "In App", "title_contains": ["comfyui"]},
        {"profile": "firefox", "subprofile": "In App", "class_contains": ["firefox"]},
        {
            "profile": "terminal-manjaro",
            "class_contains": ["alacritty", "kitty"],
        },
    ],
}


def test_find_focused_window_extracts_i3_properties():
    tree = {
        "nodes": [
            {
                "focused": False,
                "nodes": [
                    {
                        "focused": True,
                        "name": "ComfyUI",
                        "window_properties": {
                            "class": "firefox",
                            "instance": "Navigator",
                            "title": "ComfyUI - Firefox",
                        },
                    }
                ],
            }
        ]
    }
    assert find_focused_window(tree) == FocusedWindow(
        title="ComfyUI - Firefox",
        window_class="firefox",
        instance="Navigator",
    )


def test_find_open_windows_extracts_tiled_floating_and_wayland_apps():
    tree = {
        "nodes": [
            {
                "nodes": [
                    {
                        "name": "Editor",
                        "window_properties": {
                            "class": "Code",
                            "instance": "code-oss",
                            "title": "project - Code",
                        },
                    },
                    {"name": "Terminal", "app_id": "foot"},
                ],
                "floating_nodes": [
                    {
                        "name": "Video",
                        "window_properties": {"class": "vlc"},
                    }
                ],
            }
        ]
    }
    assert find_open_windows(tree) == [
        FocusedWindow(
            title="project - Code",
            window_class="Code",
            instance="code-oss",
        ),
        FocusedWindow(title="Terminal", app_id="foot"),
        FocusedWindow(title="Video", window_class="vlc"),
    ]


def test_query_i3_tree_discovers_socket_without_graphical_environment(
    tmp_path,
    monkeypatch,
):
    runtime = tmp_path / "run"
    socket = runtime / "i3" / "ipc-socket.42"
    socket.parent.mkdir(parents=True)
    socket.touch()
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(runtime))
    for variable in ("DISPLAY", "I3SOCK", "SWAYSOCK"):
        monkeypatch.delenv(variable, raising=False)
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout='{"nodes": []}', stderr="")

    monkeypatch.setattr(profile_switcher.subprocess, "run", run)

    assert query_i3_tree() == {"nodes": []}
    assert calls == [
        (
            ["i3-msg", "-s", str(socket), "-t", "get_tree"],
            {
                "check": False,
                "capture_output": True,
                "text": True,
                "timeout": 3.0,
            },
        )
    ]


def test_rules_use_first_match_so_web_apps_override_browser():
    window = FocusedWindow(title="ComfyUI - Firefox", window_class="firefox")
    assert choose_profile(CONFIG, window) == "comfyui"
    assert choose_profile(CONFIG, FocusedWindow(window_class="Firefox")) == "firefox"
    assert choose_target(CONFIG, window) == ProfileTarget("comfyui", "In App")


def test_visible_profiles_include_pinned_and_all_matching_open_apps():
    config = {
        **CONFIG,
        "filter_open_apps": True,
        "pinned_profiles": ["quicklaunch", "options", "i3wm"],
    }
    windows = [
        FocusedWindow(title="Video - YouTube", window_class="firefox"),
        FocusedWindow(window_class="kitty"),
        FocusedWindow(window_class="unknown"),
    ]
    assert choose_visible_profiles(config, windows) == (
        "i3wm",
        "quicklaunch",
        "options",
        "firefox",
        "terminal-manjaro",
    )


def test_visible_profile_filter_can_be_disabled_to_restore_full_library():
    assert choose_visible_profiles(CONFIG, [FocusedWindow(window_class="firefox")]) == ()


def test_visible_profiles_keep_the_selected_default_for_an_unknown_app():
    config = {
        **CONFIG,
        "filter_open_apps": True,
        "pinned_profiles": ["options"],
    }
    assert choose_visible_profiles(
        config,
        [FocusedWindow(window_class="unknown")],
        selected_profile="editing",
    ) == ("i3wm", "options", "editing")


def test_service_sends_filter_only_when_open_app_set_changes(monkeypatch):
    config = {
        **CONFIG,
        "filter_open_apps": True,
        "pinned_profiles": ["quicklaunch", "options"],
    }
    tree = {
        "nodes": [
            {
                "focused": True,
                "window_properties": {
                    "class": "firefox",
                    "title": "Documentation",
                },
            }
        ]
    }
    port = SimpleNamespace(device="/dev/ttyACM0", serial_number="PAD1")
    visible_calls = []
    target_calls = []

    monkeypatch.setattr(profile_switcher, "query_i3_tree", lambda: tree)
    monkeypatch.setattr(profile_switcher, "macropad_ports", lambda: [port])

    def send_visible(port_name, profile_ids):
        visible_calls.append((port_name, profile_ids))
        return {"profile_count": len(profile_ids)}

    def send_target(port_name, profile_id, subprofile):
        target_calls.append((port_name, profile_id, subprofile))
        return {
            "profile": profile_id,
            "subprofile": subprofile,
            "ignored": False,
        }

    monkeypatch.setattr(profile_switcher, "send_visible_profiles_to_port", send_visible)
    monkeypatch.setattr(profile_switcher, "send_to_port", send_target)

    service = profile_switcher.ActiveProfileService(config)
    assert service.tick() == "firefox"
    assert visible_calls == [
        (
            "/dev/ttyACM0",
            ("i3wm", "quicklaunch", "options", "firefox"),
        )
    ]
    assert target_calls == [("/dev/ttyACM0", "firefox", "In App")]

    assert service.tick() == "firefox"
    assert len(visible_calls) == 1
    assert len(target_calls) == 1

    tree["nodes"].append(
        {
            "focused": False,
            "window_properties": {"class": "kitty", "title": "Shell"},
        }
    )
    assert service.tick() == "firefox"
    assert visible_calls[-1][1] == (
        "i3wm",
        "quicklaunch",
        "options",
        "firefox",
        "terminal-manjaro",
    )
    assert len(target_calls) == 1


def test_desktop_and_unknown_window_fallbacks():
    assert choose_profile(CONFIG, None) == "i3wm"
    assert choose_profile(CONFIG, FocusedWindow(window_class="unknown")) == "editing"
    assert choose_target(CONFIG, None) == ProfileTarget("i3wm")


def test_rule_selectors_are_case_insensitive_and_combined():
    rule = {
        "profile": "ssh",
        "class_contains": ["terminal"],
        "title_contains": ["ssh"],
    }
    assert rule_matches(
        rule,
        FocusedWindow(title="SSH user@host", window_class="Xfce4-Terminal"),
    )
    assert not rule_matches(
        rule,
        FocusedWindow(title="Local shell", window_class="Xfce4-Terminal"),
    )


def test_bundled_map_selects_desktop_application_profiles():
    import json
    from pathlib import Path

    config = json.loads(
        (Path(__file__).resolve().parents[1] / "config" / "active-profile-map.json").read_text(
            encoding="utf-8"
        )
    )
    cases = {
        "Caja": "caja",
        "krita": "krita",
        "libreoffice-writer": "libreoffice",
        "soffice": "libreoffice",
        "Blender": "blender",
    }
    for window_class, expected_profile in cases.items():
        target = choose_target(config, FocusedWindow(window_class=window_class))
        assert target == ProfileTarget(expected_profile, "In App")


def test_bundled_map_selects_firefox_website_profiles_before_firefox():
    import json
    from pathlib import Path

    config = json.loads(
        (Path(__file__).resolve().parents[1] / "config" / "active-profile-map.json").read_text(
            encoding="utf-8"
        )
    )
    cases = {
        "A community on Reddit - Firefox": "reddit",
        "Video title - YouTube — Mozilla Firefox": "youtube",
        "Instagram — Mozilla Firefox": "instagram",
        "Model detail | Printables.com - Firefox": "printables",
        "Thingiverse - Digital Designs - Firefox": "thingiverse",
        "Nitter — Mozilla Firefox": "nitter",
        "Prime Video: Watch now - Firefox": "prime-video",
    }
    for title, expected_profile in cases.items():
        target = choose_target(
            config,
            FocusedWindow(title=title, window_class="Firefox"),
        )
        assert target == ProfileTarget(expected_profile, "In App")

    assert choose_target(
        config,
        FocusedWindow(title="Unmatched page - Firefox", window_class="Firefox"),
    ) == ProfileTarget("firefox", "In App")
    assert choose_target(
        config,
        FocusedWindow(title="YouTube notes", window_class="Code"),
    ) == ProfileTarget("vscode", "In App")


def test_bundled_automatic_rules_all_request_the_contextual_layout():
    import json
    from pathlib import Path

    config = json.loads(
        (Path(__file__).resolve().parents[1] / "config" / "active-profile-map.json").read_text(
            encoding="utf-8"
        )
    )
    assert config["default_subprofile"] == "In App"
    assert all(rule.get("subprofile") == "In App" for rule in config["rules"])
