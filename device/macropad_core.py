"""Hardware-independent validation and macro sequencing for CircuitPython."""

SCHEMA_VERSION = 1
NUM_KEYS = 12
MAX_PROFILES = 32
MAX_SUBPROFILES = 8
MAX_STEPS = 16
MAX_TEXT = 512
MAX_DELAY_MS = 10000
DEFAULT_IDLE = "#102040"
DEFAULT_PRESSED = "#FFFFFF"
DEFAULT_BRIGHTNESS = 5
STEP_TYPES = ("hotkey", "text", "consumer", "mouse", "delay")
DECK_ROLES = ("manual", "app", "profile")
DECK_ROLE_CYCLE = ("manual", "profile", "app")


class EncoderStepper:
    """Turn encoder position changes into one step per physical detent."""

    def __init__(self, position=0, guard_seconds=0.03):
        self.position = position
        self.guard_seconds = guard_seconds
        self.ready_at = 0.0

    def update(self, position, now):
        if position == self.position:
            return 0
        delta = position - self.position
        self.position = position
        if now < self.ready_at:
            return 0
        self.ready_at = now + self.guard_seconds
        return 1 if delta > 0 else -1

    def suppress(self, position, now):
        """Absorb movement accumulated during a blocking profile redraw."""
        self.position = position
        self.ready_at = now + self.guard_seconds


class SubprofileStore:
    """Persist one selected subprofile index for each parent profile slot."""

    def __init__(self, nvm, offset=1):
        self.nvm = nvm
        self.offset = offset

    def load(self, profile_index, count):
        if count < 1:
            return 0
        try:
            value = self.nvm[self.offset + profile_index]
        except Exception:
            return 0
        return value if value < count else 0

    def save(self, profile_index, subprofile_index):
        try:
            self.nvm[self.offset + profile_index] = subprofile_index
            return True
        except Exception:
            return False


class PersistentToggle:
    """Store a boolean in one NVM byte, with a safe default for blank NVM."""

    def __init__(self, nvm, index, default=True):
        self.nvm = nvm
        self.index = index
        self.default = bool(default)

    def load(self):
        try:
            value = self.nvm[self.index]
        except Exception:
            return self.default
        if value == 0:
            return False
        if value == 1:
            return True
        return self.default

    def save(self, enabled):
        try:
            self.nvm[self.index] = 1 if enabled else 0
            return True
        except Exception:
            return False


class PersistentChoice:
    """Store one string choice in an NVM byte while tolerating blank data."""

    def __init__(self, nvm, index, choices, default):
        self.nvm = nvm
        self.index = index
        self.choices = tuple(choices)
        self.default = default if default in self.choices else self.choices[0]

    def load(self):
        try:
            value = self.nvm[self.index]
        except Exception:
            return self.default
        if value < len(self.choices):
            return self.choices[value]
        return self.default

    def save(self, choice):
        if choice not in self.choices:
            return False
        try:
            self.nvm[self.index] = self.choices.index(choice)
            return True
        except Exception:
            return False


def normalize_deck_role(role, fallback="app"):
    return role if role in DECK_ROLES else fallback


def next_deck_role(role):
    role = normalize_deck_role(role)
    try:
        index = DECK_ROLE_CYCLE.index(role)
    except ValueError:
        index = 0
    return DECK_ROLE_CYCLE[(index + 1) % len(DECK_ROLE_CYCLE)]


def accepts_automatic_profile(role):
    return normalize_deck_role(role) != "manual"


def automatic_subprofile(role, requested):
    return requested if normalize_deck_role(role) == "app" else None


def find_subprofile_index(parent, requested):
    """Return a layout index by name or number without changing saved state."""
    count = 1 + len(parent.get("subprofiles", []))
    if isinstance(requested, int):
        return requested if 0 <= requested < count else None
    if not isinstance(requested, str) or not requested.strip():
        return None
    wanted = requested.strip().lower()
    names = [parent.get("subprofile_name", "Main")]
    names.extend(item.get("name", "") for item in parent.get("subprofiles", []))
    for index, name in enumerate(names):
        if str(name).strip().lower() == wanted:
            return index
    return None


