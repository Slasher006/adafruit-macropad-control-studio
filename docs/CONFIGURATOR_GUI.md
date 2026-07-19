# Configurator GUI guide

The Adafruit MacroPad Configurator is the desktop editor for this project's profiles. It keeps an autosaved local library, previews changes, compares that library with a connected MacroPad, and writes profiles to the device only when you choose **Sync Device**.

The MacroPad does not need the configurator to run its profiles. Once synchronized, all hotkeys, typed text, media commands, mouse actions, RGB colors, and macros are executed by the CircuitPython firmware on the device.

## Start the configurator

On Linux, create the environment once and then use the launcher:

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -e '.[test]'
./run_gui.sh
```

You can also double-click `Start-MacroPad-Configurator.sh` in a file manager. When installed as a package, the command is `macropad-configurator`.

Connect the MacroPad normally so its `CIRCUITPY` drive is mounted. The editor detects supported Adafruit MacroPad RP2040 drives automatically.

## How saving and synchronization work

There are two independent copies of your configuration:

- **Local library** — the working copy used by the GUI. Changes are autosaved after a short delay.
- **Device profiles** — the configuration currently running on the selected MacroPad.

The colored status badge explains their state:

- **Autosaving…** means a local edit is waiting to be saved.
- **Local saved • device differs** means the local library is safe, but the connected device has not received those changes.
- **Synced/local saved** means the local and selected device configurations match.

The recommended first-use workflow is:

1. Select the MacroPad in the **Device** list.
2. Choose **Import Device** if the device already contains profiles you want to keep.
3. Edit profiles and controls in the local library.
4. Use **Compare** to review what will change.
5. Optionally use **Preview RGB** to see the active profile's colors on the hardware.
6. Choose **Sync Device** to write the full library to that MacroPad.

> **Important:** **Import Device** replaces the local library with the profiles from the selected device. **Sync Device** goes in the other direction and replaces the selected device's profile library with the local one.

## Interface tour

Hover over any menu command, toolbar action, button, key tile, list, or input for
a concise tooltip. Every tooltip includes both a short description and a
practical example.

### Device toolbar

| Control | Purpose |
| --- | --- |
| **Device** | Selects one of the connected MacroPads. The mount path and device UID help distinguish multiple units. |
| **Refresh** | Scans mounted drives again. Use this after connecting or disconnecting a device. |
| **Import Device** | Loads the selected device's profiles into the local editor. |
| **Preview RGB** | Temporarily displays the active profile's lighting on the selected device without synchronizing profiles. |
| **Clear Preview** | Returns the device from temporary preview mode to its normal profile lighting. |
| **Sync Device** | Backs up the existing device configuration and safely writes the local library. |
| **Save Local** | Immediately saves the library; normal edits are also autosaved. |
| **Layout** | Chooses US or German host keyboard mapping for keyboard and text actions. |

Additional maintenance commands are available on the second toolbar and in the **Library** and **Device** menus:

- **File → Exit** closes the configurator, prompting to save pending local changes when needed.
- **Compare** lists profile, order, brightness, layout, and control differences.
- **Backups** loads an earlier per-device backup into the local editor for inspection. Synchronize afterward only if you want to restore it to hardware.
- **Export Library** creates a portable archive containing every profile and the saved color palette.
- **Import Library** loads a previously exported library archive.
- **Device Health** checks required firmware files and the serial command connection.
- **Repair Firmware** reinstalls the firmware and required CircuitPython libraries while preserving existing profiles when possible.
- **Name Device** assigns a local friendly name to a MacroPad UID.

### Profiles panel

The left panel controls profile membership and order. The device uses this exact order when you turn the rotary encoder.

- **Add** creates a blank profile at the standard 5% brightness.
- **Duplicate** creates an editable copy of the selected profile.
- **Delete** removes the selected profile. At least one profile must remain.
- The left **Profile screens** list is the device's encoder-turn sequence. Drag
  screens into the desired order, or use **Up** and **Down**.
- **Import…** and **Export…** move one profile as JSON without replacing the full library.
- **Template…** creates an Editing, Media, or Blank profile.
- **Clear profile** removes every key and encoder assignment while retaining the profile identity and brightness.
- **Reset lights** restores the profile to 5% brightness and the default idle/pressed colors.

The editor supports up to 32 profiles. Keep frequently used profiles next to each other so they take fewer encoder turns to reach.

### Active profile and MacroPad preview

The center panel edits the profile itself:

- **Name** is the full profile name shown in the GUI and on the OLED.
- **OLED icon** is an optional two-character prefix for the OLED title.
- **Light intensity** is stored per profile from 0–100%. New and built-in profiles use 5% by default.
- **Screens (knob press order)** lists the active profile's key layouts in the
  exact sequence shown when pressing the encoder. Drag screens to reorder them;
  use **+** to add, **⧉** to duplicate, **↑/↓** to move, and **−** to remove an
  additional layout. The first screen can be moved but cannot be deleted.
- **Profile name** labels the parent entry selected by turning the encoder;
  **Layout name** labels the selected subprofile shown on the OLED.
- The monochrome preview shows the profile title and the six-character OLED labels in the same 3×4 arrangement as the hardware.

Click any of the 12 key tiles or **Encoder press** to edit that control. Drag a
key tile onto another position to move it there; the intervening assignments
shift to close and open the corresponding positions. The cyan dashed border
marks the drop target. Ctrl-click keys to select several keys for a shared
lighting change. Use **Swap…** when you want to exchange exactly two controls
without shifting the keys between them.

When a profile has additional subprofiles, encoder press is reserved for cycling
through them and its action editor is disabled. The selected subprofile stays
active when you turn to another parent profile and back, and is persisted across
device restarts. A single-layout profile continues to use its normal encoder
action.

Turn to the visible **Options** parent screen on the device, or hold the physical
encoder for about one second to open it directly. Select **Manual deck** with
key 1, **Profile deck** with key 2, or **App deck** with key 3. Pressing the
encoder cycles Manual -> Profile -> App. Turn the encoder to leave.

The Manual deck stays on its encoder-selected regular profile and ignores
focused-application changes. The Profile deck follows the focused PC
application's parent profile but restores that parent's remembered normal key
screen. The App deck follows the same parent and selects its **In App** key
screen. Roles are stored independently and persistently on each device.
Automatic **In App** selection does not replace the subprofile remembered for
Manual or Profile mode.

While the desktop service is connected, all three deck roles receive a temporary
encoder filter containing profiles for open applications plus the pinned
`i3wm`, `quicklaunch`, and `options` utilities. Profiles remain stored on the
device and return after a reboot or when filtering is disabled. Each profile's
remembered layout uses its stable library position, so app-open/app-close
updates cannot transfer a saved layout to a different profile. Firefox website
matching uses the selected tab title from each browser window; inactive tabs
that are not selected in any window are not visible to i3/Sway.

The installed `~/.config/macropad-profile-switcher.json` file controls this with
`filter_open_apps` and `pinned_profiles`. Set `filter_open_apps` to `false` for
the complete encoder list.

### Control editor

The right panel edits the selected key or encoder press.

**Label**

- **Name** is the descriptive label shown on the key tile.
- **OLED label** is limited to six characters to fit the device display.
- **Unset key** clears the labels and action sequence. It does not delete the profile.

**RGB**

- **Illuminate this key** turns the key light on or off without losing its saved colors.
- **Idle color** is displayed while the key is waiting.
- **Pressed color** is displayed briefly when the key is pressed.
- A saved palette color can be applied to **Selected keys**, **Current row**, or **All keys**.
- **Save current** adds the selected key's current idle color to the reusable palette.

The included profiles use a functional color language:

| Color | Intended meaning |
| --- | --- |
| Green `#00FF66` | Safe, start, create, confirm, or increase |
| Lime `#B8FF00` | Navigation and movement |
| Yellow `#FFD000` | Neutral toggle, selection, or reversible edit |
| Orange `#FF7A00` | Caution or a system-changing action |
| Red `#FF2020` | Stop, close, remove, mute, or destructive action |
| White `#FFFFFF` | Standard pressed-key feedback |

