from macropad_configurator.profile_switcher import (
    FocusedWindow,
    ProfileTarget,
    choose_profile,
    choose_target,
    find_focused_window,
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