def clamp(value, low, high, fallback):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(low, min(high, value))


def normalize_hex_color(value, fallback=DEFAULT_IDLE):
    if not isinstance(value, str):
        return fallback
    value = value.strip().upper()
    if len(value) != 7 or not value.startswith("#"):
        return fallback
    try:
        int(value[1:], 16)
    except ValueError:
        return fallback
    return value


def color_tuple(value, fallback=DEFAULT_IDLE):
    value = normalize_hex_color(value, fallback)
    return (int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16))


def normalize_step(step):
    if not isinstance(step, dict):
        return None
    step_type = step.get("type")
    if step_type not in STEP_TYPES:
        return None
    if step_type == "hotkey":
        keys = step.get("keys", [])
        if not isinstance(keys, list):
            return None
        keys = [str(key).strip().upper().replace(" ", "_") for key in keys if str(key).strip()]
        return {"type": "hotkey", "keys": keys[:6]} if keys else None
    if step_type == "text":
        return {"type": "text", "text": str(step.get("text", ""))[:MAX_TEXT]}
    if step_type == "consumer":
        code = str(step.get("code", "")).strip().upper()
        return {"type": "consumer", "code": code} if code else None
    if step_type == "mouse":
        action = str(step.get("action", "move")).lower()
        if action == "click":
            button = str(step.get("button", "LEFT_BUTTON")).upper()
            return {"type": "mouse", "action": "click", "button": button}
        return {
            "type": "mouse",
            "action": "move",
            "x": clamp(step.get("x", 0), -127, 127, 0),
            "y": clamp(step.get("y", 0), -127, 127, 0),
            "wheel": clamp(step.get("wheel", 0), -127, 127, 0),
        }
    return {"type": "delay", "ms": clamp(step.get("ms", 0), 0, MAX_DELAY_MS, 0)}


def empty_control(index=0):
    return {
        "name": "Key {}".format(index + 1),
        "oled_label": "K{}".format(index + 1),
        "idle_color": DEFAULT_IDLE,
        "pressed_color": DEFAULT_PRESSED,
        "steps": [],
    }


def normalize_control(control, index=0, lighting=True):
    base = empty_control(index)
    if not isinstance(control, dict):
        control = {}
    base["name"] = str(control.get("name", base["name"]))[:24]
    base["oled_label"] = str(control.get("oled_label", base["oled_label"]))[:6]
    steps = control.get("steps", [])
    if not isinstance(steps, list):
        steps = []
    base["steps"] = [item for item in (normalize_step(step) for step in steps[:MAX_STEPS]) if item]
    if lighting:
        base["lighting_enabled"] = control.get("lighting_enabled", True) is not False
        base["idle_color"] = normalize_hex_color(control.get("idle_color"), DEFAULT_IDLE)
        base["pressed_color"] = normalize_hex_color(control.get("pressed_color"), DEFAULT_PRESSED)
    else:
        base.pop("idle_color", None)
        base.pop("pressed_color", None)
    return base


def safe_profile(profile_id="default", name="Default"):
    return {
        "schema_version": SCHEMA_VERSION,
        "id": str(profile_id)[:32],
        "name": str(name)[:24],
        "icon": "",
        "subprofile_name": "Main",
        "brightness": DEFAULT_BRIGHTNESS,
        "keys": [empty_control(index) for index in range(NUM_KEYS)],
        "encoder_press": normalize_control({"name": "Encoder", "oled_label": "KNOB"}, NUM_KEYS, False),
        "subprofiles": [],
    }


