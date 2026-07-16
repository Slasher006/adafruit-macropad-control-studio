from macropad_configurator.main_window import MainWindow
from macropad_configurator.widgets import StepDialog


def test_main_window_profile_and_key_editing(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr(MainWindow, "_load_local", lambda self: __import__("macropad_configurator.models", fromlist=["new_project"]).new_project())
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.profile_list.count() == 1
    assert len(window.key_buttons) == 12

    window.add_profile()
    assert window.profile_list.count() == 2
    window.select_control(3)
    window.control_name_edit.setText("Build")
    window._control_name_changed("Build")
    window.oled_label_edit.setText("BUILD")
    window._oled_label_changed("BUILD")
    window.brightness_slider.setValue(42)
    assert window.current_profile()["keys"][3]["name"] == "Build"
    assert window.current_profile()["keys"][3]["oled_label"] == "BUILD"
    assert window.current_profile()["brightness"] == 42
    window.lighting_enabled_checkbox.setChecked(False)
    assert window.current_profile()["keys"][3]["lighting_enabled"] is False
    assert not window.idle_color_button.isEnabled()
    window.unset_current_control()
    assert window.current_profile()["keys"][3]["name"] == "Unassigned"
    assert window.current_profile()["keys"][3]["oled_label"] == ""
    assert window.current_profile()["keys"][3]["steps"] == []
    window.undo()
    assert window.current_profile()["keys"][3]["name"] == "Build"
    window.redo()
    assert window.current_profile()["keys"][3]["name"] == "Unassigned"
    window.dirty = False


def test_encoder_has_no_rgb_controls(qtbot, monkeypatch):
    monkeypatch.setattr(MainWindow, "_load_local", lambda self: __import__("macropad_configurator.models", fromlist=["new_project"]).new_project())
    window = MainWindow()
    qtbot.addWidget(window)
    window.select_control(12)
    assert not window.lighting_enabled_checkbox.isEnabled()
    assert not window.idle_color_button.isEnabled()
    assert not window.pressed_color_button.isEnabled()
    window.dirty = False


def test_copy_swap_multiselect_and_palette(qtbot, monkeypatch):
    monkeypatch.setattr(MainWindow, "_load_local", lambda self: __import__("macropad_configurator.models", fromlist=["new_project"]).new_project())
    window = MainWindow()
    qtbot.addWidget(window)
    window.select_control(0)
    window.copy_control()
    window.select_control(1)
    window.paste_control()
    assert window.current_profile()["keys"][1]["name"] == "Copy"
    window.swap_controls(1, 2)
    assert window.current_profile()["keys"][2]["name"] == "Copy"
    window.selected_control = 1
    window.selected_controls = {1, 2}
    window._lighting_enabled_changed(False)
    assert not window.current_profile()["keys"][1]["lighting_enabled"]
    assert not window.current_profile()["keys"][2]["lighting_enabled"]
    window.palette_combo.setCurrentText("#000000")
    window.palette_scope_combo.setCurrentIndex(2)
    window.apply_palette_color("idle_color")
    assert all(key["idle_color"] == "#000000" for key in window.current_profile()["keys"])
    window.dirty = False


def test_action_preset_picker(qtbot):
    dialog = StepDialog(layout_name="de")
    qtbot.addWidget(dialog)
    dialog.preset_combo.setCurrentText("Copy")
    assert dialog.step() == {"type": "hotkey", "keys": ["CONTROL", "C"]}
