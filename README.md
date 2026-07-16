# Adafruit MacroPad Configurator

This project contains standalone CircuitPython firmware for the Adafruit MacroPad RP2040 and a PySide6 profile editor. The MacroPad performs keyboard, text, media, and mouse actions without the desktop app running.

The editor provides visual profile and OLED editing, multi-key RGB tools, reusable action sequences, per-device backups, library import/export, device comparison, and safe synchronization. See the complete [Configurator GUI guide](docs/CONFIGURATOR_GUI.md) for the interface tour, workflows, examples, and troubleshooting.

## Run the editor

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -e '.[test]'
./run_gui.sh
```

The editor stores its local library in Qt's per-user application-data directory. Use **Import Device** to copy the current `CIRCUITPY` profiles into the editor, **Preview RGB** for a temporary lighting preview, and **Sync Device** for an explicit configuration update.

For an existing device, the safest first workflow is **Import Device → edit → Compare → Preview RGB → Sync Device**. Import copies from the device to the editor; Sync copies from the editor to the selected device.

## Editing conveniences

- Undo/redo, autosave, control copy/paste, swapping, and drag-and-drop key swaps.
- Ctrl-click multiple keys to edit lighting together; palettes can target selected keys, a row, or the whole pad.
- Drag macro steps and profiles to reorder them.
- Editing, Media, and Blank profile templates plus clear-profile and reset-lighting shortcuts.
- Searchable HID key names, common action presets, safe macro previews, and explicit on-device test execution.
- Optional two-character profile icons in both the editor and OLED title.

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
- Press the encoder to execute its configured action sequence.
- Press one of the 12 keys to execute its action sequence.
- Each profile has its own brightness, idle colors, and pressed colors.
- Use **Unset key** in the editor to clear a control's name, OLED label, and action sequence.
- Clear **Illuminate this key** to keep an individual key dark while preserving its configured colors.

The included app, desktop, terminal, SSH, and audio mappings are summarized in [PROFILE_LAYOUTS.md](PROFILE_LAYOUTS.md). All built-in and newly created profiles default to 5% key brightness.
