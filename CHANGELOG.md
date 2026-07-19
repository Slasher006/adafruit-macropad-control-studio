# Changelog

All notable changes to the Adafruit MacroPad Configurator are documented here.

## Unreleased

### Firmware and profiles

- Added a temporary visible-profile filter so encoder scrolling can be limited
  to open applications without removing the full on-device library.
- Kept profile and subprofile persistence keyed to stable library positions
  while the visible profile set changes.
- Added dedicated Reddit, YouTube, Instagram, Printables, Thingiverse, Nitter,
  and Prime Video profiles with contextual In App layouts.
- Added Firefox-title rules so the App deck selects each website profile before
  falling back to the generic Firefox layout.

### Desktop service

- Added all-window discovery and configurable pinned profiles so app-open and
  app-close events update the visible encoder list.
- Made automatic profile switching recover after boot when systemd starts before
  the i3/Sway graphical environment variables are available.

## 1.1.0

### Configurator

- Added parent-profile sublayouts with add, duplicate, rename, delete, and
  drag-and-drop encoder-press ordering.
- Added drag-to-move key assignments while retaining explicit two-control
  swapping.
- Added a File menu with guarded Exit and the standard Ctrl+Q shortcut.
- Added concise description-and-example tooltips to every user-facing action
  and input in the main window and macro-step editor.
- Extended device comparison, health, backup, import/export, palette, and
  multi-selection workflows.

### Firmware and profiles

- Added persistent per-profile sublayout selection.
- Added Manual and App deck roles with a device-managed Options screen.
- Added focused-application profile switching for i3 and Sway sessions.
- Added maintained Caja, Krita, LibreOffice, and Blender profiles.
- Expanded all maintained profiles with additional layouts and contextual
  In App screens.
- Kept terminal and SSH command templates reviewable by omitting automatic
  Enter presses.

### Documentation

- Added an exhaustive, example-driven PDF tutorial and reproducible generator.
- Expanded the GUI guide and built-in profile catalog.
- Added automated tooltip coverage and broader firmware, model, profile, and
  profile-switcher tests.

## 1.0.0

- Initial public release of the PySide6 configurator, standalone CircuitPython
  firmware, built-in profiles, deployment tools, and GUI documentation.
