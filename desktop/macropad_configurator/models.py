from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
NUM_KEYS = 12
MAX_PROFILES = 32
MAX_STEPS = 16
MAX_TEXT = 512
MAX_DELAY_MS = 10_000
STEP_TYPES = ("hotkey", "text", "consumer", "mouse", "delay")
DEFAULT_IDLE = "#102040"
DEFAULT_PRESSED = "#FFFFFF"
DEFAULT_BRIGHTNESS = 5
CONSUMER_CODES = (
    "MUTE",
    "VOLUME_DECREMENT",
    "VOLUME_INCREMENT",
    "PLAY_PAUSE",
    "SCAN_PREVIOUS_TRACK",
    "SCAN_NEXT_TRACK",
    "STOP",
    "RECORD",
    "EJECT",
)
MOUSE_BUTTONS = ("LEFT_BUTTON", "MIDDLE_BUTTON", "RIGHT_BUTTON")


class ValidationError(ValueError):
    pass


def clamp_int(value: Any, low: int, high: int, fallback: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(low, min(high, number))


def normalize_color(value: Any, fallback: str = DEFAULT_IDLE) -> str:
    if isinstance(value, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", value.strip()):
        return value.strip().upper()
    return fallback


def empty_control(index: int = 0, lighting: bool = True) -> dict[str, Any]:
    control: dict[str, Any] = {
        "name": f"Key {index + 1}" if index < NUM_KEYS else "Encoder",
        "oled_label": f"K{index + 1}" if index < NUM_KEYS else "KNOB",
        "steps": [],
    }
    if lighting:
        control.update(lighting_enabled=True, idle_color=DEFAULT_IDLE, pressed_color=DEFAULT_PRESSED)
    return control


def normalize_step(step: Any) -> dict[str, Any] | None:
    if not isinstance(step, dict) or step.get("type") not in STEP_TYPES:
        return None
    step_type = step["type"]
    if step_type == "hotkey":
        keys = step.get("keys", [])
        if not isinstance(keys, list):
            return None
        keys = [str(key).strip().upper().replace(" ", "_") for key in keys if str(key).strip()]
        return {"type": "hotkey", "keys": keys[:6]} if keys else None
    if step_type == "text":
        return {"type": "text", "text": str(step.get("text", ""))[:MAX_TEXT]}
    if step_type == "consumer":
        code = str(step.get("code", "")).upper()
        return {"type": "consumer", "code": code} if code else None
    if step_type == "mouse":
        action = str(step.get("action", "move")).lower()
        if action == "click":
            return {
                "type": "mouse",
                "action": "click",
                "button": str(step.get("button", "LEFT_BUTTON")).upper(),
            }
        return {
            "type": "mouse",
            "action": "move",
            "x": clamp_int(step.get("x", 0), -127, 127, 0),
            "y": clamp_int(step.get("y", 0), -127, 127, 0),
            "wheel": clamp_int(step.get("wheel", 0), -127, 127, 0),
        }
    return {"type": "delay", "ms": clamp_int(step.get("ms", 0), 0, MAX_DELAY_MS, 0)}


def normalize_control(control: Any, index: int, lighting: bool = True) -> dict[str, Any]:
    result = empty_control(index, lighting)
    if not isinstance(control, dict):
        control = {}
    result["name"] = str(control.get("name", result["name"]))[:24]
    result["oled_label"] = str(control.get("oled_label", result["oled_label"]))[:6]
    steps = control.get("steps", [])
    if not isinstance(steps, list):
        steps = []
    result["steps"] = [item for item in (normalize_step(step) for step in steps[:MAX_STEPS]) if item]
    if lighting:
        result["lighting_enabled"] = control.get("lighting_enabled", True) is not False
        result["idle_color"] = normalize_color(control.get("idle_color"), DEFAULT_IDLE)
        result["pressed_color"] = normalize_color(control.get("pressed_color"), DEFAULT_PRESSED)
    return result


def new_profile(profile_id: str, name: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "id": profile_id,
        "name": name[:24],
        "icon": "",
        "brightness": DEFAULT_BRIGHTNESS,
        "keys": [empty_control(index) for index in range(NUM_KEYS)],
        "encoder_press": empty_control(NUM_KEYS, False),
    }


def normalize_profile(profile: Any, fallback_id: str = "default") -> dict[str, Any]:
    if not isinstance(profile, dict):
        profile = {}
    profile_id = slugify(str(profile.get("id", fallback_id))) or fallback_id
    result = new_profile(profile_id, str(profile.get("name", "Default")))
    result["icon"] = str(profile.get("icon", ""))[:2]
    result["brightness"] = clamp_int(
        profile.get("brightness", DEFAULT_BRIGHTNESS), 0, 100, DEFAULT_BRIGHTNESS
    )
    keys = profile.get("keys", [])
    if not isinstance(keys, list):
        keys = []
    result["keys"] = [normalize_control(keys[index] if index < len(keys) else {}, index) for index in range(NUM_KEYS)]
    result["encoder_press"] = normalize_control(profile.get("encoder_press", {}), NUM_KEYS, False)
    return result


def new_project() -> dict[str, Any]:
    editing = new_profile("editing", "Editing")
    editing["icon"] = "ED"
    actions = (
        ("Copy", ["CONTROL", "C"], "#00FF66"),
        ("Paste", ["CONTROL", "V"], "#00FF66"),
        ("Cut", ["CONTROL", "X"], "#FF7A00"),
        ("Undo", ["CONTROL", "Z"], "#FFD000"),
        ("Redo", ["CONTROL", "SHIFT", "Z"], "#FFD000"),
        ("Save", ["CONTROL", "S"], "#00FF66"),
        ("Find", ["CONTROL", "F"], "#B8FF00"),
        ("Select", ["CONTROL", "A"], "#FFD000"),
        ("Enter", ["ENTER"], "#00FF66"),
        ("Previous tab", ["CONTROL", "SHIFT", "TAB"], "#B8FF00"),
        ("Next tab", ["CONTROL", "TAB"], "#B8FF00"),
        ("Close", ["CONTROL", "W"], "#FF2020"),
    )
    for index, (name, keys, color) in enumerate(actions):
        editing["keys"][index].update(
            name=name,
            oled_label=name.upper().replace(" ", "")[:6],
            idle_color=color,
            steps=[{"type": "hotkey", "keys": keys}],
        )
    editing["encoder_press"].update(
        name="Application switcher",
        oled_label="SWITCH",
        steps=[{"type": "hotkey", "keys": ["ALT", "TAB"]}],
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "keyboard_layout": "us",
        "profiles": [editing],
    }


def profile_template(kind: str, profile_id: str, name: str | None = None) -> dict[str, Any]:
    """Return a built-in profile template with a caller-owned id."""
    kind = kind.lower()
    if kind == "editing":
        profile = copy.deepcopy(new_project()["profiles"][0])
        profile["id"] = profile_id
        profile["name"] = (name or "Editing")[:24]
        return profile
    if kind == "media":
        profile = new_profile(profile_id, name or "Media")
        profile["icon"] = "AV"
        actions = (
            ("Mute", "MUTE", "#FF2020"),
            ("Volume down", "VOLUME_DECREMENT", "#FF7A00"),
            ("Volume up", "VOLUME_INCREMENT", "#00FF66"),
            ("Previous", "SCAN_PREVIOUS_TRACK", "#B8FF00"),
            ("Play pause", "PLAY_PAUSE", "#00FF66"),
            ("Next", "SCAN_NEXT_TRACK", "#B8FF00"),
        )
        for index, (label, code, color) in enumerate(actions):
            profile["keys"][index].update(
                name=label,
                oled_label=label.upper().replace(" ", "")[:6],
                idle_color=color,
                steps=[{"type": "consumer", "code": code}],
            )
        return profile
    profile = new_profile(profile_id, name or "Blank")
    profile["icon"] = "BL"
    return profile


def normalize_project(project: Any) -> dict[str, Any]:
    if not isinstance(project, dict):
        project = {}
    profiles = project.get("profiles", [])
    if not isinstance(profiles, list):
        profiles = []
    normalized: list[dict[str, Any]] = []
    used: set[str] = set()
    for index, profile in enumerate(profiles[:MAX_PROFILES]):
        item = normalize_profile(profile, f"profile-{index + 1}")
        item["id"] = unique_id(item["id"], used)
        used.add(item["id"])
        normalized.append(item)
    if not normalized:
        normalized = new_project()["profiles"]
    return {
        "schema_version": SCHEMA_VERSION,
        "keyboard_layout": "de" if project.get("keyboard_layout") == "de" else "us",
        "profiles": normalized,
    }


def validate_project(project: Any) -> dict[str, Any]:
    normalized = normalize_project(project)
    errors: list[str] = []
    if len(normalized["profiles"]) > MAX_PROFILES:
        errors.append(f"No more than {MAX_PROFILES} profiles are supported")
    for profile in normalized["profiles"]:
        if not profile["name"].strip():
            errors.append(f"Profile {profile['id']} has no name")
        for control in profile["keys"] + [profile["encoder_press"]]:
            if len(control["steps"]) > MAX_STEPS:
                errors.append(f"{profile['name']}/{control['name']} has too many steps")
            for step in control["steps"]:
                if step["type"] == "consumer" and step["code"] not in CONSUMER_CODES:
                    errors.append(f"Unsupported consumer code: {step['code']}")
                if step["type"] == "mouse" and step.get("action") == "click" and step["button"] not in MOUSE_BUTTONS:
                    errors.append(f"Unsupported mouse button: {step['button']}")
    if errors:
        raise ValidationError("\n".join(errors))
    return normalized


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower()).strip("-")
    return value[:32]


def unique_id(base: str, used: set[str]) -> str:
    base = slugify(base) or "profile"
    candidate = base
    suffix = 2
    while candidate in used:
        tail = f"-{suffix}"
        candidate = base[: 32 - len(tail)] + tail
        suffix += 1
    return candidate


def duplicate_profile(profile: dict[str, Any], used: set[str]) -> dict[str, Any]:
    result = copy.deepcopy(profile)
    result["name"] = (profile["name"] + " Copy")[:24]
    result["id"] = unique_id(profile["id"] + "-copy", used)
    return result


def step_summary(step: dict[str, Any]) -> str:
    step_type = step.get("type", "")
    if step_type == "hotkey":
        return "Shortcut  " + "+".join(step.get("keys", []))
    if step_type == "text":
        text = str(step.get("text", "")).replace("\n", " ")
        return "Text  " + (text[:42] + ("…" if len(text) > 42 else ""))
    if step_type == "consumer":
        return "Media  " + str(step.get("code", ""))
    if step_type == "mouse":
        if step.get("action") == "click":
            return "Mouse  click " + str(step.get("button", ""))
        return "Mouse  x={x} y={y} wheel={wheel}".format(**step)
    return f"Delay  {step.get('ms', 0)} ms"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    temporary.replace(path)
