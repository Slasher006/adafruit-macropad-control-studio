import pytest

from macropad_configurator.models import (
    DEFAULT_BRIGHTNESS,
    ValidationError,
    duplicate_profile,
    new_profile,
    new_project,
    normalize_color,
    normalize_profile,
    normalize_project,
    normalize_step,
    profile_template,
    validate_project,
)


def test_project_normalization_has_twelve_keys_and_encoder():
    project = normalize_project({"keyboard_layout": "de", "profiles": [{"id": "work", "name": "Work"}]})
    assert project["keyboard_layout"] == "de"
    assert len(project["profiles"][0]["keys"]) == 12
    assert project["profiles"][0]["encoder_press"]["oled_label"] == "KNOB"
    assert project["profiles"][0]["brightness"] == DEFAULT_BRIGHTNESS == 5


def test_profile_values_are_bounded():
    profile = normalize_profile(
        {
            "id": "bad id!",
            "name": "x" * 50,
            "brightness": 500,
            "keys": [
                {
                    "lighting_enabled": False,
                    "requires_confirmation": True,
                    "idle_color": "wrong",
                    "pressed_color": "#abcdef",
                    "oled_label": "toolong",
                }
            ],
        }
    )
    assert profile["id"] == "bad-id"
    assert len(profile["name"]) == 24
    assert profile["brightness"] == 100
    assert profile["keys"][0]["idle_color"] == "#102040"
    assert profile["keys"][0]["pressed_color"] == "#ABCDEF"
    assert profile["keys"][0]["oled_label"] == "toolon"
    assert profile["keys"][0]["lighting_enabled"] is False
    assert profile["keys"][0]["requires_confirmation"] is True


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ({"type": "hotkey", "keys": ["ctrl", "c"]}, {"type": "hotkey", "keys": ["CTRL", "C"]}),
        ({"type": "delay", "ms": 50_000}, {"type": "delay", "ms": 10_000}),
        ({"type": "mouse", "action": "move", "x": 200, "y": -200}, {"type": "mouse", "action": "move", "x": 127, "y": -127, "wheel": 0}),
    ],
)
def test_step_normalization(raw, expected):
    assert normalize_step(raw) == expected


def test_duplicate_gets_unique_id_and_deep_copy():
    original = new_profile("work", "Work")
    duplicate = duplicate_profile(original, {"work", "work-copy"})
    duplicate["keys"][0]["name"] = "Changed"
    assert duplicate["id"] == "work-copy-2"
    assert original["keys"][0]["name"] == "Key 1"


def test_validation_rejects_unsupported_media_code():
    project = new_project()
    project["profiles"][0]["keys"][0]["steps"] = [{"type": "consumer", "code": "LAUNCH_MISSILES"}]
    with pytest.raises(ValidationError, match="Unsupported consumer"):
        validate_project(project)


def test_normalize_color():
    assert normalize_color("#a1b2c3") == "#A1B2C3"
    assert normalize_color("blue") == "#102040"


def test_profile_templates_include_icons_and_actions():
    editing = profile_template("editing", "edit-2")
    media = profile_template("media", "media-2")
    blank = profile_template("blank", "blank-2")
    assert editing["id"] == "edit-2" and editing["icon"] == "ED"
    assert media["icon"] == "AV" and media["keys"][0]["steps"][0]["type"] == "consumer"
    assert blank["icon"] == "BL" and all(not key["steps"] for key in blank["keys"])
    assert {editing["brightness"], media["brightness"], blank["brightness"]} == {5}


def test_project_preserves_and_normalizes_subprofiles():
    project = normalize_project(
        {
            "profiles": [
                {
                    "id": "i3wm",
                    "name": "i3wm",
                    "subprofile_name": "Windows",
                    "subprofiles": [
                        {
                            "name": "Workspaces",
                            "keys": [
                                {
                                    "name": "Workspace 1",
                                    "oled_label": "WS-1",
                                    "steps": [{"type": "hotkey", "keys": ["GUI", "ONE"]}],
                                }
                            ],
                        }
                    ],
                }
            ]
        }
    )
    profile = validate_project(project)["profiles"][0]
    assert profile["subprofile_name"] == "Windows"
    assert [item["name"] for item in profile["subprofiles"]] == ["Workspaces"]
    assert len(profile["subprofiles"][0]["keys"]) == 12
    assert profile["subprofiles"][0]["keys"][0]["steps"][0]["keys"] == ["GUI", "ONE"]
