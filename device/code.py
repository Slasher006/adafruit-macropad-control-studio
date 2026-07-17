"""Standalone profile firmware for the Adafruit MacroPad RP2040."""

import gc
import json
import os
import sys
import time

import microcontroller
import supervisor
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode as USKeycode
from adafruit_macropad import MacroPad

from macropad_core import (
    DEFAULT_BRIGHTNESS,
    EncoderStepper,
    find_subprofile_index,
    MAX_PROFILES,
    MacroRunner,
    PersistentToggle,
    SubprofileStore,
    clamp,
    color_tuple,
    normalize_hex_color,
    normalize_index,
    normalize_profile,
    normalize_step,
    safe_profile,
)


CONFIG_PATH = "/device_config.json"
INDEX_PATH = "/profiles/index.json"
REVISION_PATH = "/profiles/revision.txt"
PROFILE_ROOT = "/profiles"
PROFILE_SAVE_DELAY = 1.0
ACTION_OVERLAY_SECONDS = 0.8
ENCODER_DIVISOR = 2
ENCODER_GUARD_SECONDS = 0.075
ENCODER_OPTIONS_HOLD_SECONDS = 0.9
PROFILE_CACHE_SIZE = 1
NVM_SUBPROFILE_OFFSET = 1
NVM_AUTO_SWITCH_INDEX = NVM_SUBPROFILE_OFFSET + MAX_PROFILES
FIRMWARE_VERSION = "1.8.0"

try:
    supervisor.runtime.autoreload = False
except Exception:
    pass


def read_json(path):
    with open(path, "r") as handle:
        return json.load(handle)


def read_text(path, fallback=""):
    try:
        with open(path, "r") as handle:
            return handle.read().strip()
    except OSError:
        return fallback


def load_device_config():
    config = {"schema_version": 1, "keyboard_layout": "us", "revision": "0"}
    try:
        loaded = read_json(CONFIG_PATH)
        if isinstance(loaded, dict):
            config.update(loaded)
    except (OSError, ValueError):
        pass
    config["keyboard_layout"] = "de" if config.get("keyboard_layout") == "de" else "us"
    return config


def layout_classes(layout_name):
    if layout_name == "de":
        try:
            from keyboard_layout_win_de import KeyboardLayout
            from keycode_win_de import Keycode

            return KeyboardLayout, Keycode, "de"
        except ImportError:
            pass
    return KeyboardLayoutUS, USKeycode, "us"


device_config = load_device_config()
LayoutClass, KeycodeClass, active_layout = layout_classes(device_config["keyboard_layout"])
macropad = MacroPad(layout_class=LayoutClass, keycode_class=KeycodeClass)
# The MacroPad helper uses rotaryio's default divisor of 4. This board's
# encoder produces two detents per quadrature cycle, so divisor 2 makes each
# tactile click register as one profile step.
try:
    macropad._encoder.divisor = ENCODER_DIVISOR
except (AttributeError, ValueError):
    pass
runner = MacroRunner(macropad, time.monotonic)
display = macropad.display_text(title=None, text_scale=1)

profile_entries = []
profile_cache = {}
profile_cache_order = []
profile_index = 0
profile_container = safe_profile()
profile = profile_container
subprofile_index = 0
last_revision = read_text(REVISION_PATH, "0")
encoder_stepper = EncoderStepper(macropad.encoder, ENCODER_GUARD_SECONDS)
subprofile_store = SubprofileStore(microcontroller.nvm, NVM_SUBPROFILE_OFFSET)
auto_profile_setting = PersistentToggle(
    microcontroller.nvm,
    NVM_AUTO_SWITCH_INDEX,
    True,
)
automatic_switching_enabled = auto_profile_setting.load()
save_profile_at = None
overlay_until = 0.0
overlay_visible = False
serial_buffer = ""
preview_active = False
encoder_trace_enabled = False
encoder_last_edge_at = None
last_profile_timing = {}
display_pending = None
display_pending_index = 0
options_active = False
encoder_press_started_at = None
encoder_long_press_handled = False


def emit(event, **values):
    payload = {"event": event}
    payload.update(values)
    try:
        print(json.dumps(payload))
    except Exception:
        pass


def set_display_lines(lines):
    global display_pending, display_pending_index
    display_pending = [lines[index] if index < len(lines) else "" for index in range(5)]
    display_pending_index = 0