## Build an action sequence

A control can contain up to 16 steps. The firmware runs them in the displayed order. Use **Add step**, double-click a step to edit it, drag steps to reorder them, or use **Move up** and **Move down**.

The bundled Manjaro command screens use a three-step template: open a terminal
with `Super+Enter`, wait 800 ms for focus, then type the command without pressing
Enter. Pamac is deliberately run without `sudo` because it performs its own
privilege escalation and Manjaro warns against running Pamac itself as root.
Commands that directly require root, such as `pacman`, `paccache`, and
system-level `systemctl` changes, include `sudo`.

Five step types are available:

| Type | Use it for | Example |
| --- | --- | --- |
| **hotkey** | One key or a simultaneous key combination | `CONTROL, SHIFT, P` |
| **text** | Text or a command typed into the focused application | `pamac checkupdates` |
| **consumer** | Media keys understood by the operating system | `VOLUME_INCREMENT` |
| **mouse** | A mouse-button click, pointer movement, or wheel movement | Left click or wheel `-1` |
| **delay** | A pause between macro steps | `800 ms` after opening a terminal |

The hotkey picker uses CircuitPython HID names such as `CONTROL`, `SHIFT`, `ALT`, `GUI`, `ENTER`, and `F5`. A hotkey step sends its listed keys together. If keys must happen one after another, create separate steps.

