from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from PySide6.QtCore import QSettings, QStandardPaths, QTimer, Qt
from PySide6.QtGui import QAction, QColor, QCloseEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QColorDialog,
)

from .device_io import (
    DeviceError,
    DeviceInfo,
    clear_preview,
    backup_device,
    compare_projects,
    device_health,
    discover_devices,
    export_library_archive,
    import_library_archive,
    list_device_backups,
    preview_lighting,
    read_device_project,
    repair_firmware,
    send_command,
    sync_project,
)
from . import __version__
from .models import (
    DEFAULT_BRIGHTNESS,
    MAX_PROFILES,
    duplicate_profile,
    empty_control,
    load_json,
    new_profile,
    new_project,
    normalize_color,
    normalize_profile,
    normalize_project,
    normalize_control,
    profile_template,
    save_json,
    step_summary,
    unique_id,
    validate_project,
)
from .widgets import MacroKeyButton, OledPreview, StepDialog


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"Adafruit MacroPad Configurator {__version__}")
        self.resize(1320, 820)
        self.setMinimumSize(1050, 680)
        data_root = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))
        self.local_path = data_root / "library.json"
        self.backup_root = data_root / "backups"
        self.settings = QSettings()
        self.project = self._load_local()
        self.devices: list[DeviceInfo] = []
        self.selected_control = 0
        self.selected_controls: set[int] = {0}
        self.loading = False
        self.dirty = False
        self.unsynced = False
        self.preview_device: DeviceInfo | None = None
        self.key_buttons: list[MacroKeyButton] = []
        self.control_clipboard: dict[str, Any] | None = None
        self.undo_stack: list[dict[str, Any]] = []
        self.redo_stack: list[dict[str, Any]] = []
        self.history_state = copy.deepcopy(self.project)
        aliases = self.settings.value("device_aliases", {})
        self.device_aliases = aliases if isinstance(aliases, dict) else {}
        palette = self.settings.value("palette", [])
        self.palette = [str(color) for color in palette] if isinstance(palette, list) else []
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.setInterval(750)
        self.autosave_timer.timeout.connect(self.save_local)

        self._build_ui()
        self._refresh_profile_list(0)
        self.refresh_devices()
        self._update_state_status()
        self.statusBar().showMessage("Ready")

    def _load_local(self) -> dict[str, Any]:
        try:
            return normalize_project(load_json(self.local_path))
        except (OSError, ValueError):
            return new_project()

    def _build_ui(self) -> None:
        self._build_toolbar()
        self._build_edit_toolbar()
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_profile_panel())
        splitter.addWidget(self._build_pad_panel())
        splitter.addWidget(self._build_inspector())
        splitter.setSizes([240, 580, 500])
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 1)
        self.setCentralWidget(splitter)

    def _build_toolbar(self) -> None:
        toolbar = self.addToolBar("Device")
        toolbar.setMovable(False)
        toolbar.addWidget(QLabel(" Device: "))
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(300)
        toolbar.addWidget(self.device_combo)
        for label, slot in (
            ("Refresh", self.refresh_devices),
            ("Import Device", self.import_device),
            ("Preview RGB", self.preview_rgb),
            ("Clear Preview", self.clear_rgb_preview),
            ("Sync Device", self.sync_device),
            ("Save Local", self.save_local),
        ):
            action = QAction(label, self)
            action.triggered.connect(slot)
            toolbar.addAction(action)
        toolbar.addSeparator()
        toolbar.addWidget(QLabel(" Layout: "))
        self.layout_combo = QComboBox()
        self.layout_combo.addItem("US", "us")
        self.layout_combo.addItem("German", "de")
        self.layout_combo.currentIndexChanged.connect(self._layout_changed)
        toolbar.addWidget(self.layout_combo)
        toolbar.addSeparator()
        self.state_label = QLabel(" Local saved ")
        toolbar.addWidget(self.state_label)

    def _build_edit_toolbar(self) -> None:
        toolbar = self.addToolBar("Editing")
        toolbar.setMovable(False)
        edit_menu = self.menuBar().addMenu("&Edit")
        library_menu = self.menuBar().addMenu("&Library")
        device_menu = self.menuBar().addMenu("&Device")
        actions = (
            ("Undo", self.undo, "Ctrl+Z"),
            ("Redo", self.redo, "Ctrl+Shift+Z"),
            ("Copy control", self.copy_control, "Ctrl+Alt+C"),
            ("Paste control", self.paste_control, "Ctrl+Alt+V"),
            ("Swap…", self.swap_control_dialog, ""),
            ("Compare", self.compare_with_device, ""),
            ("Backups", self.restore_backup, ""),
            ("Export Library", self.export_library, ""),
            ("Import Library", self.import_library, ""),
            ("Device Health", self.show_device_health, ""),
            ("Repair Firmware", self.repair_device_firmware, ""),
            ("Name Device", self.name_device, ""),
        )
        for label, slot, shortcut in actions:
            action = QAction(label, self)
            action.triggered.connect(slot)
            if shortcut:
                action.setShortcut(shortcut)
            toolbar.addAction(action)
            if label in {"Undo", "Redo", "Copy control", "Paste control", "Swap…"}:
                edit_menu.addAction(action)
            elif label in {"Compare", "Backups", "Export Library", "Import Library"}:
                library_menu.addAction(action)
            else:
                device_menu.addAction(action)

    def _build_profile_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        title = QLabel("Profiles")
        title.setStyleSheet("font-size: 18px; font-weight: 600")
        layout.addWidget(title)
        self.profile_list = QListWidget()
        self.profile_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.profile_list.currentRowChanged.connect(self._profile_selected)
        self.profile_list.model().rowsMoved.connect(self._profiles_reordered)
        layout.addWidget(self.profile_list, 1)
        buttons = QGridLayout()
        for index, (label, slot) in enumerate(
            (
                ("Add", self.add_profile),
                ("Duplicate", self.duplicate_current_profile),
                ("Delete", self.delete_profile),
                ("Up", lambda: self.move_profile(-1)),
                ("Down", lambda: self.move_profile(1)),
                ("Import…", self.import_profile),
                ("Export…", self.export_profile),
                ("Template…", self.add_profile_from_template),
                ("Clear profile", self.clear_current_profile),
                ("Reset lights", self.reset_profile_lighting),
            )
        ):
            button = QPushButton(label)
            button.clicked.connect(slot)
            buttons.addWidget(button, index // 2, index % 2)
        layout.addLayout(buttons)
        return panel

    def _build_pad_panel(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        layout = QVBoxLayout(body)

        settings = QGroupBox("Active profile")
        form = QFormLayout(settings)
        self.profile_name_edit = QLineEdit()
        self.profile_name_edit.setMaxLength(24)
        self.profile_name_edit.textEdited.connect(self._profile_name_changed)
        self.profile_icon_edit = QLineEdit()
        self.profile_icon_edit.setMaxLength(2)
        self.profile_icon_edit.setPlaceholderText("2 chars")
        self.profile_icon_edit.textEdited.connect(self._profile_icon_changed)
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setRange(0, 100)
        self.brightness_slider.valueChanged.connect(self._brightness_changed)
        self.brightness_label = QLabel(f"{DEFAULT_BRIGHTNESS}%")
        brightness_row = QHBoxLayout()
        brightness_row.addWidget(self.brightness_slider, 1)
        brightness_row.addWidget(self.brightness_label)
        form.addRow("Name", self.profile_name_edit)
        form.addRow("OLED icon", self.profile_icon_edit)
        form.addRow("Light intensity", brightness_row)
        layout.addWidget(settings)

        self.oled = OledPreview()
        layout.addWidget(self.oled)

        keys_box = QGroupBox("MacroPad")
        keys = QGridLayout(keys_box)
        for index in range(12):
            button = MacroKeyButton(index)
            button.setCheckable(True)
            button.setMinimumSize(115, 78)
            button.clicked.connect(lambda checked=False, number=index: self.select_control(number))
            button.swapRequested.connect(self.swap_controls)
            keys.addWidget(button, index // 3, index % 3)
            self.key_buttons.append(button)
        self.encoder_button = QToolButton()
        self.encoder_button.setCheckable(True)
        self.encoder_button.setMinimumHeight(55)
        self.encoder_button.clicked.connect(lambda: self.select_control(12))
        keys.addWidget(self.encoder_button, 4, 0, 1, 3)
        layout.addWidget(keys_box)
        layout.addStretch()
        scroll.setWidget(body)
        return scroll

    def _build_inspector(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        layout = QVBoxLayout(body)
        title = QLabel("Control editor")
        title.setStyleSheet("font-size: 18px; font-weight: 600")
        layout.addWidget(title)
        self.selection_label = QLabel("1 key selected")
        layout.addWidget(self.selection_label)

        fields = QGroupBox("Label")
        form = QFormLayout(fields)
        self.control_name_edit = QLineEdit()
        self.control_name_edit.setMaxLength(24)
        self.control_name_edit.textEdited.connect(self._control_name_changed)
        self.oled_label_edit = QLineEdit()
        self.oled_label_edit.setMaxLength(6)
        self.oled_label_edit.textEdited.connect(self._oled_label_changed)
        form.addRow("Name", self.control_name_edit)
        form.addRow("OLED label", self.oled_label_edit)
        self.unset_control_button = QPushButton("Unset key")
        self.unset_control_button.clicked.connect(self.unset_current_control)
        form.addRow("Assignment", self.unset_control_button)
        layout.addWidget(fields)

        colors = QGroupBox("RGB")
        color_layout = QFormLayout(colors)
        self.lighting_enabled_checkbox = QCheckBox("Illuminate this key")
        self.lighting_enabled_checkbox.toggled.connect(self._lighting_enabled_changed)
        self.idle_color_button = QPushButton()
        self.idle_color_button.clicked.connect(lambda: self.choose_color("idle_color"))
        self.pressed_color_button = QPushButton()
        self.pressed_color_button.clicked.connect(lambda: self.choose_color("pressed_color"))
        color_layout.addRow("Lighting", self.lighting_enabled_checkbox)
        color_layout.addRow("Idle color", self.idle_color_button)
        color_layout.addRow("Pressed color", self.pressed_color_button)
        self.palette_combo = QComboBox()
        self.palette_scope_combo = QComboBox()
        self.palette_scope_combo.addItems(["Selected keys", "Current row", "All keys"])
        palette_buttons = QHBoxLayout()
        for label, slot in (
            ("Idle", lambda: self.apply_palette_color("idle_color")),
            ("Pressed", lambda: self.apply_palette_color("pressed_color")),
            ("Save current", self.save_current_palette_color),
        ):
            button = QPushButton(label)
            button.clicked.connect(slot)
            palette_buttons.addWidget(button)
        color_layout.addRow("Palette", self.palette_combo)
        color_layout.addRow("Apply to", self.palette_scope_combo)
        color_layout.addRow("Palette action", palette_buttons)
        layout.addWidget(colors)

        actions = QGroupBox("Action sequence")
        action_layout = QVBoxLayout(actions)
        self.step_list = QListWidget()
        self.step_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.step_list.model().rowsMoved.connect(self._steps_reordered)
        self.step_list.itemDoubleClicked.connect(lambda: self.edit_step())
        action_layout.addWidget(self.step_list, 1)
        action_buttons = QGridLayout()
        for index, (label, slot) in enumerate(
            (
                ("Add step", self.add_step),
                ("Edit", self.edit_step),
                ("Remove", self.remove_step),
                ("Move up", lambda: self.move_step(-1)),
                ("Move down", lambda: self.move_step(1)),
                ("Safe preview", self.preview_selected_action),
                ("Run on device", self.test_selected_action),
            )
        ):
            button = QPushButton(label)
            button.clicked.connect(slot)
            action_buttons.addWidget(button, index // 2, index % 2)
        action_layout.addLayout(action_buttons)
        layout.addWidget(actions, 1)
        layout.addStretch()
        scroll.setWidget(body)
        self._refresh_palette()
        return scroll

    def current_profile(self) -> dict[str, Any]:
        row = max(0, self.profile_list.currentRow())
        return self.project["profiles"][row]

    def current_control(self) -> dict[str, Any]:
        profile = self.current_profile()
        return profile["keys"][self.selected_control] if self.selected_control < 12 else profile["encoder_press"]

    def _control_at(self, index: int) -> dict[str, Any]:
        return self.current_profile()["keys"][index] if index < 12 else self.current_profile()["encoder_press"]

    def undo(self) -> None:
        if not self.undo_stack:
            self.statusBar().showMessage("Nothing to undo", 2000)
            return
        self.redo_stack.append(copy.deepcopy(self.project))
        self.project = self.undo_stack.pop()
        self.history_state = copy.deepcopy(self.project)
        self.dirty = True
        self.unsynced = True
        self._refresh_profile_list(min(self.profile_list.currentRow(), len(self.project["profiles"]) - 1))
        self.autosave_timer.start()
        self._update_state_status("Undid last change")

    def redo(self) -> None:
        if not self.redo_stack:
            self.statusBar().showMessage("Nothing to redo", 2000)
            return
        self.undo_stack.append(copy.deepcopy(self.project))
        self.project = self.redo_stack.pop()
        self.history_state = copy.deepcopy(self.project)
        self.dirty = True
        self.unsynced = True
        self._refresh_profile_list(min(self.profile_list.currentRow(), len(self.project["profiles"]) - 1))
        self.autosave_timer.start()
        self._update_state_status("Redid change")

    def copy_control(self) -> None:
        self.control_clipboard = copy.deepcopy(self.current_control())
        self.statusBar().showMessage(f"Copied {self.current_control()['name']}", 2500)

    def paste_control(self) -> None:
        if self.control_clipboard is None:
            self.statusBar().showMessage("No copied control", 2500)
            return
        targets = self.selected_controls if self.selected_control < 12 else {12}
        for index in targets:
            value = normalize_control(self.control_clipboard, index, index < 12)
            if index < 12:
                self.current_profile()["keys"][index] = value
            else:
                self.current_profile()["encoder_press"] = value
        self._refresh_profile_editor()
        self._mark_dirty(f"Pasted control to {len(targets)} destination(s)")

    def swap_controls(self, source: int, target: int) -> None:
        if source == target or source not in range(13) or target not in range(13):
            return
        source_value = copy.deepcopy(self._control_at(source))
        target_value = copy.deepcopy(self._control_at(target))
        new_source = normalize_control(target_value, source, source < 12)
        new_target = normalize_control(source_value, target, target < 12)
        if source < 12:
            self.current_profile()["keys"][source] = new_source
        else:
            self.current_profile()["encoder_press"] = new_source
        if target < 12:
            self.current_profile()["keys"][target] = new_target
        else:
            self.current_profile()["encoder_press"] = new_target
        self.selected_control = target
        self.selected_controls = {target}
        self._refresh_profile_editor()
        self._mark_dirty("Swapped controls")

    def swap_control_dialog(self) -> None:
        choices = [f"Key {index + 1}" for index in range(12)] + ["Encoder press"]
        choice, accepted = QInputDialog.getItem(self, "Swap control", "Swap selected control with", choices, 0, False)
        if accepted:
            self.swap_controls(self.selected_control, choices.index(choice))

    def _refresh_profile_list(self, selected: int) -> None:
        self.loading = True
        self.profile_list.clear()
        self.profile_list.addItems([profile["name"] for profile in self.project["profiles"]])
        for index, profile in enumerate(self.project["profiles"]):
            self.profile_list.item(index).setData(Qt.ItemDataRole.UserRole, profile["id"])
        self.profile_list.setCurrentRow(max(0, min(selected, len(self.project["profiles"]) - 1)))
        layout = self.project.get("keyboard_layout", "us")
        self.layout_combo.setCurrentIndex(max(0, self.layout_combo.findData(layout)))
        self.loading = False
        self._refresh_profile_editor()

    def _refresh_profile_editor(self) -> None:
        if not self.project["profiles"]:
            return
        profile = self.current_profile()
        self.loading = True
        self.profile_name_edit.setText(profile["name"])
        self.profile_icon_edit.setText(profile.get("icon", ""))
        self.brightness_slider.setValue(profile["brightness"])
        self.brightness_label.setText(f"{profile['brightness']}%")
        self.oled.set_profile(profile)
        for index, button in enumerate(self.key_buttons):
            control = profile["keys"][index]
            button.setText(f"{index + 1}\n{control['name']}")
            color = control["idle_color"] if control.get("lighting_enabled", True) else "#000000"
            button.setStyleSheet(self._key_style(color, self.selected_control == index))
            button.setChecked(index in self.selected_controls)
        self.encoder_button.setText("Encoder press — " + profile["encoder_press"]["name"])
        self.encoder_button.setChecked(12 in self.selected_controls)
        self.loading = False
        self._refresh_control_editor()

    def _refresh_control_editor(self) -> None:
        control = self.current_control()
        self.loading = True
        selected_keys = sorted(index for index in self.selected_controls if index < 12)
        self.selection_label.setText(
            f"{len(selected_keys)} keys selected — lighting and palette changes apply to all"
            if len(selected_keys) > 1
            else ("Encoder press selected" if self.selected_control == 12 else "1 key selected")
        )
        self.control_name_edit.setText(control["name"])
        self.oled_label_edit.setText(control["oled_label"])
        lighting = self.selected_control < 12
        lighting_enabled = lighting and control.get("lighting_enabled", True)
        self.lighting_enabled_checkbox.setEnabled(lighting)
        self.lighting_enabled_checkbox.setChecked(lighting_enabled)
        self.idle_color_button.setEnabled(lighting_enabled)
        self.pressed_color_button.setEnabled(lighting_enabled)
        self.unset_control_button.setText("Unset key" if lighting else "Unset encoder press")
        if lighting:
            self._set_color_button(self.idle_color_button, control["idle_color"])
            self._set_color_button(self.pressed_color_button, control["pressed_color"])
        else:
            self.idle_color_button.setText("Not applicable")
            self.pressed_color_button.setText("Not applicable")
            self.idle_color_button.setStyleSheet("")
            self.pressed_color_button.setStyleSheet("")
        self._refresh_steps()
        self.loading = False

    def _refresh_steps(self, selected: int = -1) -> None:
        self.step_list.clear()
        self.step_list.addItems([step_summary(step) for step in self.current_control()["steps"]])
        if self.step_list.count():
            self.step_list.setCurrentRow(max(0, min(selected, self.step_list.count() - 1)))

    def _key_style(self, color: str, selected: bool) -> str:
        qcolor = QColor(color)
        foreground = "#FFFFFF" if qcolor.lightness() < 130 else "#111111"
        border = "4px solid #FFFFFF" if selected else "2px solid #555555"
        return f"QToolButton {{ background: {color}; color: {foreground}; border: {border}; border-radius: 8px; font-weight: 600; }}"

    def _set_color_button(self, button: QPushButton, color: str) -> None:
        qcolor = QColor(color)
        foreground = "#FFFFFF" if qcolor.lightness() < 130 else "#111111"
        button.setText(color)
        button.setStyleSheet(f"background: {color}; color: {foreground}; font-weight: 600")

    def _mark_dirty(self, message: str = "Local changes not synchronized") -> None:
        if self.loading:
            return
        current = copy.deepcopy(self.project)
        if current != self.history_state:
            self.undo_stack.append(copy.deepcopy(self.history_state))
            self.undo_stack = self.undo_stack[-100:]
            self.redo_stack.clear()
            self.history_state = current
        self.dirty = True
        self.unsynced = True
        self.autosave_timer.start()
        self.statusBar().showMessage(message)
        self._update_state_status()

    def select_control(self, number: int) -> None:
        extend = bool(QApplication.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier)
        if extend and number < 12:
            if number in self.selected_controls and len(self.selected_controls) > 1:
                self.selected_controls.remove(number)
            else:
                self.selected_controls.add(number)
            self.selected_control = number
        else:
            self.selected_controls = {number}
            self.selected_control = number
        self._refresh_profile_editor()

    def _profile_selected(self, row: int) -> None:
        if row >= 0 and not self.loading:
            self.selected_control = min(self.selected_control, 12)
            self.selected_controls = {self.selected_control}
            self._refresh_profile_editor()

    def _profile_name_changed(self, text: str) -> None:
        if self.loading:
            return
        self.current_profile()["name"] = text[:24]
        row = self.profile_list.currentRow()
        self.profile_list.item(row).setText(text)
        self.oled.set_profile(self.current_profile())
        self._mark_dirty()

    def _profile_icon_changed(self, text: str) -> None:
        if self.loading:
            return
        self.current_profile()["icon"] = text[:2]
        self.oled.set_profile(self.current_profile())
        self._mark_dirty()

    def _brightness_changed(self, value: int) -> None:
        self.brightness_label.setText(f"{value}%")
        if not self.loading:
            self.current_profile()["brightness"] = value
            self._mark_dirty()

    def _control_name_changed(self, text: str) -> None:
        if self.loading:
            return
        self.current_control()["name"] = text[:24]
        self._refresh_profile_editor()
        self._mark_dirty()

    def _oled_label_changed(self, text: str) -> None:
        if self.loading:
            return
        self.current_control()["oled_label"] = text[:6]
        self.oled.set_profile(self.current_profile())
        self._mark_dirty()

    def _lighting_enabled_changed(self, enabled: bool) -> None:
        if self.loading or self.selected_control >= 12:
            return
        for index in self._selected_key_indices():
            self.current_profile()["keys"][index]["lighting_enabled"] = enabled
        self._refresh_profile_editor()
        self._mark_dirty("Per-key lighting changed; preview or sync to apply")

    def unset_current_control(self) -> None:
        targets = self.selected_controls if self.selected_control < 12 else {12}
        for index in targets:
            control = self.current_profile()["keys"][index] if index < 12 else self.current_profile()["encoder_press"]
            control["name"] = "Unassigned"
            control["oled_label"] = ""
            control["steps"] = []
        self._refresh_profile_editor()
        self._mark_dirty("Control unset; sync to apply")

    def _selected_key_indices(self) -> list[int]:
        return sorted(index for index in self.selected_controls if 0 <= index < 12)

    def _layout_changed(self) -> None:
        if not self.loading:
            self.project["keyboard_layout"] = self.layout_combo.currentData()
            self._mark_dirty("Keyboard layout changed; sync requires a device reload")

    def choose_color(self, field: str) -> None:
        control = self.current_control()
        if field not in control:
            return
        chosen = QColorDialog.getColor(QColor(control[field]), self, "Choose key color")
        if chosen.isValid():
            color = normalize_color(chosen.name())
            for index in self._selected_key_indices():
                self.current_profile()["keys"][index][field] = color
            self._remember_palette_color(color)
            self._refresh_profile_editor()
            self._mark_dirty()

    def _refresh_palette(self) -> None:
        defaults = ["#0066CC", "#6633CC", "#008866", "#CC6600", "#CC2200", "#FFFFFF", "#000000"]
        colors = []
        for color in self.palette + defaults:
            normalized = normalize_color(color, "")
            if normalized and normalized not in colors:
                colors.append(normalized)
        self.palette = colors[:24]
        if not hasattr(self, "palette_combo"):
            return
        current = self.palette_combo.currentText()
        self.palette_combo.clear()
        for color in self.palette:
            self.palette_combo.addItem(color, color)
            index = self.palette_combo.count() - 1
            self.palette_combo.setItemData(index, QColor(color), Qt.ItemDataRole.DecorationRole)
        self.palette_combo.setCurrentText(current if current in self.palette else self.palette[0])

    def _remember_palette_color(self, color: str) -> None:
        color = normalize_color(color)
        self.palette = [color] + [item for item in self.palette if item != color]
        self.palette = self.palette[:24]
        self.settings.setValue("palette", self.palette)
        self._refresh_palette()

    def save_current_palette_color(self) -> None:
        if self.selected_control < 12:
            self._remember_palette_color(self.current_control()["idle_color"])
            self.statusBar().showMessage("Saved idle color to the palette", 3000)

    def _palette_target_indices(self) -> list[int]:
        scope = self.palette_scope_combo.currentIndex()
        if scope == 2:
            return list(range(12))
        if scope == 1:
            start = (min(self._selected_key_indices() or [self.selected_control]) // 3) * 3
            return list(range(start, min(12, start + 3)))
        return self._selected_key_indices()

    def apply_palette_color(self, field: str) -> None:
        color = self.palette_combo.currentData() or self.palette_combo.currentText()
        color = normalize_color(color)
        targets = self._palette_target_indices()
        if not targets:
            return
        for index in targets:
            self.current_profile()["keys"][index][field] = color
        self._refresh_profile_editor()
        self._mark_dirty(f"Applied {color} to {len(targets)} key(s)")

    def add_profile(self) -> None:
        if len(self.project["profiles"]) >= MAX_PROFILES:
            QMessageBox.warning(self, "Profile limit", f"A maximum of {MAX_PROFILES} profiles is supported.")
            return
        used = {profile["id"] for profile in self.project["profiles"]}
        profile_id = unique_id("new-profile", used)
        self.project["profiles"].append(new_profile(profile_id, "New Profile"))
        self._refresh_profile_list(len(self.project["profiles"]) - 1)
        self._mark_dirty()

    def add_profile_from_template(self) -> None:
        if len(self.project["profiles"]) >= MAX_PROFILES:
            return
        labels = ["Editing", "Media", "Blank"]
        label, accepted = QInputDialog.getItem(self, "Profile template", "Create profile from", labels, 0, False)
        if not accepted:
            return
        used = {profile["id"] for profile in self.project["profiles"]}
        profile_id = unique_id(label.lower(), used)
        self.project["profiles"].append(profile_template(label.lower(), profile_id))
        self._refresh_profile_list(len(self.project["profiles"]) - 1)
        self._mark_dirty(f"Created {label} template")

    def clear_current_profile(self) -> None:
        if QMessageBox.question(
            self,
            "Clear profile?",
            f"Remove every assignment from {self.current_profile()['name']}?",
        ) != QMessageBox.StandardButton.Yes:
            return
        old = self.current_profile()
        blank = profile_template("blank", old["id"], old["name"])
        blank["icon"] = old.get("icon", "")
        blank["brightness"] = old["brightness"]
        row = self.profile_list.currentRow()
        self.project["profiles"][row] = blank
        self.selected_control = 0
        self.selected_controls = {0}
        self._refresh_profile_editor()
        self._mark_dirty("Cleared profile assignments")

    def reset_profile_lighting(self) -> None:
        for index, control in enumerate(self.current_profile()["keys"]):
            defaults = empty_control(index)
            control["lighting_enabled"] = True
            control["idle_color"] = defaults["idle_color"]
            control["pressed_color"] = defaults["pressed_color"]
        self.current_profile()["brightness"] = DEFAULT_BRIGHTNESS
        self._refresh_profile_editor()
        self._mark_dirty("Reset profile lighting")

    def duplicate_current_profile(self) -> None:
        if len(self.project["profiles"]) >= MAX_PROFILES:
            return
        row = self.profile_list.currentRow()
        used = {profile["id"] for profile in self.project["profiles"]}
        self.project["profiles"].insert(row + 1, duplicate_profile(self.current_profile(), used))
        self._refresh_profile_list(row + 1)
        self._mark_dirty()

    def delete_profile(self) -> None:
        if len(self.project["profiles"]) == 1:
            QMessageBox.warning(self, "Cannot delete", "At least one profile is required.")
            return
        row = self.profile_list.currentRow()
        if QMessageBox.question(self, "Delete profile", f"Delete {self.current_profile()['name']}?") == QMessageBox.StandardButton.Yes:
            self.project["profiles"].pop(row)
            self._refresh_profile_list(min(row, len(self.project["profiles"]) - 1))
            self._mark_dirty()

    def move_profile(self, offset: int) -> None:
        row = self.profile_list.currentRow()
        target = row + offset
        if target < 0 or target >= len(self.project["profiles"]):
            return
        self.project["profiles"].insert(target, self.project["profiles"].pop(row))
        self._refresh_profile_list(target)
        self._mark_dirty()

    def _profiles_reordered(self, parent, start, end, destination, row) -> None:
        if self.loading:
            return
        ids = [self.profile_list.item(index).data(Qt.ItemDataRole.UserRole) for index in range(self.profile_list.count())]
        by_id = {profile["id"]: profile for profile in self.project["profiles"]}
        if len(by_id) == len(ids) and all(profile_id in by_id for profile_id in ids):
            self.project["profiles"] = [by_id[profile_id] for profile_id in ids]
            self._mark_dirty()

    def add_step(self) -> None:
        dialog = StepDialog(parent=self, layout_name=self.project["keyboard_layout"])
        if dialog.exec() and (step := dialog.step()):
            self.current_control()["steps"].append(step)
            self._refresh_steps(len(self.current_control()["steps"]) - 1)
            self._mark_dirty()

    def edit_step(self) -> None:
        row = self.step_list.currentRow()
        if row < 0:
            return
        dialog = StepDialog(self.current_control()["steps"][row], self, self.project["keyboard_layout"])
        if dialog.exec() and (step := dialog.step()):
            self.current_control()["steps"][row] = step
            self._refresh_steps(row)
            self._mark_dirty()

    def remove_step(self) -> None:
        row = self.step_list.currentRow()
        if row >= 0:
            self.current_control()["steps"].pop(row)
            self._refresh_steps(min(row, len(self.current_control()["steps"]) - 1))
            self._mark_dirty()

    def move_step(self, offset: int) -> None:
        row = self.step_list.currentRow()
        target = row + offset
        steps = self.current_control()["steps"]
        if row < 0 or target < 0 or target >= len(steps):
            return
        steps.insert(target, steps.pop(row))
        self._refresh_steps(target)
        self._mark_dirty()

    def _steps_reordered(self, parent, start, end, destination, row) -> None:
        if self.loading or start != end:
            return
        steps = self.current_control()["steps"]
        if start < 0 or start >= len(steps):
            return
        step = steps.pop(start)
        target = row if row < start else row - 1
        target = max(0, min(target, len(steps)))
        steps.insert(target, step)
        self._refresh_steps(target)
        self._mark_dirty("Reordered macro steps")

    def preview_selected_action(self) -> None:
        steps = self.current_control()["steps"]
        details = "\n".join(f"{index + 1}. {step_summary(step)}" for index, step in enumerate(steps))
        QMessageBox.information(
            self,
            f"Safe preview — {self.current_control()['name']}",
            details or "This control is unset and will perform no action.",
        )

    def test_selected_action(self) -> None:
        control = self.current_control()
        if not control["steps"]:
            self.statusBar().showMessage("This control has no action to test", 3000)
            return
        if QMessageBox.question(
            self,
            "Run HID action?",
            "The MacroPad will send this action to the currently focused application. Continue?",
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            response = send_command(
                {"cmd": "test_steps", "name": control["name"], "steps": control["steps"]},
                self.current_device().uid,
                timeout=3.0,
            )
            self.statusBar().showMessage(f"Device started {response.get('steps', 0)} test step(s)", 4000)
        except DeviceError as exc:
            QMessageBox.critical(self, "Test failed", str(exc))

    def save_local(self) -> None:
        try:
            self.project = validate_project(self.project)
            save_json(self.local_path, self.project)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Cannot save", str(exc))
            return
        self.dirty = False
        self.history_state = copy.deepcopy(self.project)
        self.statusBar().showMessage(f"Autosaved local library to {self.local_path}", 3500)
        self._update_state_status()

    def _update_state_status(self, message: str = "") -> None:
        if self.dirty:
            text, color = " Autosaving… ", "#CC8800"
        elif self.unsynced:
            text, color = " Local saved • device differs ", "#CC6600"
        else:
            text, color = " Synced/local saved ", "#228844"
        self.state_label.setText(text)
        self.state_label.setStyleSheet(f"color: white; background: {color}; padding: 3px 8px; border-radius: 4px")
        if message:
            self.statusBar().showMessage(message, 3500)

    def import_profile(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Import profile", "", "JSON files (*.json)")
        if not filename:
            return
        try:
            profile = normalize_profile(load_json(Path(filename)), Path(filename).stem)
            used = {item["id"] for item in self.project["profiles"]}
            profile["id"] = unique_id(profile["id"], used)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Import failed", str(exc))
            return
        self.project["profiles"].append(profile)
        self._refresh_profile_list(len(self.project["profiles"]) - 1)
        self._mark_dirty()

    def export_profile(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(self, "Export profile", self.current_profile()["id"] + ".json", "JSON files (*.json)")
        if not filename:
            return
        try:
            save_json(Path(filename), self.current_profile())
        except OSError as exc:
            QMessageBox.critical(self, "Export failed", str(exc))

    def refresh_devices(self) -> None:
        self.devices = discover_devices()
        self.device_combo.clear()
        for device in self.devices:
            alias = self.device_aliases.get(device.uid, "")
            label = f"{alias} ({device.uid})" if alias else (device.uid or "MacroPad")
            self.device_combo.addItem(f"{label} — {device.mount}")
        if not self.devices:
            self.device_combo.addItem("No MacroPad CIRCUITPY drive found")
        else:
            try:
                self.unsynced = bool(compare_projects(self.project, read_device_project(self.devices[0])))
                if hasattr(self, "state_label"):
                    self._update_state_status()
            except (DeviceError, ValueError):
                pass
        self.statusBar().showMessage(f"Found {len(self.devices)} MacroPad device(s)", 4000)

    def name_device(self) -> None:
        try:
            device = self.current_device()
        except DeviceError as exc:
            QMessageBox.critical(self, "No device", str(exc))
            return
        current = self.device_aliases.get(device.uid, "")
        name, accepted = QInputDialog.getText(self, "Name MacroPad", "Friendly device name", text=current)
        if accepted:
            if name.strip():
                self.device_aliases[device.uid] = name.strip()[:32]
            else:
                self.device_aliases.pop(device.uid, None)
            self.settings.setValue("device_aliases", self.device_aliases)
            self.refresh_devices()

    def current_device(self) -> DeviceInfo:
        index = self.device_combo.currentIndex()
        if not self.devices or index < 0 or index >= len(self.devices):
            raise DeviceError("No MacroPad CIRCUITPY drive is connected")
        return self.devices[index]

    def import_device(self) -> None:
        try:
            project = read_device_project(self.current_device())
        except DeviceError as exc:
            QMessageBox.critical(self, "Import failed", str(exc))
            return
        if self.dirty and QMessageBox.question(self, "Replace local edits?", "Importing will replace unsaved local edits. Continue?") != QMessageBox.StandardButton.Yes:
            return
        self.project = project
        self._refresh_profile_list(0)
        self._mark_dirty("Imported profiles from MacroPad")
        self.save_local()
        self.unsynced = False
        self.history_state = copy.deepcopy(self.project)
        self._update_state_status("Imported profiles from MacroPad")

    def preview_rgb(self) -> None:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            device = self.current_device()
            preview_lighting(device, self.current_profile())
            self.preview_device = device
            self.statusBar().showMessage("Temporary RGB preview active", 5000)
        except DeviceError as exc:
            QMessageBox.critical(self, "Preview failed", str(exc))
        finally:
            QApplication.restoreOverrideCursor()

    def clear_rgb_preview(self) -> None:
        try:
            device = self.preview_device or self.current_device()
            clear_preview(device)
            self.preview_device = None
            self.statusBar().showMessage("RGB preview cleared", 4000)
        except DeviceError as exc:
            QMessageBox.critical(self, "Clear preview failed", str(exc))

    def sync_device(self) -> None:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.project = validate_project(self.project)
            self.save_local()
            device = self.current_device()
            remote = read_device_project(device)
            changes = compare_projects(self.project, remote)
            if not changes:
                self.unsynced = False
                self._update_state_status("Device already matches the local library")
                return
            summary = "\n".join(f"• {change}" for change in changes[:16])
            if len(changes) > 16:
                summary += f"\n• …and {len(changes) - 16} more change(s)"
            if QMessageBox.question(
                self,
                "Synchronize these changes?",
                summary + "\n\nA device backup will be created first.",
            ) != QMessageBox.StandardButton.Yes:
                return
            backup_path = backup_device(device, self.backup_root)
            revision = sync_project(device, self.project)
            try:
                send_command({"cmd": "reload_config"}, device.uid)
            except DeviceError:
                pass
            self.preview_device = None
            self.unsynced = False
            self._update_state_status(f"Synchronized revision {revision}; backup: {backup_path.name}")
        except (DeviceError, ValueError) as exc:
            QMessageBox.critical(self, "Sync failed", str(exc))
        finally:
            QApplication.restoreOverrideCursor()

    def compare_with_device(self) -> None:
        try:
            changes = compare_projects(self.project, read_device_project(self.current_device()))
        except (DeviceError, ValueError) as exc:
            QMessageBox.critical(self, "Comparison failed", str(exc))
            return
        QMessageBox.information(
            self,
            "Local ↔ device comparison",
            "\n".join(f"• {change}" for change in changes) if changes else "The local library and device match.",
        )

    def export_library(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export complete library",
            "macropad-library.macropad.zip",
            "MacroPad library (*.macropad.zip *.zip)",
        )
        if not filename:
            return
        try:
            export_library_archive(Path(filename), self.project, self.palette)
            self.statusBar().showMessage(f"Exported complete library to {filename}", 5000)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Export failed", str(exc))

    def import_library(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Import complete library",
            "",
            "MacroPad library (*.macropad.zip *.zip)",
        )
        if not filename:
            return
        try:
            project, palette = import_library_archive(Path(filename))
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Import failed", str(exc))
            return
        self.project = project
        for color in reversed(palette):
            self._remember_palette_color(color)
        self._refresh_profile_list(0)
        self._mark_dirty("Imported complete profile library")

    def restore_backup(self) -> None:
        try:
            device = self.current_device()
        except DeviceError as exc:
            QMessageBox.critical(self, "No device", str(exc))
            return
        backups = list_device_backups(self.backup_root, device.uid)
        if not backups:
            QMessageBox.information(self, "Backups", "No backups exist for this MacroPad yet.")
            return
        labels = [path.stem for path in backups]
        label, accepted = QInputDialog.getItem(self, "Restore backup", "Load backup into local editor", labels, 0, False)
        if not accepted:
            return
        try:
            self.project = normalize_project(load_json(backups[labels.index(label)]))
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Restore failed", str(exc))
            return
        self._refresh_profile_list(0)
        self._mark_dirty("Backup loaded locally; review and Sync Device to restore it")

    def show_device_health(self) -> None:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            health = device_health(self.current_device())
            missing = health.get("missing", [])
            lines = [
                f"Configurator: {__version__}",
                f"Firmware: {health.get('firmware_version', 'unknown')}",
                f"Configuration revision: {health.get('revision', 'unknown')}",
                f"Active profile: {health.get('profile', 'unknown')}",
                f"Layout: {health.get('layout', 'unknown').upper()}",
                "Required files: OK" if not missing else "Missing:\n  " + "\n  ".join(missing),
            ]
            if health.get("serial_error"):
                lines.append("Serial: " + health["serial_error"])
            elif health.get("firmware_version") != __version__:
                lines.append("Update recommended: firmware and configurator versions differ")
            QMessageBox.information(self, "MacroPad device health", "\n".join(lines))
        except DeviceError as exc:
            QMessageBox.critical(self, "Health check failed", str(exc))
        finally:
            QApplication.restoreOverrideCursor()

    def repair_device_firmware(self) -> None:
        if QMessageBox.question(
            self,
            "Repair/update firmware?",
            "Reinstall required libraries and update firmware while preserving profiles?",
        ) != QMessageBox.StandardButton.Yes:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            device = self.current_device()
            try:
                backup_device(device, self.backup_root)
            except DeviceError:
                pass
            source = Path(__file__).resolve().parents[2] / "device"
            repair_firmware(device, source)
            self.statusBar().showMessage("Firmware repair/update completed; device restarting", 6000)
        except DeviceError as exc:
            QMessageBox.critical(self, "Repair failed", str(exc))
        finally:
            QApplication.restoreOverrideCursor()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self.preview_device:
            try:
                clear_preview(self.preview_device)
            except DeviceError:
                pass
        if self.dirty:
            choice = QMessageBox.question(
                self,
                "Save local changes?",
                "Save your local profile-library changes before closing?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            )
            if choice == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            if choice == QMessageBox.StandardButton.Yes:
                self.save_local()
        event.accept()