def refresh_display_step():
    """Update one OLED line so encoder sampling is never blocked by all five."""
    global display_pending, display_pending_index
    if display_pending is None:
        return
    try:
        display[display_pending_index].text = display_pending[display_pending_index]
    except (IndexError, AttributeError):
        display_pending = None
        return
    display_pending_index += 1
    if display_pending_index >= 5:
        try:
            display.show()
        except AttributeError:
            pass
        display_pending = None


def profile_rows():
    rows = []
    for row in range(4):
        labels = []
        for column in range(3):
            control = profile["keys"][row * 3 + column]
            label = control.get("oled_label", "")[:6]
            labels.append(label + (" " * (6 - len(label))))
        rows.append(" ".join(labels))
    return rows


def subprofile_count():
    return 1 + len(profile_container.get("subprofiles", []))


def active_subprofile_name():
    if subprofile_index == 0:
        return profile_container.get("subprofile_name", "Main")
    return profile.get("name", "Subprofile {}".format(subprofile_index + 1))


def profile_title():
    icon = profile.get("icon", profile_container.get("icon", ""))[:2]
    if subprofile_count() > 1:
        title = "{} {}/{}".format(
            active_subprofile_name(),
            subprofile_index + 1,
            subprofile_count(),
        )
    else:
        title = profile_container.get("name", "Profile")
    return (((icon + " ") if icon else "") + title)[:20]


def show_profile():
    global overlay_visible
    set_display_lines([profile_title()] + profile_rows())
    overlay_visible = False


def show_options():
    global options_active, overlay_visible
    runner.cancel()
    options_active = True
    overlay_visible = False
    macropad.pixels.brightness = 0.03
    for index in range(12):
        macropad.pixels[index] = (0, 0, 0)
    macropad.pixels[0] = (32, 128, 255) if not automatic_switching_enabled else (4, 12, 24)
    macropad.pixels[2] = (0, 255, 64) if automatic_switching_enabled else (0, 24, 8)
    role = "APP DECK" if automatic_switching_enabled else "MANUAL DECK"
    description = "Follows focused app" if automatic_switching_enabled else "Keeps chosen profile"
    set_display_lines(
        [
            "OPTIONS: DECK ROLE",
            "Role: {}".format(role),
            description,
            "K1 Manual | K3 App",
            "Press knob; turn out",
        ]
    )


def set_automatic_switching(enabled):
    global automatic_switching_enabled
    automatic_switching_enabled = bool(enabled)
    auto_profile_setting.save(automatic_switching_enabled)
    emit(
        "auto_profile",
        enabled=automatic_switching_enabled,
        deck_role="app" if automatic_switching_enabled else "manual",
    )
    if options_active:
        show_options()


def describe_step(step):
    step_type = step.get("type", "")
    if step_type == "hotkey":
        return "+".join(step.get("keys", []))[:20]
    if step_type == "text":
        return "Text: " + str(step.get("text", ""))[:14]
    if step_type == "consumer":
        return str(step.get("code", ""))[:20]
    if step_type == "mouse":
        return "Mouse " + str(step.get("action", ""))[:14]
    if step_type == "delay":
        return "Delay {} ms".format(step.get("ms", 0))
    return "No action"


def show_action(control):
    global overlay_until, overlay_visible
    steps = control.get("steps", [])
    details = describe_step(steps[0]) if steps else "No action"
    set_display_lines([
        profile_title(),
        "> " + control.get("name", "Control")[:18],
        details,
        "{} step{}".format(len(steps), "" if len(steps) == 1 else "s"),
        "",
    ])
    overlay_until = time.monotonic() + ACTION_OVERLAY_SECONDS
    overlay_visible = True


def apply_profile_lighting():
    global preview_active
    preview_active = False
    macropad.pixels.brightness = profile.get("brightness", DEFAULT_BRIGHTNESS) / 100.0
    for index, control in enumerate(profile["keys"]):
        macropad.pixels[index] = (
            color_tuple(control.get("idle_color")) if control.get("lighting_enabled", True) else (0, 0, 0)
        )


def apply_preview(command):
    global preview_active
    brightness = clamp(
        command.get("brightness", profile.get("brightness", DEFAULT_BRIGHTNESS)),
        0,
        100,
        DEFAULT_BRIGHTNESS,
    )
    colors = command.get("colors", [])
    if not isinstance(colors, list) or len(colors) != 12:
        raise ValueError("preview requires 12 colors")
    macropad.pixels.brightness = brightness / 100.0
    for index, value in enumerate(colors):
        macropad.pixels[index] = color_tuple(normalize_hex_color(value))
    preview_active = True


