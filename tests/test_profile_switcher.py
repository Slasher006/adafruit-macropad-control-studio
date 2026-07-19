from types import SimpleNamespace

import macropad_configurator.profile_switcher as profile_switcher
from macropad_configurator.profile_switcher import (
    FocusedWindow,
    ProfileTarget,
    choose_profile,
    choose_target,
    find_focused_window,
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