def normalize_subprofile(subprofile, index=0, parent=None):
    if not isinstance(subprofile, dict):
        subprofile = {}
    parent = parent or safe_profile()
    keys = subprofile.get("keys", [])
    if not isinstance(keys, list):
        keys = []
    keys = list(keys[:NUM_KEYS])
    while len(keys) < NUM_KEYS:
        keys.append({})
    for key_index in range(NUM_KEYS):
        keys[key_index] = normalize_control(keys[key_index], key_index, True)
    return {
        "name": str(subprofile.get("name", "Subprofile {}".format(index + 2)))[:24],
        "icon": str(subprofile.get("icon", parent.get("icon", "")))[:2],
        "brightness": clamp(
            subprofile.get("brightness", parent.get("brightness", DEFAULT_BRIGHTNESS)),
            0,
            100,
            parent.get("brightness", DEFAULT_BRIGHTNESS),
        ),
        "keys": keys,
    }


def normalize_profile(profile, fallback_id="default"):
    if not isinstance(profile, dict):
        profile = {}
    result = {
        "schema_version": SCHEMA_VERSION,
        "id": str(profile.get("id", fallback_id))[:32],
        "name": str(profile.get("name", "Default"))[:24],
        "icon": str(profile.get("icon", ""))[:2],
        "subprofile_name": str(profile.get("subprofile_name", "Main"))[:24],
        "brightness": clamp(
            profile.get("brightness", DEFAULT_BRIGHTNESS),
            0,
            100,
            DEFAULT_BRIGHTNESS,
        ),
        "keys": [],
        "encoder_press": {},
        "subprofiles": [],
    }
    keys = profile.get("keys", [])
    if not isinstance(keys, list):
        keys = []
    keys = list(keys[:NUM_KEYS])
    while len(keys) < NUM_KEYS:
        keys.append({})
    for key_index in range(NUM_KEYS):
        keys[key_index] = normalize_control(keys[key_index], key_index, True)
    result["keys"] = keys
    result["encoder_press"] = normalize_control(profile.get("encoder_press", {}), NUM_KEYS, False)
    subprofiles = profile.get("subprofiles", [])
    if not isinstance(subprofiles, list):
        subprofiles = []
    subprofiles = list(subprofiles[:MAX_SUBPROFILES])
    for index in range(len(subprofiles)):
        subprofiles[index] = normalize_subprofile(subprofiles[index], index, result)
    result["subprofiles"] = subprofiles
    return result


def normalize_shared_key_profile(profile, fallback_id="default"):
    """Normalize many named screens while sharing one key array to conserve RAM."""
    if not isinstance(profile, dict):
        profile = {}
    compact = dict(profile)
    source_subprofiles = compact.get("subprofiles", [])
    compact["subprofiles"] = []
    result = normalize_profile(compact, fallback_id)
    shared_keys = result["keys"]
    if not isinstance(source_subprofiles, list):
        source_subprofiles = []
    for index, item in enumerate(source_subprofiles[:MAX_SUBPROFILES]):
        if not isinstance(item, dict):
            item = {}
        result["subprofiles"].append(
            {
                "name": str(
                    item.get("name", "Subprofile {}".format(index + 2))
                )[:24],
                "icon": str(item.get("icon", result.get("icon", "")))[:2],
                "brightness": clamp(
                    item.get("brightness", result.get("brightness", DEFAULT_BRIGHTNESS)),
                    0,
                    100,
                    result.get("brightness", DEFAULT_BRIGHTNESS),
                ),
                "keys": shared_keys,
            }
        )
    return result


def normalize_index(data):
    if not isinstance(data, dict):
        return []
    profiles = data.get("profiles", [])
    if not isinstance(profiles, list):
        return []
    result = []
    seen = set()
    for entry in profiles[:MAX_PROFILES]:
        if not isinstance(entry, dict):
            continue
        profile_id = str(entry.get("id", "")).strip()
        if not profile_id or profile_id in seen:
            continue
        allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        if not all(ch in allowed for ch in profile_id):
            continue
        seen.add(profile_id)
        filename = str(entry.get("file", profile_id + ".json"))
        file_allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
        if not filename.endswith(".json") or not all(ch in file_allowed for ch in filename):
            filename = profile_id + ".json"
        result.append(
            {
                "id": profile_id[:32],
                "name": str(entry.get("name", profile_id))[:24],
                "file": filename,
            }
        )
    return result


