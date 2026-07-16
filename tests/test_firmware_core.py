from device.macropad_core import EncoderStepper, MacroRunner, color_tuple, normalize_index, normalize_profile, resolve_keycodes


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


def test_profile_fallback_and_color_conversion():
    profile = normalize_profile({"id": "x", "keys": [{"lighting_enabled": False}]}, "x")
    assert profile["brightness"] == 5
    assert len(profile["keys"]) == 12
    assert profile["keys"][0]["lighting_enabled"] is False
    assert profile["keys"][1]["lighting_enabled"] is True
    assert color_tuple("#112233") == (17, 34, 51)


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
