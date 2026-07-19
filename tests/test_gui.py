from macropad_configurator.main_window import MainWindow
from macropad_configurator.widgets import StepDialog
from PySide6.QtCore import QModelIndex
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QCheckBox, QComboBox, QLineEdit, QListWidget, QPushButton, QSlider


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
    window.requires_confirmation_checkbox.setChecked(True)
    assert window.current_profile()["keys"][3]["requires_confirmation"] is True
    window.unset_current_control()
    assert window.current_profile()["keys"][3]["name"] == "Unassigned"
    assert window.current_profile()["keys"][3]["oled_label"] == ""
    assert window.current_profile()["keys"][3]["steps"] == []
    window.undo()
    assert window.current_profile()["keys"][3]["name"] == "Build"
    window.redo()
    assert window.current_profile()["keys"][3]["name"] == "Unassigned"
    window.dirty = False


def test_file_menu_exit_action_closes_window(qtbot, monkeypatch):
    monkeypatch.setattr(MainWindow, "_load_local", lambda self: __import__("macropad_configurator.models", fromlist=["new_project"]).new_project())
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    assert window.file_menu.menuAction() in window.menuBar().actions()
    assert window.exit_action in window.file_menu.actions()
    assert window.exit_action.shortcut() == QKeySequence(QKeySequence.StandardKey.Quit)

    window.exit_action.trigger()
    assert not window.isVisible()


def test_main_window_controls_have_descriptive_example_tooltips(qtbot, monkeypatch):
    monkeypatch.setattr(MainWindow, "_load_local", lambda self: __import__("macropad_configurator.models", fromlist=["new_project"]).new_project())
    window = MainWindow()
    qtbot.addWidget(window)

    controls = []
    for widget_type in (QPushButton, QCheckBox, QComboBox, QLineEdit, QListWidget, QSlider):
        controls.extend(window.findChildren(widget_type))
    controls.extend(window.key_buttons)
    controls.append(window.encoder_button)

    for control in controls:
        assert "Example:" in control.toolTip(), (
            f"{type(control).__name__} {getattr(control, 'text', lambda: '')()!r} "
            "is missing a description-and-example tooltip"
        )

    for action in window.findChildren(QAction):
        if action.text() and not action.isSeparator():
            assert "Example:" in action.toolTip(), (
                f"Action {action.text()!r} is missing a description-and-example tooltip"
            )


def test_step_dialog_controls_have_descriptive_example_tooltips(qtbot):
    dialog = StepDialog()
    qtbot.addWidget(dialog)
    controls = [
        dialog.type_combo,
        dialog.preset_combo,
        dialog.hotkey_edit,
        dialog.hotkey_key_combo,
        dialog.text_edit,
        dialog.consumer_combo,
        dialog.mouse_action_combo,
        dialog.mouse_button_combo,
        dialog.mouse_x,
        dialog.mouse_y,
        dialog.mouse_wheel,
        dialog.delay_spin,
    ]
    controls.extend(dialog.findChildren(QPushButton))

    for control in controls:
        assert "Example:" in control.toolTip(), (
            f"{type(control).__name__} {getattr(control, 'text', lambda: '')()!r} "
            "is missing a description-and-example tooltip"
        )


def test_encoder_has_no_rgb_controls(qtbot, monkeypatch):
    monkeypatch.setattr(MainWindow, "_load_local", lambda self: __import__("macropad_configurator.models", fromlist=["new_project"]).new_project())
    window = MainWindow()
    qtbot.addWidget(window)
    window.select_control(12)
    assert not window.lighting_enabled_checkbox.isEnabled()
    assert not window.idle_color_button.isEnabled()
    assert not window.pressed_color_button.isEnabled()
    assert not window.requires_confirmation_checkbox.isEnabled()
    window.dirty = False


