from __future__ import annotations

from typing import Any

from PySide6.QtCore import QMimeData, QPoint, Qt, Signal
from PySide6.QtGui import QColor, QDrag, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QToolButton,
)

from .models import CONSUMER_CODES, MAX_DELAY_MS, MOUSE_BUTTONS, normalize_step


COMMON_KEY_NAMES = (
    "CONTROL", "SHIFT", "ALT", "GUI", "ENTER", "ESCAPE", "TAB", "SPACE", "BACKSPACE", "DELETE",
    "HOME", "END", "PAGE_UP", "PAGE_DOWN", "UP_ARROW", "DOWN_ARROW", "LEFT_ARROW", "RIGHT_ARROW",
    "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "ZERO", "COMMA",
    "GRAVE_ACCENT",
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q",
    "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "F1", "F2", "F3", "F4", "F5", "F6", "F7",
    "F8", "F9", "F10", "F11", "F12",
)

ACTION_PRESETS = (
    ("Copy", {"type": "hotkey", "keys": ["CONTROL", "C"]}),
    ("Paste", {"type": "hotkey", "keys": ["CONTROL", "V"]}),
    ("Cut", {"type": "hotkey", "keys": ["CONTROL", "X"]}),
    ("Undo", {"type": "hotkey", "keys": ["CONTROL", "Z"]}),
    ("Redo", {"type": "hotkey", "keys": ["CONTROL", "SHIFT", "Z"]}),
    ("Save", {"type": "hotkey", "keys": ["CONTROL", "S"]}),
    ("Select all", {"type": "hotkey", "keys": ["CONTROL", "A"]}),
    ("Close tab", {"type": "hotkey", "keys": ["CONTROL", "W"]}),
    ("Play / pause", {"type": "consumer", "code": "PLAY_PAUSE"}),
    ("Mute", {"type": "consumer", "code": "MUTE"}),
    ("Volume up", {"type": "consumer", "code": "VOLUME_INCREMENT"}),
    ("Volume down", {"type": "consumer", "code": "VOLUME_DECREMENT"}),
    ("Left click", {"type": "mouse", "action": "click", "button": "LEFT_BUTTON"}),
    ("Right click", {"type": "mouse", "action": "click", "button": "RIGHT_BUTTON"}),
)


