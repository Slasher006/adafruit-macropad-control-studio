# Adafruit MacroPad Configurator

This project contains standalone CircuitPython firmware for the Adafruit MacroPad RP2040 and a PySide6 profile editor. The MacroPad performs keyboard, text, media, and mouse actions without the desktop app running.

The editor provides visual profile and OLED editing, multi-key RGB tools, reusable action sequences, per-device backups, library import/export, device comparison, and safe synchronization. See the complete [Configurator GUI guide](docs/CONFIGURATOR_GUI.md) for the interface tour, workflows, examples, and troubleshooting. An exhaustive printable tutorial is available as [PDF](output/pdf/adafruit-macropad-configurator-tutorial.pdf).

## Run the editor

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
./run_gui.sh
```

The editor stores its local library in Qt's per-user application-data directory. Use **Import Device** to copy the current `CIRCUITPY` profiles into the editor, **Preview RGB** for a temporary lighting preview, and **Sync Device** for an explicit configuration update.

For an existing device, the safest first workflow is **Import Device → edit → Compare → Preview RGB → Sync Device**. Import copies from the device to the editor; Sync copies from the editor to the selected device.

## Editing conveniences

- Undo/redo, autosave, control copy/paste, explicit swapping, and drag-and-drop
  key reordering with automatic shifting.
- Ctrl-click multiple keys to edit lighting together; palettes can target selected keys, a row, or the whole pad.
- Drag profile screens to change encoder-turn order, and drag subprofile screens
  to change encoder-press order.
- Editing, Media, and Blank profile templates plus clear-profile and reset-lighting shortcuts.
- Searchable HID key names, common action presets, safe macro previews, and explicit on-device test execution.
- Optional two-character profile icons in both the editor and OLED title.
- Visual subprofile/submenu selection with add, duplicate, reorder, rename, and
  delete controls.

## Sync safety and maintenance

- The status badge distinguishes local edits from synchronized state, and **Compare** previews device differences.
- Every changed synchronization creates a per-device backup. **Backups** loads an older revision locally for review before restoring it with Sync.
- **Export Library** and **Import Library** move the complete library and saved color palette as one archive.
- Devices can have friendly aliases. **Device Health** checks versions and required files; **Repair Firmware** reinstalls dependencies and firmware while preserving profiles.

## Device layout

Copy `device/code.py`, `device/macropad_core.py`, `device/device_config.json`, and `device/profiles/` to the root of `CIRCUITPY`. The helper at `tools/deploy_device.py` installs `adafruit_macropad`, its CircuitPython 10.x dependencies, and the maintained `keyboard_layout_win_de` / `keycode_win_de` modules before copying the project files.

Profile changes are written through temporary files, with `profiles/index.json` and `profiles/revision.txt` committed last. Firmware keeps the last valid in-memory profile if a write is interrupted or malformed.

## Controls

- Turn the encoder to switch profile immediately.
- Press the encoder to advance to the next subprofile when the active profile has
  multiple layouts. Profiles with one layout keep their configured encoder action.
- Press one of the 12 keys to execute its action sequence.
- Each profile has its own brightness, idle colors, and pressed colors.
- The selected subprofile is remembered per parent profile, so turning to another
  profile and back does not reset it. The selection is also restored after restart.
- Use **Unset key** in the editor to clear a control's name, OLED label, and action sequence.
- Clear **Illuminate this key** to keep an individual key dark while preserving its configured colors.

### On-device options

Turn through the parent profiles until the visible **Options** screen appears.
It assigns that physical MacroPad one of two independent deck roles:

- **Manual deck** stays on the regular parent profile and subprofile selected
  with its encoder. Automatic focused-app commands are ignored.
- **App deck** follows the focused desktop application while preserving that
  application's selected subprofile.

Press key 1 for Manual, key 3 for App, or press the encoder to toggle roles.
Turn the encoder to leave. Holding it for about one second from any profile is
a shortcut to the same screen. The role is stored separately on each device and
survives restarts, so either MacroPad can be the Manual deck or the App deck.
For a two-device split, set one device to each role.

## Automatic profile switching

The included systemd user service reads the focused i3/Sway window and switches
every connected MacroPad to the matching parent profile. For example, focusing
Firefox selects `firefox`, Code OSS selects `vscode`, and a Firefox tab whose
title contains ComfyUI selects `comfyui`. Firefox tabs for Reddit, YouTube,
Instagram, Printables, Thingiverse, Nitter, and Prime Video select their own
website profiles before the generic Firefox fallback. Caja, Krita, LibreOffice,
and Blender have dedicated matches as well. On an App deck the service selects
the matching parent plus its fourth **In App** layout. This automatic contextual
selection does not overwrite the manually remembered layout used when that
device acts as a Manual deck.

The service also keeps the encoder list short on both deck roles. It scans all
open i3/Sway windows and temporarily exposes only their matching profiles plus
the pinned `i3wm`, `quicklaunch`, and `options` profiles. Opening or closing an
application updates the list without deleting any stored profile. If filtering
is disabled or the device restarts without the service, the complete library is
available again. Firefox can report the selected tab title in each browser
window, but not every inactive tab, so website profiles appear for currently
selected website tabs.

Install and start it with:

```bash
.venv/bin/python tools/install_profile_switcher.py
```

The editable matching rules are stored at
`~/.config/macropad-profile-switcher.json`. After changing them, restart the
service:

```bash
systemctl --user restart macropad-profile-switcher.service
```

Set `"filter_open_apps": false` to retain the complete encoder list, or edit
`"pinned_profiles"` to change which utility profiles always remain visible.

Inspect its state and recent decisions with:

```bash
systemctl --user status macropad-profile-switcher.service
journalctl --user -u macropad-profile-switcher.service -n 50
```

The included app, desktop, terminal, SSH, and audio mappings are summarized in [PROFILE_LAYOUTS.md](PROFILE_LAYOUTS.md). All built-in and newly created profiles default to 5% key brightness.

## Development and verification

Install the test and documentation dependencies:

```bash
.venv/bin/pip install -e '.[test,docs]'
```

Run the full headless Qt test suite:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

Regenerate the printable tutorial:

```bash
.venv/bin/python tools/generate_configurator_tutorial.py
```

The generated file is written to
`output/pdf/adafruit-macropad-configurator-tutorial.pdf`.

## Project documentation

- [Exhaustive configurator tutorial (PDF)](output/pdf/adafruit-macropad-configurator-tutorial.pdf)
- [Configurator GUI guide](docs/CONFIGURATOR_GUI.md)
- [Included profile layouts](PROFILE_LAYOUTS.md)
- [Release history](CHANGELOG.md)
- [Contributing and verification](CONTRIBUTING.md)