def test_subprofiles_are_selectable_and_reserve_encoder(qtbot, monkeypatch):
    def project_with_subprofiles(self):
        models = __import__("macropad_configurator.models", fromlist=["new_project", "normalize_subprofile"])
        project = models.new_project()
        profile = project["profiles"][0]
        profile["subprofile_name"] = "Primary"
        profile["subprofiles"].append(
            models.normalize_subprofile({"name": "Second"}, 0, profile)
        )
        return project

    monkeypatch.setattr(MainWindow, "_load_local", project_with_subprofiles)
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.subprofile_list.count() == 2
    assert not window.encoder_button.isEnabled()
    window.subprofile_list.setCurrentRow(1)
    assert window.current_layout()["name"] == "Second"
    window.control_name_edit.setText("Second action")
    window._control_name_changed("Second action")
    assert window.current_profile()["subprofiles"][0]["keys"][0]["name"] == "Second action"
    window.duplicate_subprofile()
    assert window.subprofile_list.count() == 3
    assert window.current_layout()["name"] == "Second Copy"
    window.move_subprofile(-1)
    assert window.subprofile_index == 1
    assert window.current_layout()["name"] == "Second Copy"
    window.move_subprofile(-1)
    assert window.subprofile_index == 0
    assert window.current_profile()["subprofile_name"] == "Second Copy"
    window.subprofile_list.setCurrentRow(1)
    window.delete_subprofile()
    assert window.subprofile_list.count() == 2
    window.dirty = False


def test_subprofile_screen_list_drag_changes_encoder_press_order(qtbot, monkeypatch):
    def project_with_three_screens(self):
        models = __import__(
            "macropad_configurator.models",
            fromlist=["new_project", "normalize_subprofile"],
        )
        project = models.new_project()
        profile = project["profiles"][0]
        profile["subprofile_name"] = "Primary"
        profile["keys"][0]["name"] = "Primary action"
        second = models.normalize_subprofile({"name": "Second"}, 0, profile)
        second["keys"][0]["name"] = "Second action"
        third = models.normalize_subprofile({"name": "Third"}, 1, profile)
        third["keys"][0]["name"] = "Third action"
        profile["subprofiles"] = [second, third]
        return project

    monkeypatch.setattr(MainWindow, "_load_local", project_with_three_screens)
    window = MainWindow()
    qtbot.addWidget(window)

    moved = window.subprofile_list.model().moveRows(
        QModelIndex(),
        2,
        1,
        QModelIndex(),
        0,
    )

    assert moved
    profile = window.current_profile()
    assert [profile["subprofile_name"]] + [
        item["name"] for item in profile["subprofiles"]
    ] == ["Third", "Primary", "Second"]
    assert profile["keys"][0]["name"] == "Third action"
    assert "encoder press order" in window.statusBar().currentMessage()
    window.dirty = False


def test_profile_screen_list_drag_changes_encoder_turn_order(qtbot, monkeypatch):
    def project_with_three_profiles(self):
        models = __import__(
            "macropad_configurator.models",
            fromlist=["new_project", "new_profile"],
        )
        project = models.new_project()
        project["profiles"].extend(
            [
                models.new_profile("second", "Second"),
                models.new_profile("third", "Third"),
            ]
        )
        return project

    monkeypatch.setattr(MainWindow, "_load_local", project_with_three_profiles)
    window = MainWindow()
    qtbot.addWidget(window)

    moved = window.profile_list.model().moveRows(
        QModelIndex(),
        2,
        1,
        QModelIndex(),
        0,
    )

    assert moved
    assert [profile["id"] for profile in window.project["profiles"]] == [
        "third",
        "editing",
        "second",
    ]
    assert "encoder turn order" in window.statusBar().currentMessage()
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


def test_drag_signal_moves_key_and_shifts_intervening_assignments(qtbot, monkeypatch):
    monkeypatch.setattr(
        MainWindow,
        "_load_local",
        lambda self: __import__(
            "macropad_configurator.models",
            fromlist=["new_project"],
        ).new_project(),
    )
    window = MainWindow()
    qtbot.addWidget(window)
    keys = window.current_layout()["keys"]
    original_names = [key["name"] for key in keys[:4]]

    window.key_buttons[0].moveRequested.emit(0, 3)

    assert [key["name"] for key in keys[:4]] == original_names[1:] + original_names[:1]
    assert window.selected_control == 3
    assert window.selected_controls == {3}
    assert "Moved key 1 to position 4" in window.statusBar().currentMessage()
    window.undo()
    assert [key["name"] for key in window.current_layout()["keys"][:4]] == original_names
    window.dirty = False


def test_action_preset_picker(qtbot):
    dialog = StepDialog(layout_name="de")
    qtbot.addWidget(dialog)
    dialog.preset_combo.setCurrentText("Copy")
    assert dialog.step() == {"type": "hotkey", "keys": ["CONTROL", "C"]}
