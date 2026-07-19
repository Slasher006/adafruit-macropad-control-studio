from device.macropad_core import (
    EncoderStepper,
    MacroRunner,
    PersistentChoice,
    PersistentToggle,
    SubprofileStore,
    accepts_automatic_profile,
    automatic_subprofile,
    color_tuple,
    filter_profile_entries,
    find_subprofile_index,
    normalize_index,
    next_deck_role,
    normalize_profile,
    normalize_shared_key_profile,
    resolve_keycodes,
)


class FakeKeycode:
    CONTROL = 1
    C = 2
    Z = 3
    GUI = 4


class FakeConsumerCodes:
    MUTE = 20


class FakeMouseCodes:
    LEFT_BUTTON = 1


class FakeKeyboard:
    def __init__(self):
        self.sent = []
        self.released = 0

    def send(self, *codes):
        self.sent.append(codes)

    def release_all(self):
        self.released += 1


class FakeLayout:
    def __init__(self):
        self.text = ""

    def write(self, text):
        self.text += text


class FakeConsumer:
    def __init__(self):
        self.sent = []

    def send(self, code):
        self.sent.append(code)


class FakeMouse:
    def __init__(self):
        self.clicks = []
        self.moves = []
        self.released = 0

    def click(self, button):
        self.clicks.append(button)

    def move(self, **values):
        self.moves.append(values)

    def release_all(self):
        self.released += 1


class FakePad:
    Keycode = FakeKeycode
    ConsumerControlCode = FakeConsumerCodes
    Mouse = FakeMouseCodes

    def __init__(self):
        self.keyboard = FakeKeyboard()
        self.keyboard_layout = FakeLayout()
        self.consumer_control = FakeConsumer()
        self.mouse = FakeMouse()


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def run_until_done(runner, clock, limit=200):
    for _ in range(limit):
        runner.tick()
        clock.now += 0.01
        if not runner.running:
            return
    raise AssertionError("runner did not finish")


def test_macro_runner_executes_sequence_and_releases_hid():
    pad = FakePad()
    clock = Clock()
    runner = MacroRunner(pad, clock)
    runner.start(
        [
            {"type": "hotkey", "keys": ["CONTROL", "C"]},
            {"type": "text", "text": "Hi"},
            {"type": "consumer", "code": "MUTE"},
            {"type": "mouse", "action": "click", "button": "LEFT_BUTTON"},
            {"type": "delay", "ms": 20},
            {"type": "mouse", "action": "move", "x": 3, "y": -4, "wheel": 1},
        ]
    )
    run_until_done(runner, clock)
    assert pad.keyboard.sent == [(1, 2)]
    assert pad.keyboard_layout.text == "Hi"
    assert pad.consumer_control.sent == [20]
    assert pad.mouse.clicks == [1]
    assert pad.mouse.moves == [{"x": 3, "y": -4, "wheel": 1}]
    assert pad.keyboard.released >= 1
    assert pad.mouse.released >= 1


def test_macro_runner_cancel_releases_and_stops_text():
    pad = FakePad()
    clock = Clock()
    runner = MacroRunner(pad, clock)
    runner.start([{"type": "text", "text": "abcdef"}])
    runner.tick()
    runner.tick()
    runner.cancel()
    assert not runner.running
    assert len(pad.keyboard_layout.text) < 6
    assert pad.keyboard.released >= 1


def test_invalid_key_cancels_safely():
    pad = FakePad()
    clock = Clock()
    runner = MacroRunner(pad, clock)
    runner.start([{"type": "hotkey", "keys": ["NOT_A_KEY"]}])
    runner.tick()
    assert not runner.running
    assert "Unknown key" in runner.last_error
    assert pad.keyboard.released >= 1


def test_key_aliases_and_profile_index():
    assert resolve_keycodes(["ctrl", "cmd"], FakeKeycode) == [1, 4]
    assert normalize_index({"profiles": [{"id": "one", "name": "One"}, {"id": "one"}, {"id": "bad id"}]}) == [
        {"id": "one", "name": "One", "file": "one.json"}
    ]


def test_profile_filter_preserves_library_order_and_falls_back_safely():
    entries = [
        {"id": "editing"},
        {"id": "firefox"},
        {"id": "i3wm"},
        {"id": "options"},
    ]
    assert [
        entry["id"]
        for entry in filter_profile_entries(
            entries,
            ["options", "firefox", "i3wm"],
        )
    ] == ["firefox", "i3wm", "options"]
    assert filter_profile_entries(entries, []) == entries
    assert filter_profile_entries(entries, ["missing"]) == entries