### Example: launch an application

A typical i3 application launcher macro uses:

1. A **hotkey** step containing `GUI, D`.
2. A short **delay** so the launcher can receive focus.
3. A **text** step containing the application command.
4. A **hotkey** step containing `ENTER`.

### Example: delayed shutdown

The included System Control profile opens a terminal, waits for it to focus, types `shutdown +60`, and presses Enter. Red actions such as immediate shutdown deserve an obvious label and color because **Run on device** and a physical key press execute the sequence for real.

## Preview and test safely

- **Safe preview** displays a readable list of the selected control's steps and sends nothing.
- **Run on device** asks for confirmation, then tells the MacroPad to send the action to the currently focused application.
- **Preview RGB** changes only the temporary LED display and does not alter the stored profile library.

Before testing text, terminal, close, reboot, or shutdown actions, focus a harmless destination and read the safe preview first. Terminal and SSH templates intentionally omit Enter where commands require user review.

## Multiple devices

Each connected MacroPad appears separately by UID. You can give each one a friendly name with **Name Device**. Import, preview, compare, health, backup, repair, and sync operations always target the device selected in the toolbar.

To copy the same library to two devices:

1. Finish and save the local library.
2. Select the first device and choose **Compare**, then **Sync Device**.
3. Select the second device and repeat **Compare** and **Sync Device**.

Device-specific backups are stored separately by UID, so restoring one unit does not overwrite another unit's backup history.

## Keyboard layouts

Choose the layout that the host operating system uses. The firmware supports **US** and **German** mappings. This matters for typed text and characters whose physical HID key differs between the layouts. Common modifier shortcuts such as Ctrl+C remain familiar, but punctuation and Y/Z positions can differ.

Synchronize after changing the layout. If a typed command produces the wrong characters, confirm both the GUI layout selector and the desktop environment's active keyboard layout.

## Undo, copy, and editing shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+Q` | Exit the configurator |
| `Ctrl+Z` | Undo |
| `Ctrl+Shift+Z` | Redo |
| `Ctrl+Alt+C` | Copy the selected control |
| `Ctrl+Alt+V` | Paste to the selected control or selected keys |

**Swap…** exchanges the selected control with another key or the encoder press. Copy/paste duplicates an assignment, while swap moves two complete assignments, including RGB values where applicable.

## Troubleshooting

### No MacroPad is listed

Confirm that the board is running CircuitPython and that its `CIRCUITPY` drive is mounted, then choose **Refresh**. A board in UF2 bootloader mode appears as `RPI-RP2` and is not treated as a configurable MacroPad.

### Preview or action testing fails

The drive may be mounted while the USB serial port is busy or unavailable. Close serial monitors and other tools using the MacroPad, reconnect it, and run **Device Health**.

### Device profiles do not match the editor

Use **Compare** to determine the direction of the difference. Choose **Import Device** to keep the device copy, or **Sync Device** to keep the local copy.

### A synchronized profile appears stale

Wait for the drive activity to finish, reconnect the device if necessary, choose **Refresh**, and compare again. Profile writes use revisioned files and commit the index last so an interrupted USB write does not partially replace the active profile set.

### A key types the wrong symbol

Select the correct **Layout**, synchronize again, and confirm the host desktop uses the same layout. For application shortcuts, also verify that the application has not customized the default binding.

### Firmware files are missing

Run **Device Health** first. **Repair Firmware** can reinstall required libraries and project firmware, but the CircuitPython filesystem must be writable and the application environment must contain `circup`.

## Included profiles

The repository ships with application, desktop, terminal, SSH, audio, quick-launch, and system-control mappings. See [Included MacroPad profiles](../PROFILE_LAYOUTS.md) for the complete key map and shortcut sources.