def saved_subprofile_index(parent_index, count):
    return subprofile_store.load(parent_index, count)


def save_subprofile_index():
    subprofile_store.save(profile_index, subprofile_index)


def activate_subprofile(index, announce=True):
    global profile, subprofile_index
    count = subprofile_count()
    subprofile_index = index % count
    if subprofile_index == 0:
        profile = profile_container
    else:
        profile = profile_container["subprofiles"][subprofile_index - 1]
    runner.cancel()
    apply_profile_lighting()
    if profile_container.get("id") == "options":
        show_options()
    else:
        show_profile()
    if announce:
        emit(
            "subprofile",
            profile=profile_container.get("id"),
            name=active_subprofile_name(),
            index=subprofile_index,
            count=count,
        )


def load_profile_at(index, announce=True):
    global profile_index, profile_container, last_profile_timing
    started = time.monotonic()
    if not profile_entries:
        profile_index = 0
        profile_container = safe_profile()
        activate_subprofile(0, False)
        last_profile_timing = {"total_ms": int((time.monotonic() - started) * 1000)}
        return
    profile_index = index % len(profile_entries)
    entry = profile_entries[profile_index]
    cached_profile = profile_cache.get(entry["id"])
    if cached_profile is not None:
        profile_container = cached_profile
        try:
            profile_cache_order.remove(entry["id"])
        except ValueError:
            pass
        profile_cache_order.append(entry["id"])
        read_done = started
        normalize_done = started
    else:
        try:
            loaded = read_json(PROFILE_ROOT + "/" + entry.get("file", entry["id"] + ".json"))
            read_done = time.monotonic()
            profile_container = normalize_profile(loaded, entry["id"])
            normalize_done = time.monotonic()
        except (OSError, ValueError) as exc:
            read_done = time.monotonic()
            profile_container = safe_profile(entry["id"], entry.get("name", "Invalid"))
            normalize_done = time.monotonic()
            emit("config_error", profile=entry["id"], error=str(exc))
        profile_cache[entry["id"]] = profile_container
        profile_cache_order.append(entry["id"])
        while len(profile_cache_order) > PROFILE_CACHE_SIZE:
            profile_cache.pop(profile_cache_order.pop(0), None)
    activate_subprofile(
        saved_subprofile_index(profile_index, subprofile_count()),
        False,
    )
    gc.collect()
    lighting_done = time.monotonic()
    show_done = time.monotonic()
    last_profile_timing = {
        "read_ms": int((read_done - started) * 1000),
        "normalize_ms": int((normalize_done - read_done) * 1000),
        "lighting_ms": int((lighting_done - normalize_done) * 1000),
        "display_ms": int((show_done - lighting_done) * 1000),
        "total_ms": int((show_done - started) * 1000),
    }
    if announce:
        emit(
            "profile",
            id=profile_container.get("id"),
            name=profile_container.get("name"),
            index=profile_index,
            subprofile=active_subprofile_name(),
            subprofile_index=subprofile_index,
        )


def load_all_config(preserve_id=None):
    global profile_entries, profile_cache, profile_cache_order, last_revision
    old_id = preserve_id or profile_container.get("id")
    try:
        index_data = read_json(INDEX_PATH)
        entries = normalize_index(index_data)
        if not entries:
            raise ValueError("profile index is empty")
        profile_entries = entries
    except (OSError, ValueError) as exc:
        profile_entries = [{"id": "default", "name": "Config error"}]
        emit("config_error", error=str(exc))
    profile_cache = {}
    profile_cache_order = []
    gc.collect()
    selected = 0
    for index, entry in enumerate(profile_entries):
        if entry["id"] == old_id:
            selected = index
            break
    load_profile_at(selected, False)
    last_revision = read_text(REVISION_PATH, last_revision)


def start_control(control, number):
    if runner.running:
        return
    show_action(control)
    runner.start(control.get("steps", []))
    emit("action", control=number, name=control.get("name", ""))


def serial_response(command, ok=True, **values):
    payload = {"event": "response", "cmd": command, "ok": ok}
    payload.update(values)
    try:
        print(json.dumps(payload))
    except Exception:
        pass