def test_profile_fallback_and_color_conversion():
    profile = normalize_profile({"id": "x", "keys": [{"lighting_enabled": False}]}, "x")
    assert profile["brightness"] == 5
    assert len(profile["keys"]) == 12
    assert profile["keys"][0]["lighting_enabled"] is False
    assert profile["keys"][1]["lighting_enabled"] is True
    assert color_tuple("#112233") == (17, 34, 51)


def test_profile_normalizes_additional_subprofiles():
    profile = normalize_profile(
        {
            "id": "work",
            "subprofile_name": "Windows",
            "subprofiles": [
                {
                    "name": "Workspaces",
                    "brightness": 9,
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
    )
    assert profile["subprofile_name"] == "Windows"
    assert len(profile["subprofiles"]) == 1
    assert profile["subprofiles"][0]["name"] == "Workspaces"
    assert profile["subprofiles"][0]["brightness"] == 9
    assert len(profile["subprofiles"][0]["keys"]) == 12
    assert profile["subprofiles"][0]["keys"][0]["oled_label"] == "WS-1"


def test_shared_key_profile_keeps_eight_named_screens_in_one_key_array():
    profile = normalize_shared_key_profile(
        {
            "id": "live-controls",
            "subprofile_name": "Status",
            "keys": [],
            "subprofiles": [
                {"name": name, "keys": []}
                for name in (
                    "Programs",
                    "App Audio",
                    "Windows",
                    "Clipboard",
                    "Focus",
                    "System",
                    "Jobs",
                )
            ],
        }
    )
    assert len(profile["keys"]) == 12
    assert len(profile["subprofiles"]) == 7
    assert all(item["keys"] is profile["keys"] for item in profile["subprofiles"])


def test_subprofile_store_keeps_an_independent_selection_per_parent_profile():
    nvm = bytearray([255] * 40)
    store = SubprofileStore(nvm)
    assert store.load(2, 3) == 0
    assert store.save(2, 1)
    assert store.save(5, 2)
    assert store.load(2, 3) == 1
    assert store.load(5, 3) == 2
    assert store.load(2, 1) == 0


def test_persistent_toggle_uses_default_and_saves_both_states():
    nvm = bytearray([255] * 40)
    toggle = PersistentToggle(nvm, 33, True)
    assert toggle.load() is True
    assert toggle.save(False)
    assert toggle.load() is False
    assert toggle.save(True)
    assert toggle.load() is True


def test_persistent_deck_role_keeps_old_boolean_values_and_adds_profile_mode():
    nvm = bytearray([255] * 40)
    roles = PersistentChoice(nvm, 33, ("manual", "app", "profile"), "app")
    assert roles.load() == "app"
    nvm[33] = 0
    assert roles.load() == "manual"
    nvm[33] = 1
    assert roles.load() == "app"
    assert roles.save("profile")
    assert nvm[33] == 2
    assert roles.load() == "profile"
    assert not roles.save("missing")


def test_deck_role_cycle_and_automatic_layout_behavior():
    assert next_deck_role("manual") == "profile"
    assert next_deck_role("profile") == "app"
    assert next_deck_role("app") == "manual"
    assert not accepts_automatic_profile("manual")
    assert accepts_automatic_profile("profile")
    assert accepts_automatic_profile("app")
    assert automatic_subprofile("manual", "In App") is None
    assert automatic_subprofile("profile", "In App") is None
    assert automatic_subprofile("app", "In App") == "In App"


def test_find_subprofile_index_resolves_context_without_touching_storage():
    profile = {
        "subprofile_name": "General",
        "subprofiles": [
            {"name": "Navigation"},
            {"name": "In App"},
        ],
    }
    assert find_subprofile_index(profile, "General") == 0
    assert find_subprofile_index(profile, "in app") == 2
    assert find_subprofile_index(profile, 1) == 1
    assert find_subprofile_index(profile, "Missing") is None
    assert find_subprofile_index(profile, 5) is None


def test_encoder_stepper_collapses_one_detent_and_keeps_direction():
    stepper = EncoderStepper(position=0, guard_seconds=0.075)

    assert stepper.update(1, 1.000) == 1
    assert stepper.update(2, 1.005) == 0
    assert stepper.update(3, 1.050) == 0
    assert stepper.update(4, 1.080) == 1
    assert stepper.update(3, 1.160) == -1
    assert stepper.update(2, 1.165) == 0

    stepper.suppress(0, 2.000)
    assert stepper.update(0, 2.050) == 0
    assert stepper.update(1, 2.050) == 0
    assert stepper.update(2, 2.080) == 1