def filter_profile_entries(entries, profile_ids):
    """Return requested profiles in library order, or the full library as a fallback."""
    if not isinstance(profile_ids, list) or not profile_ids:
        return list(entries)
    wanted = set()
    for profile_id in profile_ids:
        value = str(profile_id).strip()
        if value:
            wanted.add(value)
    filtered = [entry for entry in entries if entry.get("id") in wanted]
    return filtered or list(entries)


KEY_ALIASES = {
    "CTRL": "CONTROL",
    "CMD": "GUI",
    "COMMAND": "GUI",
    "META": "GUI",
    "WIN": "WINDOWS",
    "ESC": "ESCAPE",
    "DEL": "DELETE",
    "RETURN": "ENTER",
}


def resolve_keycodes(tokens, keycode_class):
    codes = []
    for token in tokens:
        name = str(token).strip().upper().replace(" ", "_").replace("-", "_")
        name = KEY_ALIASES.get(name, name)
        code = getattr(keycode_class, name, None)
        if code is None and name == "WINDOWS":
            code = getattr(keycode_class, "GUI", None)
        if code is None:
            raise ValueError("Unknown key: {}".format(token))
        codes.append(code)
    return codes


class MacroRunner:
    """Non-blocking action sequence executor using an injected MacroPad object."""

    def __init__(self, macropad, monotonic):
        self.macropad = macropad
        self.monotonic = monotonic
        self.steps = []
        self.index = 0
        self.deadline = 0.0
        self.text = None
        self.text_index = 0
        self.running = False
        self.last_error = None

    def start(self, steps):
        self.cancel()
        self.steps = list(steps or [])[:MAX_STEPS]
        self.index = 0
        self.deadline = 0.0
        self.text = None
        self.text_index = 0
        self.running = bool(self.steps)
        self.last_error = None

    def release_all(self):
        try:
            self.macropad.keyboard.release_all()
        except Exception:
            pass
        try:
            self.macropad.mouse.release_all()
        except Exception:
            pass

    def cancel(self):
        self.running = False
        self.steps = []
        self.text = None
        self.release_all()

    def _finish_step(self):
        self.index += 1
        if self.index >= len(self.steps):
            self.running = False
            self.release_all()

    def tick(self):
        if not self.running:
            return False
        now = self.monotonic()
        if now < self.deadline:
            return True
        try:
            if self.text is not None:
                if self.text_index < len(self.text):
                    self.macropad.keyboard_layout.write(self.text[self.text_index])
                    self.text_index += 1
                    self.deadline = now + 0.005
                    return True
                self.text = None
                self._finish_step()
                return self.running

            step = self.steps[self.index]
            step_type = step.get("type")
            if step_type == "delay":
                self.deadline = now + (clamp(step.get("ms", 0), 0, MAX_DELAY_MS, 0) / 1000.0)
                self._finish_step()
            elif step_type == "hotkey":
                codes = resolve_keycodes(step.get("keys", []), self.macropad.Keycode)
                self.macropad.keyboard.send(*codes)
                self._finish_step()
            elif step_type == "text":
                self.text = str(step.get("text", ""))[:MAX_TEXT]
                self.text_index = 0
                if not self.text:
                    self.text = None
                    self._finish_step()
            elif step_type == "consumer":
                code = getattr(self.macropad.ConsumerControlCode, str(step.get("code", "")).upper())
                self.macropad.consumer_control.send(code)
                self._finish_step()
            elif step_type == "mouse":
                if step.get("action") == "click":
                    button = getattr(self.macropad.Mouse, str(step.get("button", "LEFT_BUTTON")).upper())
                    self.macropad.mouse.click(button)
                else:
                    self.macropad.mouse.move(
                        x=clamp(step.get("x", 0), -127, 127, 0),
                        y=clamp(step.get("y", 0), -127, 127, 0),
                        wheel=clamp(step.get("wheel", 0), -127, 127, 0),
                    )
                self._finish_step()
            else:
                self._finish_step()
        except Exception as exc:
            self.last_error = str(exc)
            self.cancel()
        return self.running