def handle_command(command):
    global encoder_trace_enabled, encoder_last_edge_at, options_active
    name = str(command.get("cmd", ""))
    try:
        if name in ("ping", "status"):
            serial_response(
                name,
                board="adafruit_macropad_rp2040",
                schema_version=1,
                profile=profile_container.get("id"),
                subprofile=active_subprofile_name(),
                subprofile_index=subprofile_index,
                subprofile_count=subprofile_count(),
                automatic_switching=automatic_switching_enabled,
                deck_role="app" if automatic_switching_enabled else "manual",
                layout=active_layout,
                encoder_divisor=getattr(getattr(macropad, "_encoder", None), "divisor", None),
                encoder_guard_ms=int(ENCODER_GUARD_SECONDS * 1000),
                profile_timing=last_profile_timing,
                heap_free=gc.mem_free(),
                profile_cache_size=len(profile_cache),
                firmware_version=FIRMWARE_VERSION,
                revision=last_revision,
            )
        elif name == "set_profile":
            requested_id = str(command.get("id", "")).strip()
            requested_subprofile = command.get("subprofile")
            target_index = None
            for index, entry in enumerate(profile_entries):
                if entry["id"] == requested_id:
                    target_index = index
                    break
            if target_index is None:
                raise ValueError("unknown profile: {}".format(requested_id))
            automatic = command.get("automatic", False) is True
            if automatic and options_active:
                serial_response(
                    name,
                    changed=False,
                    ignored=True,
                    reason="options_open",
                    automatic_switching=automatic_switching_enabled,
                    deck_role="app" if automatic_switching_enabled else "manual",
                    profile=profile_container.get("id"),
                )
            elif automatic and not automatic_switching_enabled:
                serial_response(
                    name,
                    changed=False,
                    ignored=True,
                    automatic_switching=False,
                    deck_role="manual",
                    profile=profile_container.get("id"),
                )
            else:
                changed = target_index != profile_index
                if changed:
                    options_active = False
                    load_profile_at(target_index)
                    try:
                        microcontroller.nvm[0] = profile_index
                    except Exception:
                        pass
                if requested_subprofile is not None:
                    requested_subprofile_index = find_subprofile_index(
                        profile_container,
                        requested_subprofile,
                    )
                    if requested_subprofile_index is None:
                        raise ValueError(
                            "unknown subprofile: {}".format(requested_subprofile)
                        )
                    if requested_subprofile_index != subprofile_index:
                        activate_subprofile(requested_subprofile_index)
                        changed = True
                serial_response(
                    name,
                    changed=changed,
                    ignored=False,
                    automatic_switching=automatic_switching_enabled,
                    deck_role="app" if automatic_switching_enabled else "manual",
                    profile=profile_container.get("id"),
                    subprofile=active_subprofile_name(),
                )
        elif name == "set_auto_switch":
            set_automatic_switching(command.get("enabled", True) is not False)
            serial_response(
                name,
                enabled=automatic_switching_enabled,
                deck_role="app" if automatic_switching_enabled else "manual",
            )
        elif name == "preview_lighting":
            apply_preview(command)
            serial_response(name)
        elif name == "clear_preview":
            apply_profile_lighting()
            serial_response(name)
        elif name == "encoder_trace":
            encoder_trace_enabled = command.get("enabled", True) is not False
            encoder_last_edge_at = None
            serial_response(name, enabled=encoder_trace_enabled)
        elif name == "profile_bench":
            original_index = profile_index
            results = []
            iterations = clamp(command.get("iterations", 4), 1, 8, 4)
            for offset in range(iterations):
                load_profile_at(original_index + offset + 1, False)
                results.append(dict(last_profile_timing))
            load_profile_at(original_index, False)
            serial_response(name, results=results)
        elif name == "test_steps":
            raw_steps = command.get("steps", [])
            if not isinstance(raw_steps, list):
                raise ValueError("steps must be a list")
            steps = [step for step in (normalize_step(item) for item in raw_steps[:16]) if step]
            runner.cancel()
            temporary = {"name": str(command.get("name", "Test"))[:24], "steps": steps}
            show_action(temporary)
            runner.start(steps)
            serial_response(name, steps=len(steps))
        elif name == "reload_config":
            serial_response(name, restarting=True)
            time.sleep(0.05)
            microcontroller.reset()
        else:
            serial_response(name, False, error="unknown command")
    except Exception as exc:
        serial_response(name, False, error=str(exc))