class MacroKeyButton(QToolButton):
    """A key tile that supports drag-and-drop swapping."""

    swapRequested = Signal(int, int)
    MIME = "application/x-macropad-key"

    def __init__(self, key_index: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.key_index = key_index
        self._drag_start = QPoint()
        self.setAcceptDrops(True)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if not event.buttons() & Qt.MouseButton.LeftButton:
            return super().mouseMoveEvent(event)
        if (event.position().toPoint() - self._drag_start).manhattanLength() < QApplication.startDragDistance():
            return super().mouseMoveEvent(event)
        mime = QMimeData()
        mime.setData(self.MIME, str(self.key_index).encode("ascii"))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.setPixmap(self.grab())
        drag.exec(Qt.DropAction.MoveAction)

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(self.MIME):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        try:
            source = int(bytes(event.mimeData().data(self.MIME)).decode("ascii"))
        except (TypeError, ValueError):
            return
        if source != self.key_index:
            self.swapRequested.emit(source, self.key_index)
        event.acceptProposedAction()


class OledPreview(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.profile: dict[str, Any] | None = None
        self.setMinimumSize(384, 192)

    def set_profile(self, profile: dict[str, Any] | None) -> None:
        self.profile = profile
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(self.rect(), QColor("#101418"))
        bounds = self.rect().adjusted(8, 8, -8, -8)
        painter.fillRect(bounds, QColor("#020304"))
        painter.setPen(QPen(QColor("#DDEEFF"), 1))
        if not self.profile:
            painter.drawText(bounds, Qt.AlignmentFlag.AlignCenter, "No profile")
            return
        line_height = max(18, bounds.height() // 5)
        icon = self.profile.get("icon", "")[:2]
        title = ((icon + " ") if icon else "") + self.profile["name"]
        painter.drawText(bounds.adjusted(8, 0, -8, 0), Qt.AlignmentFlag.AlignTop, title[:20])
        cell_width = bounds.width() // 3
        for row in range(4):
            y = bounds.top() + line_height * (row + 1)
            for column in range(3):
                index = row * 3 + column
                cell = bounds.adjusted(column * cell_width, y - bounds.top(), -(2 - column) * cell_width, 0)
                painter.drawText(cell, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, self.profile["keys"][index]["oled_label"][:6])


class StepDialog(QDialog):
    def __init__(
        self,
        step: dict[str, Any] | None = None,
        parent: QWidget | None = None,
        layout_name: str = "us",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Macro step")
        self.resize(520, 330)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["hotkey", "text", "consumer", "mouse", "delay"])
        self.preset_combo = QComboBox()
        self.preset_combo.addItem("Custom action", None)
        for label, value in ACTION_PRESETS:
            self.preset_combo.addItem(label, value)
        self.stack = QStackedWidget()
        self.stack.addWidget(self._hotkey_page())
        self.stack.addWidget(self._text_page())
        self.stack.addWidget(self._consumer_page())
        self.stack.addWidget(self._mouse_page())
        self.stack.addWidget(self._delay_page())
        self.type_combo.currentIndexChanged.connect(self.stack.setCurrentIndex)
        self.preset_combo.currentIndexChanged.connect(self._preset_changed)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.addRow("Preset", self.preset_combo)
        form.addRow("Type", self.type_combo)
        layout_note = "German host mapping active" if layout_name == "de" else "US host mapping active"
        form.addRow("Keyboard layout", QLabel(layout_note))
        layout.addLayout(form)
        layout.addWidget(self.stack, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        if step:
            self.set_step(step)

    def _hotkey_page(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)
        self.hotkey_edit = QLineEdit()
        self.hotkey_edit.setPlaceholderText("CONTROL, SHIFT, S")
        layout.addRow("Keys", self.hotkey_edit)
        picker = QHBoxLayout()
        self.hotkey_key_combo = QComboBox()
        self.hotkey_key_combo.setEditable(True)
        self.hotkey_key_combo.addItems(COMMON_KEY_NAMES)
        self.hotkey_key_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        add_key = QPushButton("Add key")
        add_key.clicked.connect(self._append_hotkey_key)
        picker.addWidget(self.hotkey_key_combo, 1)
        picker.addWidget(add_key)
        layout.addRow("Find HID key", picker)
        layout.addRow(QLabel("Use HID names separated by commas, for example CONTROL, C or ALT, TAB."))
        return page

    def _append_hotkey_key(self) -> None:
        key = self.hotkey_key_combo.currentText().strip().upper().replace(" ", "_")
        if not key:
            return
        keys = [part.strip() for part in self.hotkey_edit.text().replace("+", ",").split(",") if part.strip()]
        if key not in keys:
            keys.append(key)
        self.hotkey_edit.setText(", ".join(keys))

    def _preset_changed(self, index: int) -> None:
        value = self.preset_combo.itemData(index)
        if isinstance(value, dict):
            self.set_step(value)

    def _text_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("Text typed by the MacroPad")
        layout.addWidget(self.text_edit)
        return page

    def _consumer_page(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)
        self.consumer_combo = QComboBox()
        self.consumer_combo.addItems(CONSUMER_CODES)
        layout.addRow("Media action", self.consumer_combo)
        return page

    def _mouse_page(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)
        self.mouse_action_combo = QComboBox()
        self.mouse_action_combo.addItems(["click", "move"])
        self.mouse_button_combo = QComboBox()
        self.mouse_button_combo.addItems(MOUSE_BUTTONS)
        self.mouse_x = self._signed_spin()
        self.mouse_y = self._signed_spin()
        self.mouse_wheel = self._signed_spin()
        layout.addRow("Action", self.mouse_action_combo)
        layout.addRow("Button", self.mouse_button_combo)
        layout.addRow("X", self.mouse_x)
        layout.addRow("Y", self.mouse_y)
        layout.addRow("Wheel", self.mouse_wheel)
        self.mouse_action_combo.currentTextChanged.connect(self._update_mouse_fields)
        self._update_mouse_fields("click")
        return page

    def _signed_spin(self) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(-127, 127)
        return spin

    def _delay_page(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, MAX_DELAY_MS)
        self.delay_spin.setSuffix(" ms")
        layout.addRow("Delay", self.delay_spin)
        return page

    def _update_mouse_fields(self, action: str) -> None:
        clicking = action == "click"
        self.mouse_button_combo.setEnabled(clicking)
        self.mouse_x.setEnabled(not clicking)
        self.mouse_y.setEnabled(not clicking)
        self.mouse_wheel.setEnabled(not clicking)

    def set_step(self, step: dict[str, Any]) -> None:
        step_type = str(step.get("type", "hotkey"))
        self.type_combo.setCurrentText(step_type)
        if step_type == "hotkey":
            self.hotkey_edit.setText(", ".join(step.get("keys", [])))
        elif step_type == "text":
            self.text_edit.setPlainText(str(step.get("text", "")))
        elif step_type == "consumer":
            self.consumer_combo.setCurrentText(str(step.get("code", "MUTE")))
        elif step_type == "mouse":
            self.mouse_action_combo.setCurrentText(str(step.get("action", "click")))
            self.mouse_button_combo.setCurrentText(str(step.get("button", "LEFT_BUTTON")))
            self.mouse_x.setValue(int(step.get("x", 0)))
            self.mouse_y.setValue(int(step.get("y", 0)))
            self.mouse_wheel.setValue(int(step.get("wheel", 0)))
        elif step_type == "delay":
            self.delay_spin.setValue(int(step.get("ms", 0)))

    def step(self) -> dict[str, Any] | None:
        step_type = self.type_combo.currentText()
        if step_type == "hotkey":
            raw = self.hotkey_edit.text().replace("+", ",")
            value = {"type": "hotkey", "keys": [part.strip() for part in raw.split(",") if part.strip()]}
        elif step_type == "text":
            value = {"type": "text", "text": self.text_edit.toPlainText()}
        elif step_type == "consumer":
            value = {"type": "consumer", "code": self.consumer_combo.currentText()}
        elif step_type == "mouse" and self.mouse_action_combo.currentText() == "click":
            value = {"type": "mouse", "action": "click", "button": self.mouse_button_combo.currentText()}
        elif step_type == "mouse":
            value = {
                "type": "mouse",
                "action": "move",
                "x": self.mouse_x.value(),
                "y": self.mouse_y.value(),
                "wheel": self.mouse_wheel.value(),
            }
        else:
            value = {"type": "delay", "ms": self.delay_spin.value()}
        return normalize_step(value)