def poll_serial():
    global serial_buffer
    try:
        while supervisor.runtime.serial_bytes_available:
            character = sys.stdin.read(1)
            if character in ("\r", "\n"):
                line = serial_buffer.strip()
                serial_buffer = ""
                if line.startswith("{"):
                    try:
                        handle_command(json.loads(line))
                    except ValueError as exc:
                        serial_response("parse", False, error=str(exc))
            elif character and character >= " ":
                serial_buffer += character
                if len(serial_buffer) > 12000:
                    serial_buffer = ""
    except Exception:
        serial_buffer = ""


def initial_profile_index():
    try:
        value = microcontroller.nvm[0]
        if value < len(profile_entries):
            return value
    except Exception:
        pass
    return 0


load_all_config(None)
load_profile_at(initial_profile_index(), False)
emit("ready", board="adafruit_macropad_rp2040", schema_version=1, layout=active_layout)

while True:
    now = time.monotonic()
    poll_serial()

    encoder_position = macropad.encoder
    previous_encoder_position = encoder_stepper.position
    encoder_step = encoder_stepper.update(encoder_position, now)
    if encoder_trace_enabled and encoder_position != previous_encoder_position:
        since_previous_ms = (
            None if encoder_last_edge_at is None else int((now - encoder_last_edge_at) * 1000)
        )
        encoder_last_edge_at = now
        emit(
            "encoder_trace",
            phase="edge",
            position=encoder_position,
            delta=encoder_position - previous_encoder_position,
            accepted=bool(encoder_step),
            since_previous_ms=since_previous_ms,
            guard_remaining_ms=max(0, int((encoder_stepper.ready_at - now) * 1000)),
        )
    if encoder_step and profile_entries:
        if options_active and profile_container.get("id") != "options":
            options_active = False
            apply_profile_lighting()
            show_profile()
            load_started = None
        else:
            options_active = False
            runner.cancel()
            load_started = time.monotonic()
            load_profile_at(profile_index + encoder_step)
            save_profile_at = time.monotonic() + PROFILE_SAVE_DELAY
        # Absorb movement accumulated during display/profile work.
        now = time.monotonic()
        encoder_stepper.suppress(macropad.encoder, now)
        if encoder_trace_enabled and load_started is not None:
            emit(
                "encoder_trace",
                phase="loaded",
                profile=profile_container.get("id"),
                load_ms=int((now - load_started) * 1000),
                absorbed_position=encoder_stepper.position,
            )

    macropad.encoder_switch_debounced.update()
    if macropad.encoder_switch_debounced.pressed:
        encoder_press_started_at = now
        encoder_long_press_handled = False
    if (
        encoder_press_started_at is not None
        and not encoder_long_press_handled
        and not options_active
        and now - encoder_press_started_at >= ENCODER_OPTIONS_HOLD_SECONDS
    ):
        show_options()
        encoder_long_press_handled = True
    if macropad.encoder_switch_debounced.released:
        if not encoder_long_press_handled:
            if options_active:
                set_automatic_switching(not automatic_switching_enabled)
            elif subprofile_count() > 1:
                activate_subprofile(subprofile_index + 1)
                save_subprofile_index()
            else:
                start_control(profile["encoder_press"], 12)
        encoder_press_started_at = None
        encoder_long_press_handled = False

    event = macropad.keys.events.get()
    while event:
        key_number = event.key_number
        if 0 <= key_number < 12 and options_active:
            if event.pressed and key_number == 0:
                set_automatic_switching(False)
            elif event.pressed and key_number == 2:
                set_automatic_switching(True)
        elif 0 <= key_number < 12:
            control = profile["keys"][key_number]
            if event.pressed:
                if not preview_active and control.get("lighting_enabled", True):
                    macropad.pixels[key_number] = color_tuple(control.get("pressed_color"), "#FFFFFF")
                start_control(control, key_number)
            elif event.released and not preview_active:
                macropad.pixels[key_number] = (
                    color_tuple(control.get("idle_color")) if control.get("lighting_enabled", True) else (0, 0, 0)
                )
        event = macropad.keys.events.get()

    refresh_display_step()
    runner.tick()
    if overlay_visible and not runner.running and now >= overlay_until:
        show_profile()

    if save_profile_at is not None and now >= save_profile_at:
        try:
            microcontroller.nvm[0] = profile_index
        except Exception:
            pass
        save_profile_at = None

    time.sleep(0.005)
