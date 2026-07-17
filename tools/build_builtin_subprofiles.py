#!/usr/bin/env python3
"""Build the maintained three-layout maps for every bundled profile."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROFILE_ROOT = ROOT / "device" / "profiles"

GREEN = "#00FF66"
LIME = "#B8FF00"
YELLOW = "#FFD000"
ORANGE = "#FF7A00"
RED = "#FF2020"
WHITE = "#FFFFFF"


def control(name, label, color, steps):
    return {
        "name": name,
        "oled_label": label,
        "idle_color": color,
        "pressed_color": WHITE,
        "steps": steps,
    }


def hotkey(name, label, color, *keys):
    return control(name, label, color, [{"type": "hotkey", "keys": list(keys)}])


def text(name, label, color, value):
    return control(name, label, color, [{"type": "text", "text": value}])


def consumer(name, label, color, code, repeat=1):
    return control(
        name,
        label,
        color,
        [{"type": "consumer", "code": code} for _ in range(repeat)],
    )


def launcher(name, label, color, command):
    return control(
        name,
        label,
        color,
        [
            {"type": "hotkey", "keys": ["GUI", "D"]},
            {"type": "delay", "ms": 250},
            {"type": "text", "text": command},
            {"type": "hotkey", "keys": ["ENTER"]},
        ],
    )


def terminal(name, label, color, command):
    return control(
        name,
        label,
        color,
        [
            {"type": "hotkey", "keys": ["GUI", "ENTER"]},
            {"type": "delay", "ms": 800},
            {"type": "text", "text": command},
            {"type": "hotkey", "keys": ["ENTER"]},
        ],
    )


def terminal_template(name, label, color, command):
    """Open a terminal and type a command without executing it."""
    return control(
        name,
        label,
        color,
        [
            {"type": "hotkey", "keys": ["GUI", "ENTER"]},
            {"type": "delay", "ms": 800},
            {"type": "text", "text": command},
        ],
    )


def layout(name, icon, keys):
    if len(keys) != 12:
        raise ValueError(f"{name} must define exactly 12 keys")
    return {"name": name, "icon": icon, "brightness": 5, "keys": keys}


SPECS = {
    "editing": (
        "General",
        [
            layout(
                "Navigation",
                "NV",
                [
                    hotkey("Cursor left", "LEFT", LIME, "LEFT_ARROW"),
                    hotkey("Cursor up", "UP", LIME, "UP_ARROW"),
                    hotkey("Cursor right", "RIGHT", LIME, "RIGHT_ARROW"),
                    hotkey("Previous word", "WORD-", LIME, "CONTROL", "LEFT_ARROW"),
                    hotkey("Cursor down", "DOWN", LIME, "DOWN_ARROW"),
                    hotkey("Next word", "WORD+", LIME, "CONTROL", "RIGHT_ARROW"),
                    hotkey("Line start", "HOME", LIME, "HOME"),
                    hotkey("Page up", "PGUP", LIME, "PAGE_UP"),
                    hotkey("Line end", "END", LIME, "END"),
                    hotkey("Document start", "DOC-", LIME, "CONTROL", "HOME"),
                    hotkey("Page down", "PGDN", LIME, "PAGE_DOWN"),
                    hotkey("Document end", "DOC+", LIME, "CONTROL", "END"),
                ],
            ),
            layout(
                "Document",
                "DC",
                [
                    hotkey("New document", "NEW", GREEN, "CONTROL", "N"),
                    hotkey("Open document", "OPEN", GREEN, "CONTROL", "O"),
                    hotkey("Save as", "SAVEAS", GREEN, "CONTROL", "SHIFT", "S"),
                    hotkey("Bold", "BOLD", YELLOW, "CONTROL", "B"),
                    hotkey("Italic", "ITALIC", YELLOW, "CONTROL", "I"),
                    hotkey("Underline", "UNDER", YELLOW, "CONTROL", "U"),
                    hotkey("Indent", "INDENT", YELLOW, "TAB"),
                    hotkey("Outdent", "OUTDNT", YELLOW, "SHIFT", "TAB"),
                    hotkey("Delete previous word", "DEL-W", ORANGE, "CONTROL", "BACKSPACE"),
                    hotkey("Print", "PRINT", GREEN, "CONTROL", "P"),
                    hotkey("Replace", "REPL", YELLOW, "CONTROL", "H"),
                    hotkey("Close document", "CLOSE", RED, "CONTROL", "W"),
                ],
            ),
        ],
    ),
    "media": (
        "Media",
        [
            layout(
                "Navigation",
                "NV",
                [
                    hotkey("Left", "LEFT", LIME, "LEFT_ARROW"),
                    hotkey("Up", "UP", LIME, "UP_ARROW"),
                    hotkey("Right", "RIGHT", LIME, "RIGHT_ARROW"),
                    hotkey("Back", "BACK", LIME, "ALT", "LEFT_ARROW"),
                    hotkey("Down", "DOWN", LIME, "DOWN_ARROW"),
                    hotkey("Forward", "FWD", LIME, "ALT", "RIGHT_ARROW"),
                    hotkey("Home", "HOME", LIME, "HOME"),
                    hotkey("Page up", "PGUP", LIME, "PAGE_UP"),
                    hotkey("End", "END", LIME, "END"),
                    hotkey("Escape", "ESC", ORANGE, "ESCAPE"),
                    hotkey("Page down", "PGDN", LIME, "PAGE_DOWN"),
                    hotkey("Activate", "ENTER", GREEN, "ENTER"),
                ],
            ),
            layout(
                "Presentation",
                "PR",
                [
                    hotkey("Previous slide", "SLIDE-", LIME, "PAGE_UP"),
                    hotkey("Start presentation", "START", GREEN, "F5"),
                    hotkey("Next slide", "SLIDE+", LIME, "PAGE_DOWN"),
                    hotkey("First slide", "FIRST", LIME, "HOME"),
                    hotkey("Blank screen", "BLANK", YELLOW, "B"),
                    hotkey("Last slide", "LAST", LIME, "END"),
                    hotkey("Previous item", "ITEM-", LIME, "SHIFT", "TAB"),
                    hotkey("Activate item", "ENTER", GREEN, "ENTER"),
                    hotkey("Next item", "ITEM+", LIME, "TAB"),
                    hotkey("Zoom out", "ZOOM-", YELLOW, "CONTROL", "MINUS"),
                    hotkey("Exit presentation", "EXIT", RED, "ESCAPE"),
                    hotkey("Zoom in", "ZOOM+", YELLOW, "CONTROL", "EQUALS"),
                ],
            ),
        ],
    ),
    "vscode": (
        "General",
        [
            layout(
                "Navigation",
                "NV",
                [
                    hotkey("Go to file", "FILE", LIME, "CONTROL", "P"),
                    hotkey("Go to line", "LINE", LIME, "CONTROL", "G"),
                    hotkey("Go to symbol", "SYMBOL", LIME, "CONTROL", "SHIFT", "O"),
                    hotkey("Go to definition", "DEF", LIME, "F12"),
                    hotkey("Go to references", "REFS", LIME, "SHIFT", "F12"),
                    hotkey("Navigate back", "BACK", LIME, "ALT", "LEFT_ARROW"),
                    hotkey("Navigate forward", "FWD", LIME, "ALT", "RIGHT_ARROW"),
                    hotkey("Next problem", "ERR+", ORANGE, "F8"),
                    hotkey("Previous problem", "ERR-", ORANGE, "SHIFT", "F8"),
                    hotkey("Previous editor", "EDIT-", LIME, "CONTROL", "PAGE_UP"),
                    hotkey("Next editor", "EDIT+", LIME, "CONTROL", "PAGE_DOWN"),
                    hotkey("Toggle terminal", "TERM", YELLOW, "CONTROL", "GRAVE_ACCENT"),
                ],
            ),
            layout(
                "Code and Debug",
                "DB",
                [
                    hotkey("Quick fix", "FIX", YELLOW, "CONTROL", "PERIOD"),
                    hotkey("Rename symbol", "RENAME", ORANGE, "F2"),
                    hotkey("Format document", "FORMAT", YELLOW, "SHIFT", "ALT", "F"),
                    hotkey("Delete line", "DEL-LN", RED, "CONTROL", "SHIFT", "K"),
                    hotkey("Insert line below", "LINE+", GREEN, "CONTROL", "ENTER"),
                    hotkey("Toggle comment", "COMENT", YELLOW, "CONTROL", "FORWARD_SLASH"),
                    hotkey("Start debugging", "START", GREEN, "F5"),
                    hotkey("Stop debugging", "STOP", RED, "SHIFT", "F5"),
                    hotkey("Step over", "OVER", LIME, "F10"),
                    hotkey("Step into", "INTO", LIME, "F11"),
                    hotkey("Step out", "OUT", LIME, "SHIFT", "F11"),
                    hotkey("Toggle breakpoint", "BREAK", YELLOW, "F9"),
                ],
            ),
        ],
    ),
    "firefox": (
        "Browse",
        [
            layout(
                "Tabs",
                "TB",
                [
                    hotkey("New tab", "NEW", GREEN, "CONTROL", "T"),
                    hotkey("Close tab", "CLOSE", RED, "CONTROL", "W"),
                    hotkey("Restore tab", "REOPEN", GREEN, "CONTROL", "SHIFT", "T"),
                    hotkey("Tab 1", "TAB-1", LIME, "CONTROL", "ONE"),
                    hotkey("Tab 2", "TAB-2", LIME, "CONTROL", "TWO"),
                    hotkey("Tab 3", "TAB-3", LIME, "CONTROL", "THREE"),
                    hotkey("Tab 4", "TAB-4", LIME, "CONTROL", "FOUR"),
                    hotkey("Tab 5", "TAB-5", LIME, "CONTROL", "FIVE"),
                    hotkey("Tab 6", "TAB-6", LIME, "CONTROL", "SIX"),
                    hotkey("Previous tab", "TAB-", LIME, "CONTROL", "PAGE_UP"),
                    hotkey("Last tab", "LAST", LIME, "CONTROL", "NINE"),
                    hotkey("Next tab", "TAB+", LIME, "CONTROL", "PAGE_DOWN"),
                ],
            ),
            layout(
                "Tools",
                "TL",
                [
                    hotkey("History sidebar", "HIST", LIME, "CONTROL", "H"),
                    hotkey("Bookmarks library", "BOOKS", LIME, "CONTROL", "SHIFT", "O"),
                    hotkey("Bookmark page", "BOOK", GREEN, "CONTROL", "D"),
                    hotkey("Downloads", "DOWN", LIME, "CONTROL", "J"),
                    hotkey("Add-ons", "ADDON", LIME, "CONTROL", "SHIFT", "A"),
                    hotkey("Developer tools", "DEV", YELLOW, "F12"),
                    hotkey("Web console", "CONSOL", YELLOW, "CONTROL", "SHIFT", "K"),
                    hotkey("Inspector", "INSPEC", YELLOW, "CONTROL", "SHIFT", "C"),
                    hotkey("Screenshot", "SHOT", GREEN, "CONTROL", "SHIFT", "S"),
                    hotkey("Page source", "SOURCE", LIME, "CONTROL", "U"),
                    hotkey("Print", "PRINT", GREEN, "CONTROL", "P"),
                    hotkey("Save page", "SAVE", GREEN, "CONTROL", "S"),
                ],
            ),
        ],
    ),
    "vlc": (
        "Playback",
        [
            layout(
                "Seek",
                "SK",
                [
                    hotkey("Very short back", "VSBACK", LIME, "SHIFT", "LEFT_ARROW"),
                    hotkey("Play pause", "PLAY", GREEN, "SPACE"),
                    hotkey("Very short forward", "VSFWD", LIME, "SHIFT", "RIGHT_ARROW"),
                    hotkey("Short back", "S-BACK", LIME, "ALT", "LEFT_ARROW"),
                    hotkey("Stop", "STOP", RED, "S"),
                    hotkey("Short forward", "S-FWD", LIME, "ALT", "RIGHT_ARROW"),
                    hotkey("Medium back", "M-BACK", LIME, "CONTROL", "LEFT_ARROW"),
                    hotkey("Previous", "PREV", LIME, "P"),
                    hotkey("Medium forward", "M-FWD", LIME, "CONTROL", "RIGHT_ARROW"),
                    hotkey("Long back", "L-BACK", LIME, "CONTROL", "ALT", "LEFT_ARROW"),
                    hotkey("Next", "NEXT", LIME, "N"),
                    hotkey("Long forward", "L-FWD", LIME, "CONTROL", "ALT", "RIGHT_ARROW"),
                ],
            ),
            layout(
                "View and Audio",
                "VA",
                [
                    hotkey("Fullscreen", "FULL", YELLOW, "F"),
                    hotkey("Minimal interface", "MINI", YELLOW, "CONTROL", "H"),
                    hotkey("Playlist", "LIST", LIME, "CONTROL", "L"),
                    hotkey("Snapshot", "SHOT", GREEN, "SHIFT", "S"),
                    hotkey("Aspect ratio", "ASPECT", YELLOW, "A"),
                    hotkey("Crop mode", "CROP", YELLOW, "C"),
                    hotkey("Subtitle track", "SUB", YELLOW, "V"),
                    hotkey("Audio track", "AUDIO", YELLOW, "B"),
                    hotkey("Deinterlace", "DEINT", YELLOW, "D"),
                    hotkey("Preferences", "PREF", ORANGE, "CONTROL", "P"),
                    hotkey("Effects", "EFFECT", YELLOW, "CONTROL", "E"),
                    hotkey("Mute", "MUTE", RED, "M"),
                ],
            ),
        ],
    ),
    "discord": (
        "General",
        [
            layout(
                "Navigation",
                "NV",
                [
                    hotkey("Previous server", "SRV-", LIME, "CONTROL", "ALT", "LEFT_ARROW"),
                    hotkey("Quick switcher", "QUICK", GREEN, "CONTROL", "K"),
                    hotkey("Next server", "SRV+", LIME, "CONTROL", "ALT", "RIGHT_ARROW"),
                    hotkey("Previous channel", "CH-", LIME, "ALT", "UP_ARROW"),
                    hotkey("Next section", "SECT+", LIME, "F6"),
                    hotkey("Next channel", "CH+", LIME, "ALT", "DOWN_ARROW"),
                    hotkey("History up", "HIST-", LIME, "CONTROL", "UP_ARROW"),
                    hotkey("Previous section", "SECT-", LIME, "SHIFT", "F6"),
                    hotkey("History down", "HIST+", LIME, "CONTROL", "DOWN_ARROW"),
                    hotkey("Previous element", "ITEM-", LIME, "SHIFT", "TAB"),
                    hotkey("Activate", "ENTER", GREEN, "ENTER"),
                    hotkey("Next element", "ITEM+", LIME, "TAB"),
                ],
            ),
            layout(
                "Messages",
                "MS",
                [
                    hotkey("Edit last message", "EDIT", ORANGE, "SHIFT", "UP_ARROW"),
                    hotkey("Reply focused message", "REPLY", GREEN, "R"),
                    hotkey("Quote focused message", "QUOTE", GREEN, "Q"),
                    hotkey("React to message", "REACT", GREEN, "SHIFT", "EQUALS"),
                    hotkey("Edit focused message", "EDIT-F", ORANGE, "E"),
                    hotkey("Delete focused message", "DELETE", RED, "BACKSPACE"),
                    hotkey("Pin focused message", "PIN", YELLOW, "P"),
                    hotkey("Copy message", "COPY", GREEN, "CONTROL", "C"),
                    hotkey("Mark unread", "UNREAD", YELLOW, "ALT", "ENTER"),
                    hotkey("Emoji picker", "EMOJI", GREEN, "CONTROL", "E"),
                    hotkey("GIF picker", "GIF", GREEN, "CONTROL", "G"),
                    hotkey("Upload file", "UPLOAD", GREEN, "CONTROL", "SHIFT", "U"),
                ],
            ),
        ],
    ),
    "lm-studio": (
        "General",
        [
            layout(
                "Chat Editing",
                "CE",
                [
                    hotkey("New chat", "CHAT", GREEN, "CONTROL", "N"),
                    hotkey("New chat folder", "FOLDER", GREEN, "CONTROL", "SHIFT", "N"),
                    hotkey("Find", "FIND", LIME, "CONTROL", "F"),
                    hotkey("Copy", "COPY", GREEN, "CONTROL", "C"),
                    hotkey("Paste", "PASTE", GREEN, "CONTROL", "V"),
                    hotkey("Cut", "CUT", ORANGE, "CONTROL", "X"),
                    hotkey("Undo", "UNDO", YELLOW, "CONTROL", "Z"),
                    hotkey("Redo", "REDO", YELLOW, "CONTROL", "Y"),
                    hotkey("Select all", "ALL", YELLOW, "CONTROL", "A"),
                    hotkey("Settings", "SET", ORANGE, "CONTROL", "COMMA"),
                    hotkey("Runtimes", "RUN", ORANGE, "CONTROL", "SHIFT", "R"),
                    control(
                        "Select theme",
                        "THEME",
                        YELLOW,
                        [
                            {"type": "hotkey", "keys": ["CONTROL", "K"]},
                            {"type": "delay", "ms": 80},
                            {"type": "hotkey", "keys": ["T"]},
                        ],
                    ),
                ],
            ),
            layout(
                "UI Navigation",
                "NV",
                [
                    hotkey("Previous control", "ITEM-", LIME, "SHIFT", "TAB"),
                    hotkey("Up", "UP", LIME, "UP_ARROW"),
                    hotkey("Next control", "ITEM+", LIME, "TAB"),
                    hotkey("Left", "LEFT", LIME, "LEFT_ARROW"),
                    hotkey("Activate", "ENTER", GREEN, "ENTER"),
                    hotkey("Right", "RIGHT", LIME, "RIGHT_ARROW"),
                    hotkey("Page up", "PGUP", LIME, "PAGE_UP"),
                    hotkey("Down", "DOWN", LIME, "DOWN_ARROW"),
                    hotkey("Page down", "PGDN", LIME, "PAGE_DOWN"),
                    hotkey("First item", "FIRST", LIME, "HOME"),
                    hotkey("Cancel", "ESC", ORANGE, "ESCAPE"),
                    hotkey("Last item", "LAST", LIME, "END"),
                ],
            ),
        ],
    ),
    "terminal-manjaro": (
        "Packages",
        [
            layout(
                "System",
                "SY",
                [
                    text("Service status", "STATUS", LIME, "systemctl status "),
                    text("Restart service", "RE-ST", ORANGE, "sudo systemctl restart "),
                    text("Stop service", "STOP", RED, "sudo systemctl stop "),
                    text("Enable service", "ENABLE", GREEN, "sudo systemctl enable --now "),
                    text("Disable service", "DISABL", ORANGE, "sudo systemctl disable --now "),
                    text("Service logs", "SVCLOG", LIME, "journalctl -u "),
                    text("Boot errors", "ERRORS", LIME, "journalctl -b -p err"),
                    text("Failed services", "FAILED", LIME, "systemctl --failed"),
                    text("System uptime", "UPTIME", LIME, "uptime"),
                    text("Memory usage", "MEM", LIME, "free -h"),
                    text("Disk usage", "DISK", LIME, "df -h"),
                    text("Block devices", "BLOCK", LIME, "lsblk -f"),
                ],
            ),
            layout(
                "Files and Network",
                "FN",
                [
                    text("Working directory", "PWD", LIME, "pwd"),
                    text("List files", "LIST", LIME, "ls -lah"),
                    text("Change directory", "CD", LIME, "cd "),
                    text("Create directory", "MKDIR", GREEN, "mkdir -p "),
                    text("Copy files", "COPY", GREEN, "cp -av "),
                    text("Move files", "MOVE", ORANGE, "mv -iv "),
                    text("Search text", "RG", LIME, "rg '' "),
                    text("Find files", "FIND", LIME, "find . -name ''"),
                    text("IP addresses", "IP", LIME, "ip -brief address"),
                    text("Listening ports", "PORTS", LIME, "ss -tulpn"),
                    text("Ping host", "PING", LIME, "ping -c 4 "),
                    text("HTTP headers", "HTTP", LIME, "curl -I "),
                ],
            ),
        ],
    ),
    "comfyui": (
        "Workflow",
        [
            layout(
                "Canvas",
                "CV",
                [
                    hotkey("Zoom in", "ZOOM+", LIME, "ALT", "EQUALS"),
                    hotkey("Fit selected", "FIT", LIME, "PERIOD"),
                    hotkey("Zoom out", "ZOOM-", LIME, "ALT", "MINUS"),
                    hotkey("Pin selected", "PIN", YELLOW, "P"),
                    hotkey("Focus mode", "FOCUS", YELLOW, "F"),
                    hotkey("Refresh nodes", "REFRSH", ORANGE, "R"),
                    hotkey("Queue sidebar", "QUEUE", LIME, "Q"),
                    hotkey("Workflow sidebar", "WORK", LIME, "W"),
                    hotkey("Node library", "NODES", LIME, "N"),
                    hotkey("Model library", "MODELS", LIME, "M"),
                    hotkey("Log panel", "LOG", LIME, "CONTROL", "GRAVE_ACCENT"),
                    hotkey("Settings", "SET", ORANGE, "CONTROL", "COMMA"),
                ],
            ),
            layout(
                "Node Editing",
                "ND",
                [
                    hotkey("Copy nodes", "COPY", GREEN, "CONTROL", "C"),
                    hotkey("Paste nodes", "PASTE", GREEN, "CONTROL", "V"),
                    hotkey("Paste with links", "LINKS", GREEN, "CONTROL", "SHIFT", "V"),
                    hotkey("Frame nodes", "FRAME", GREEN, "CONTROL", "G"),
                    hotkey("Delete nodes", "DELETE", RED, "DELETE"),
                    hotkey("Collapse nodes", "FOLD", YELLOW, "ALT", "C"),
                    hotkey("Mute nodes", "MUTE", RED, "CONTROL", "M"),
                    hotkey("Bypass nodes", "BYPASS", YELLOW, "CONTROL", "B"),
                    hotkey("Select all nodes", "ALL", YELLOW, "CONTROL", "A"),
                    hotkey("Undo", "UNDO", YELLOW, "CONTROL", "Z"),
                    hotkey("Redo", "REDO", YELLOW, "CONTROL", "Y"),
                    hotkey("Queue prompt", "QUEUE", GREEN, "CONTROL", "ENTER"),
                ],
            ),
        ],
    ),
    "ssh": (
        "Connections",
        [
            layout(
                "Keys and Config",
                "KC",
                [
                    text("Generate Ed25519 key", "KEYGEN", GREEN, "ssh-keygen -t ed25519 -C user@host"),
                    text("Add key to agent", "AGENT", GREEN, "ssh-add ~/.ssh/id_ed25519"),
                    text("Copy public key", "COPYID", GREEN, "ssh-copy-id user@host"),
                    text("Key fingerprint", "FINGER", LIME, "ssh-keygen -lf ~/.ssh/id_ed25519.pub"),
                    text("Remove known host", "RMHOST", ORANGE, "ssh-keygen -R host"),
                    text("Secure SSH folder", "CHMOD", ORANGE, "chmod 700 ~/.ssh && chmod 600 ~/.ssh/config"),
                    text("Edit SSH config", "EDIT", ORANGE, "nano ~/.ssh/config"),
                    text("List SSH files", "LIST", LIME, "ls -la ~/.ssh"),
                    text("Start SSH agent", "START", GREEN, "eval \"$(ssh-agent -s)\""),
                    text("List agent keys", "KEYS", LIME, "ssh-add -l"),
                    text("Known hosts", "KNOWN", LIME, "less ~/.ssh/known_hosts"),
                    text("Resolved config", "CONFIG", LIME, "ssh -G user@host"),
                ],
            ),
            layout(
                "Transfer and Diagnose",
                "TD",
                [
                    text("SCP upload", "UPLOAD", GREEN, "scp file user@host:/path/"),
                    text("SCP download", "DOWN", GREEN, "scp user@host:/path/file ."),
                    text("SCP directory", "SCP-R", GREEN, "scp -r folder user@host:/path/"),
                    text("Rsync upload", "RS-UP", GREEN, "rsync -avz folder/ user@host:/path/"),
                    text("Rsync download", "RS-DN", GREEN, "rsync -avz user@host:/path/ folder/"),
                    text("SFTP session", "SFTP", GREEN, "sftp user@host"),
                    text("Verbose SSH", "SSH-V", LIME, "ssh -vvv user@host"),
                    text("Resolved config", "CONFIG", LIME, "ssh -G user@host"),
                    text("Test SSH port", "PORT", LIME, "nc -vz host 22"),
                    text("Ping host", "PING", LIME, "ping -c 4 host"),
                    text("Trace route", "TRACE", LIME, "traceroute host"),
                    text("Remote command", "REMOTE", ORANGE, "ssh user@host 'command'"),
                ],
            ),
        ],
    ),
    "audio-controls": (
        "Playback",
        [
            layout(
                "Fine Volume",
                "VL",
                [
                    consumer("Mute", "MUTE", RED, "MUTE"),
                    consumer("Volume down 1", "VOL-1", ORANGE, "VOLUME_DECREMENT"),
                    consumer("Volume up 1", "VOL+1", GREEN, "VOLUME_INCREMENT"),
                    consumer("Volume down 2", "VOL-2", ORANGE, "VOLUME_DECREMENT", 2),
                    consumer("Play pause", "PLAY", GREEN, "PLAY_PAUSE"),
                    consumer("Volume up 2", "VOL+2", GREEN, "VOLUME_INCREMENT", 2),
                    consumer("Volume down 3", "VOL-3", ORANGE, "VOLUME_DECREMENT", 3),
                    consumer("Stop", "STOP", RED, "STOP"),
                    consumer("Volume up 3", "VOL+3", GREEN, "VOLUME_INCREMENT", 3),
                    consumer("Volume down 5", "VOL-5", ORANGE, "VOLUME_DECREMENT", 5),
                    consumer("Mute toggle", "MUTE", RED, "MUTE"),
                    consumer("Volume up 5", "VOL+5", GREEN, "VOLUME_INCREMENT", 5),
                ],
            ),
            layout(
                "Transport",
                "TR",
                [
                    consumer("Previous track", "PREV", LIME, "SCAN_PREVIOUS_TRACK"),
                    consumer("Play pause", "PLAY", GREEN, "PLAY_PAUSE"),
                    consumer("Next track", "NEXT", LIME, "SCAN_NEXT_TRACK"),
                    consumer("Stop", "STOP", RED, "STOP"),
                    consumer("Record", "REC", RED, "RECORD"),
                    consumer("Eject", "EJECT", ORANGE, "EJECT"),
                    consumer("Volume down", "VOL-", ORANGE, "VOLUME_DECREMENT"),
                    consumer("Mute", "MUTE", RED, "MUTE"),
                    consumer("Volume up", "VOL+", GREEN, "VOLUME_INCREMENT"),
                    consumer("Previous again", "PREV", LIME, "SCAN_PREVIOUS_TRACK"),
                    consumer("Play again", "PLAY", GREEN, "PLAY_PAUSE"),
                    consumer("Next again", "NEXT", LIME, "SCAN_NEXT_TRACK"),
                ],
            ),
        ],
    ),
    "quicklaunch": (
        "Apps",
        [
            layout(
                "Web",
                "WB",
                [
                    launcher("Open Gmail", "GMAIL", GREEN, "firefox https://mail.google.com"),
                    launcher("Open GitHub", "GITHUB", GREEN, "firefox https://github.com"),
                    launcher("Open YouTube", "YOUTUB", GREEN, "firefox https://youtube.com"),
                    launcher("Open ChatGPT", "CHATGP", GREEN, "firefox https://chatgpt.com"),
                    launcher("Open Hugging Face", "HUGGNG", GREEN, "firefox https://huggingface.co"),
                    launcher("Open Reddit", "REDDIT", GREEN, "firefox https://reddit.com"),
                    launcher("Open Google Drive", "DRIVE", GREEN, "firefox https://drive.google.com"),
                    launcher("Open Calendar", "CAL", GREEN, "firefox https://calendar.google.com"),
                    launcher("Open Maps", "MAPS", GREEN, "firefox https://maps.google.com"),
                    launcher("Open Wikipedia", "WIKI", GREEN, "firefox https://wikipedia.org"),
                    launcher("Open weather", "WEATHR", GREEN, "firefox https://weather.com"),
                    launcher("Open localhost", "LOCAL", GREEN, "firefox http://localhost:8188"),
                ],
            ),
            layout(
                "Tools",
                "TL",
                [
                    launcher("Launch Terminal", "TERM", GREEN, "alacritty"),
                    launcher("Launch Caja", "CAJA", GREEN, "caja"),
                    launcher("Launch VS Code", "VSCODE", GREEN, "code"),
                    launcher("Launch VLC", "VLC", GREEN, "vlc"),
                    launcher("Launch Discord", "DISCRD", GREEN, "discord"),
                    launcher("Launch LM Studio", "LMSTU", GREEN, "lm-studio"),
                    launcher("Audio mixer", "AUDIO", GREEN, "pavucontrol"),
                    launcher("System settings", "SET", ORANGE, "xfce4-settings-manager"),
                    launcher("Calculator", "CALC", GREEN, "qalculate-gtk"),
                    launcher("Image editor", "GIMP", GREEN, "gimp"),
                    launcher("Office suite", "OFFICE", GREEN, "libreoffice"),
                    terminal("System monitor", "MON", GREEN, "btop"),
                ],
            ),
        ],
    ),
    "system-control": (
        "Power",
        [
            layout(
                "Session",
                "SE",
                [
                    launcher("Lock screen", "LOCK", ORANGE, "i3lock"),
                    terminal("Suspend", "SUSP", ORANGE, "systemctl suspend"),
                    terminal("Hibernate", "HIBER", ORANGE, "systemctl hibernate"),
                    hotkey("i3 logout prompt", "LOGOUT", RED, "GUI", "SHIFT", "E"),
                    hotkey("Restart i3", "I3-RST", ORANGE, "GUI", "SHIFT", "R"),
                    hotkey("Reload i3 config", "I3-CFG", YELLOW, "GUI", "SHIFT", "C"),
                    hotkey("Open terminal", "TERM", GREEN, "GUI", "ENTER"),
                    hotkey("Application launcher", "MENU", GREEN, "GUI", "D"),
                    consumer("Mute", "MUTE", RED, "MUTE"),
                    consumer("Volume down", "VOL-", ORANGE, "VOLUME_DECREMENT"),
                    consumer("Play pause", "PLAY", GREEN, "PLAY_PAUSE"),
                    consumer("Volume up", "VOL+", GREEN, "VOLUME_INCREMENT"),
                ],
            ),
            layout(
                "Diagnostics",
                "DG",
                [
                    terminal("System uptime", "UPTIME", LIME, "uptime"),
                    terminal("Disk usage", "DISK", LIME, "df -h"),
                    terminal("Memory usage", "MEM", LIME, "free -h"),
                    terminal("Failed services", "FAILED", ORANGE, "systemctl --failed"),
                    terminal("Boot errors", "ERRORS", ORANGE, "journalctl -b -p err"),
                    terminal("Temperatures", "TEMPS", LIME, "sensors"),
                    terminal("IP addresses", "IP", LIME, "ip -brief address"),
                    terminal("Listening ports", "PORTS", LIME, "ss -tulpn"),
                    terminal("Block devices", "BLOCK", LIME, "lsblk -f"),
                    terminal("Kernel version", "KERNEL", LIME, "uname -a"),
                    terminal("Recent boots", "BOOTS", LIME, "journalctl --list-boots"),
                    terminal("Network check", "PING", LIME, "ping -c 4 1.1.1.1"),
                ],
            ),
        ],
    ),
    "caja": (
        "Files",
        [
            layout(
                "Navigation",
                "NV",
                [
                    hotkey("Back", "BACK", LIME, "ALT", "LEFT_ARROW"),
                    hotkey("Up one folder", "UP", LIME, "ALT", "UP_ARROW"),
                    hotkey("Forward", "FWD", LIME, "ALT", "RIGHT_ARROW"),
                    hotkey("Home folder", "HOME", LIME, "ALT", "HOME"),
                    hotkey("Reload", "RELOAD", LIME, "CONTROL", "R"),
                    hotkey("Edit location", "LOC", LIME, "CONTROL", "L"),
                    hotkey("Search", "SEARCH", LIME, "CONTROL", "F"),
                    hotkey("Previous tab", "TAB-", LIME, "CONTROL", "PAGE_UP"),
                    hotkey("Next tab", "TAB+", LIME, "CONTROL", "PAGE_DOWN"),
                    hotkey("First item", "FIRST", LIME, "HOME"),
                    hotkey("Open item", "OPEN", GREEN, "ENTER"),
                    hotkey("Last item", "LAST", LIME, "END"),
                ],
            ),
            layout(
                "View",
                "VW",
                [
                    hotkey("Icon view", "ICONS", YELLOW, "CONTROL", "ONE"),
                    hotkey("List view", "LIST", YELLOW, "CONTROL", "TWO"),
                    hotkey("Compact view", "CMPACT", YELLOW, "CONTROL", "THREE"),
                    hotkey("Zoom in", "ZOOM+", LIME, "CONTROL", "EQUALS"),
                    hotkey("Normal zoom", "ZOOM0", LIME, "CONTROL", "ZERO"),
                    hotkey("Zoom out", "ZOOM-", LIME, "CONTROL", "MINUS"),
                    hotkey("Show hidden files", "HIDDEN", YELLOW, "CONTROL", "H"),
                    hotkey("Toggle side pane", "SIDE", YELLOW, "F9"),
                    hotkey("Toggle extra pane", "SPLIT", YELLOW, "F3"),
                    hotkey("Computer location", "COMPUT", LIME, "CONTROL", "L"),
                    hotkey("Refresh view", "REFRSH", LIME, "F5"),
                    hotkey("Escape", "ESC", ORANGE, "ESCAPE"),
                ],
            ),
        ],
    ),
    "krita": (
        "Painting",
        [
            layout(
                "Canvas",
                "CV",
                [
                    hotkey("Canvas only mode", "CANVAS", YELLOW, "TAB"),
                    hotkey("Full screen", "FULL", YELLOW, "CONTROL", "SHIFT", "F"),
                    hotkey("Mirror canvas", "MIRROR", YELLOW, "M"),
                    hotkey("Reset canvas", "RESET", LIME, "ONE"),
                    hotkey("Fit canvas", "FIT", LIME, "TWO"),
                    hotkey("Reset rotation", "ROT0", LIME, "FIVE"),
                    hotkey("Rotate left", "ROT-", LIME, "FOUR"),
                    hotkey("Zoom out", "ZOOM-", LIME, "MINUS"),
                    hotkey("Rotate right", "ROT+", LIME, "SIX"),
                    hotkey("Pan left", "LEFT", LIME, "LEFT_ARROW"),
                    hotkey("Zoom in", "ZOOM+", LIME, "EQUALS"),
                    hotkey("Pan right", "RIGHT", LIME, "RIGHT_ARROW"),
                ],
            ),
            layout(
                "Brush and Layers",
                "LY",
                [
                    hotkey("Freehand brush", "BRUSH", GREEN, "B"),
                    hotkey("Eraser mode", "ERASE", YELLOW, "E"),
                    hotkey("Brush editor", "BR-SET", YELLOW, "F5"),
                    hotkey("Smaller brush", "SIZE-", LIME, "LEFT_BRACKET"),
                    hotkey("Larger brush", "SIZE+", LIME, "RIGHT_BRACKET"),
                    hotkey("Default colors", "COLORS", YELLOW, "D"),
                    hotkey("New paint layer", "LAYER+", GREEN, "INSERT"),
                    hotkey("Previous layer", "LYR-", LIME, "PAGE_UP"),
                    hotkey("Next layer", "LYR+", LIME, "PAGE_DOWN"),
                    hotkey("Duplicate layer", "DUP", GREEN, "CONTROL", "J"),
                    hotkey("Merge layer down", "MERGE", ORANGE, "CONTROL", "E"),
                    hotkey("Clear layer", "CLEAR", RED, "SHIFT", "DELETE"),
                ],
            ),
        ],
    ),
    "libreoffice": (
        "General",
        [
            layout(
                "Writer",
                "WR",
                [
                    hotkey("Bold", "BOLD", YELLOW, "CONTROL", "B"),
                    hotkey("Italic", "ITALIC", YELLOW, "CONTROL", "I"),
                    hotkey("Underline", "UNDER", YELLOW, "CONTROL", "U"),
                    hotkey("Align left", "LEFT", LIME, "CONTROL", "L"),
                    hotkey("Align center", "CENTER", LIME, "CONTROL", "E"),
                    hotkey("Align right", "RIGHT", LIME, "CONTROL", "R"),
                    hotkey("Justified", "JUST", LIME, "CONTROL", "J"),
                    hotkey("Spell check", "SPELL", YELLOW, "F7"),
                    hotkey("Navigator", "NAV", LIME, "F5"),
                    hotkey("Nonprinting marks", "MARKS", YELLOW, "CONTROL", "F10"),
                    hotkey("Numbered list", "NUM", YELLOW, "F12"),
                    hotkey("Bullet list", "BULLET", YELLOW, "SHIFT", "F12"),
                ],
            ),
            layout(
                "Calc and Impress",
                "CI",
                [
                    hotkey("Edit cell", "CELL", YELLOW, "F2"),
                    hotkey("Function wizard", "FUNC", YELLOW, "CONTROL", "F2"),
                    hotkey("Absolute reference", "REF", YELLOW, "F4"),
                    hotkey("Previous sheet", "SHEET-", LIME, "CONTROL", "PAGE_UP"),
                    hotkey("Next sheet", "SHEET+", LIME, "CONTROL", "PAGE_DOWN"),
                    hotkey("Select column", "COLUMN", YELLOW, "CONTROL", "SPACE"),
                    hotkey("Select row", "ROW", YELLOW, "SHIFT", "SPACE"),
                    hotkey("Start slideshow", "SHOW", GREEN, "F5"),
                    hotkey("Start at current slide", "SHOW-C", GREEN, "SHIFT", "F5"),
                    hotkey("Duplicate slide", "DUP", GREEN, "CONTROL", "SHIFT", "D"),
                    hotkey("Move slide up", "SLIDE-", LIME, "ALT", "UP_ARROW"),
                    hotkey("Move slide down", "SLIDE+", LIME, "ALT", "DOWN_ARROW"),
                ],
            ),
        ],
    ),
    "blender": (
        "General",
        [
            layout(
                "Transform",
                "TR",
                [
                    hotkey("Move", "MOVE", LIME, "G"),
                    hotkey("Rotate", "ROTATE", LIME, "R"),
                    hotkey("Scale", "SCALE", LIME, "S"),
                    hotkey("Constrain X", "AXIS-X", YELLOW, "X"),
                    hotkey("Constrain Y", "AXIS-Y", YELLOW, "Y"),
                    hotkey("Constrain Z", "AXIS-Z", YELLOW, "Z"),
                    hotkey("Add object", "ADD", GREEN, "SHIFT", "A"),
                    hotkey("Duplicate", "DUP", GREEN, "SHIFT", "D"),
                    hotkey("Delete", "DELETE", RED, "X"),
                    hotkey("Apply transform", "APPLY", ORANGE, "CONTROL", "A"),
                    hotkey("Edit mode", "EDIT", YELLOW, "TAB"),
                    hotkey("Mode pie menu", "MODE", YELLOW, "CONTROL", "TAB"),
                ],
            ),
            layout(
                "Viewport",
                "VW",
                [
                    hotkey("Select all", "ALL", YELLOW, "A"),
                    hotkey("Deselect all", "NONE", YELLOW, "ALT", "A"),
                    hotkey("Invert selection", "INVERT", YELLOW, "CONTROL", "I"),
                    hotkey("Hide selected", "HIDE", YELLOW, "H"),
                    hotkey("Reveal hidden", "REVEAL", LIME, "ALT", "H"),
                    hotkey("Toolbar", "TOOLS", YELLOW, "T"),
                    hotkey("Sidebar", "SIDE", YELLOW, "N"),
                    hotkey("View pie menu", "VIEW", LIME, "GRAVE_ACCENT"),
                    hotkey("Toggle gizmos", "GIZMO", YELLOW, "CONTROL", "GRAVE_ACCENT"),
                    hotkey("Fly navigation", "FLY", LIME, "SHIFT", "GRAVE_ACCENT"),
                    hotkey("Previous workspace", "WORK-", LIME, "CONTROL", "PAGE_UP"),
                    hotkey("Next workspace", "WORK+", LIME, "CONTROL", "PAGE_DOWN"),
                ],
            ),
        ],
    ),
}


IN_APP_LAYOUTS = {
    "editing": layout(
        "In App",
        "IA",
        [
            hotkey("Copy", "COPY", GREEN, "CONTROL", "C"),
            hotkey("Paste", "PASTE", GREEN, "CONTROL", "V"),
            hotkey("Cut", "CUT", ORANGE, "CONTROL", "X"),
            hotkey("Undo", "UNDO", YELLOW, "CONTROL", "Z"),
            hotkey("Redo", "REDO", YELLOW, "CONTROL", "SHIFT", "Z"),
            hotkey("Save", "SAVE", GREEN, "CONTROL", "S"),
            hotkey("Find", "FIND", LIME, "CONTROL", "F"),
            hotkey("Replace", "REPL", YELLOW, "CONTROL", "H"),
            hotkey("Bold", "BOLD", YELLOW, "CONTROL", "B"),
            hotkey("Italic", "ITALIC", YELLOW, "CONTROL", "I"),
            hotkey("Select all", "ALL", YELLOW, "CONTROL", "A"),
            hotkey("Close document", "CLOSE", RED, "CONTROL", "W"),
        ],
    ),
    "media": layout(
        "In App",
        "IA",
        [
            consumer("Previous track", "PREV", LIME, "SCAN_PREVIOUS_TRACK"),
            consumer("Play pause", "PLAY", GREEN, "PLAY_PAUSE"),
            consumer("Next track", "NEXT", LIME, "SCAN_NEXT_TRACK"),
            hotkey("Seek backward", "SEEK-", LIME, "LEFT_ARROW"),
            consumer("Stop", "STOP", RED, "STOP"),
            hotkey("Seek forward", "SEEK+", LIME, "RIGHT_ARROW"),
            consumer("Volume down", "VOL-", ORANGE, "VOLUME_DECREMENT"),
            consumer("Mute", "MUTE", RED, "MUTE"),
            consumer("Volume up", "VOL+", GREEN, "VOLUME_INCREMENT"),
            hotkey("Page up", "PGUP", LIME, "PAGE_UP"),
            hotkey("Fullscreen", "FULL", YELLOW, "F11"),
            hotkey("Page down", "PGDN", LIME, "PAGE_DOWN"),
        ],
    ),
    "vscode": layout(
        "In App",
        "IA",
        [
            hotkey("Command palette", "CMD", YELLOW, "CONTROL", "SHIFT", "P"),
            hotkey("Quick open", "OPEN", GREEN, "CONTROL", "P"),
            hotkey("Save", "SAVE", GREEN, "CONTROL", "S"),
            hotkey("Format document", "FORMAT", YELLOW, "SHIFT", "ALT", "F"),
            hotkey("Go to definition", "DEF", LIME, "F12"),
            hotkey("Rename symbol", "RENAME", ORANGE, "F2"),
            hotkey("Quick fix", "FIX", YELLOW, "CONTROL", "PERIOD"),
            hotkey("Toggle comment", "COMENT", YELLOW, "CONTROL", "FORWARD_SLASH"),
            hotkey("Toggle terminal", "TERM", YELLOW, "CONTROL", "GRAVE_ACCENT"),
            hotkey("Problems panel", "PROBS", RED, "CONTROL", "SHIFT", "M"),
            hotkey("Start debugging", "DEBUG", GREEN, "F5"),
            hotkey("Toggle breakpoint", "BREAK", YELLOW, "F9"),
        ],
    ),
    "firefox": layout(
        "In App",
        "IA",
        [
            hotkey("Back", "BACK", LIME, "ALT", "LEFT_ARROW"),
            hotkey("Reload", "RELOAD", YELLOW, "CONTROL", "R"),
            hotkey("Forward", "FWD", LIME, "ALT", "RIGHT_ARROW"),
            hotkey("Page up", "PGUP", LIME, "PAGE_UP"),
            hotkey("Page top", "TOP", LIME, "HOME"),
            hotkey("Page down", "PGDN", LIME, "PAGE_DOWN"),
            hotkey("Find in page", "FIND", LIME, "CONTROL", "F"),
            hotkey("Previous tab", "TAB-", LIME, "CONTROL", "PAGE_UP"),
            hotkey("Next tab", "TAB+", LIME, "CONTROL", "PAGE_DOWN"),
            hotkey("Zoom out", "ZOOM-", YELLOW, "CONTROL", "MINUS"),
            hotkey("Reset zoom", "ZOOM0", YELLOW, "CONTROL", "ZERO"),
            hotkey("Zoom in", "ZOOM+", YELLOW, "CONTROL", "EQUALS"),
        ],
    ),
    "vlc": layout(
        "In App",
        "IA",
        [
            hotkey("Previous", "PREV", LIME, "P"),
            hotkey("Play pause", "PLAY", GREEN, "SPACE"),
            hotkey("Next", "NEXT", LIME, "N"),
            hotkey("Short back", "BACK", LIME, "ALT", "LEFT_ARROW"),
            hotkey("Stop", "STOP", RED, "S"),
            hotkey("Short forward", "FWD", LIME, "ALT", "RIGHT_ARROW"),
            hotkey("Slower", "SLOW", YELLOW, "MINUS"),
            hotkey("Normal speed", "NORMAL", YELLOW, "EQUALS"),
            hotkey("Faster", "FAST", YELLOW, "RIGHT_BRACKET"),
            hotkey("Volume down", "VOL-", ORANGE, "CONTROL", "DOWN_ARROW"),
            hotkey("Mute", "MUTE", RED, "M"),
            hotkey("Volume up", "VOL+", GREEN, "CONTROL", "UP_ARROW"),
        ],
    ),
    "discord": layout(
        "In App",
        "IA",
        [
            hotkey("Quick switcher", "QUICK", GREEN, "CONTROL", "K"),
            hotkey("Previous channel", "CH-", LIME, "ALT", "UP_ARROW"),
            hotkey("Next channel", "CH+", LIME, "ALT", "DOWN_ARROW"),
            hotkey("Microphone mute", "MIC", RED, "CONTROL", "SHIFT", "M"),
            hotkey("Deafen", "DEAF", RED, "CONTROL", "SHIFT", "D"),
            hotkey("Upload file", "UPLOAD", GREEN, "CONTROL", "SHIFT", "U"),
            hotkey("Edit last message", "EDIT", ORANGE, "SHIFT", "UP_ARROW"),
            hotkey("Reply focused message", "REPLY", GREEN, "R"),
            hotkey("React to message", "REACT", GREEN, "SHIFT", "EQUALS"),
            hotkey("Emoji picker", "EMOJI", GREEN, "CONTROL", "E"),
            hotkey("GIF picker", "GIF", GREEN, "CONTROL", "G"),
            hotkey("Mark unread", "UNREAD", YELLOW, "ALT", "ENTER"),
        ],
    ),
    "lm-studio": layout(
        "In App",
        "IA",
        [
            hotkey("New chat", "CHAT+", GREEN, "CONTROL", "N"),
            hotkey("Find", "FIND", LIME, "CONTROL", "F"),
            hotkey("Send message", "SEND", GREEN, "ENTER"),
            hotkey("Copy", "COPY", GREEN, "CONTROL", "C"),
            hotkey("Paste", "PASTE", GREEN, "CONTROL", "V"),
            hotkey("New line", "LINE+", GREEN, "SHIFT", "ENTER"),
            hotkey("Undo", "UNDO", YELLOW, "CONTROL", "Z"),
            hotkey("Redo", "REDO", YELLOW, "CONTROL", "Y"),
            hotkey("Select all", "ALL", YELLOW, "CONTROL", "A"),
            hotkey("Previous control", "ITEM-", LIME, "SHIFT", "TAB"),
            hotkey("Cancel", "ESC", ORANGE, "ESCAPE"),
            hotkey("Next control", "ITEM+", LIME, "TAB"),
        ],
    ),
    "terminal-manjaro": layout(
        "In App",
        "IA",
        [
            hotkey("Interrupt", "INT", RED, "CONTROL", "C"),
            hotkey("End input", "EOF", ORANGE, "CONTROL", "D"),
            hotkey("Suspend process", "SUSP", ORANGE, "CONTROL", "Z"),
            hotkey("Clear screen", "CLEAR", YELLOW, "CONTROL", "L"),
            hotkey("Previous command", "HIST-", LIME, "UP_ARROW"),
            hotkey("Next command", "HIST+", LIME, "DOWN_ARROW"),
            hotkey("Previous word", "WORD-", LIME, "ALT", "B"),
            hotkey("Next word", "WORD+", LIME, "ALT", "F"),
            hotkey("Line start", "HOME", LIME, "CONTROL", "A"),
            hotkey("Line end", "END", LIME, "CONTROL", "E"),
            hotkey("Complete", "TAB", GREEN, "TAB"),
            hotkey("Paste", "PASTE", GREEN, "CONTROL", "SHIFT", "V"),
        ],
    ),
    "comfyui": layout(
        "In App",
        "IA",
        [
            hotkey("Queue prompt", "QUEUE", GREEN, "CONTROL", "ENTER"),
            hotkey("Queue front", "FRONT", GREEN, "CONTROL", "SHIFT", "ENTER"),
            hotkey("Interrupt", "STOP", RED, "CONTROL", "ALT", "ENTER"),
            hotkey("Undo", "UNDO", YELLOW, "CONTROL", "Z"),
            hotkey("Redo", "REDO", YELLOW, "CONTROL", "Y"),
            hotkey("Delete nodes", "DELETE", RED, "DELETE"),
            hotkey("Copy nodes", "COPY", GREEN, "CONTROL", "C"),
            hotkey("Paste nodes", "PASTE", GREEN, "CONTROL", "V"),
            hotkey("Select all nodes", "ALL", YELLOW, "CONTROL", "A"),
            hotkey("Collapse nodes", "FOLD", YELLOW, "ALT", "C"),
            hotkey("Mute nodes", "MUTE", RED, "CONTROL", "M"),
            hotkey("Bypass nodes", "BYPASS", YELLOW, "CONTROL", "B"),
        ],
    ),
    "ssh": layout(
        "In App",
        "IA",
        [
            hotkey("Interrupt remote", "INT", RED, "CONTROL", "C"),
            hotkey("End remote shell", "EOF", ORANGE, "CONTROL", "D"),
            hotkey("Suspend process", "SUSP", ORANGE, "CONTROL", "Z"),
            hotkey("Clear screen", "CLEAR", YELLOW, "CONTROL", "L"),
            hotkey("Previous command", "HIST-", LIME, "UP_ARROW"),
            hotkey("Next command", "HIST+", LIME, "DOWN_ARROW"),
            hotkey("Previous word", "WORD-", LIME, "ALT", "B"),
            hotkey("Next word", "WORD+", LIME, "ALT", "F"),
            hotkey("Line start", "HOME", LIME, "CONTROL", "A"),
            hotkey("Line end", "END", LIME, "CONTROL", "E"),
            hotkey("Complete", "TAB", GREEN, "TAB"),
            hotkey("Paste", "PASTE", GREEN, "CONTROL", "SHIFT", "V"),
        ],
    ),
    "audio-controls": layout(
        "In App",
        "IA",
        [
            consumer("Previous track", "PREV", LIME, "SCAN_PREVIOUS_TRACK"),
            consumer("Play pause", "PLAY", GREEN, "PLAY_PAUSE"),
            consumer("Next track", "NEXT", LIME, "SCAN_NEXT_TRACK"),
            consumer("Volume down", "VOL-", ORANGE, "VOLUME_DECREMENT"),
            consumer("Mute", "MUTE", RED, "MUTE"),
            consumer("Volume up", "VOL+", GREEN, "VOLUME_INCREMENT"),
            consumer("Volume down 3", "VOL-3", ORANGE, "VOLUME_DECREMENT", 3),
            consumer("Stop", "STOP", RED, "STOP"),
            consumer("Volume up 3", "VOL+3", GREEN, "VOLUME_INCREMENT", 3),
            consumer("Volume down 5", "VOL-5", ORANGE, "VOLUME_DECREMENT", 5),
            consumer("Record", "REC", RED, "RECORD"),
            consumer("Volume up 5", "VOL+5", GREEN, "VOLUME_INCREMENT", 5),
        ],
    ),
    "system-control": layout(
        "In App",
        "IA",
        [
            hotkey("Previous control", "ITEM-", LIME, "SHIFT", "TAB"),
            hotkey("Up", "UP", LIME, "UP_ARROW"),
            hotkey("Next control", "ITEM+", LIME, "TAB"),
            hotkey("Left", "LEFT", LIME, "LEFT_ARROW"),
            hotkey("Activate", "ENTER", GREEN, "ENTER"),
            hotkey("Right", "RIGHT", LIME, "RIGHT_ARROW"),
            hotkey("Page up", "PGUP", LIME, "PAGE_UP"),
            hotkey("Down", "DOWN", LIME, "DOWN_ARROW"),
            hotkey("Page down", "PGDN", LIME, "PAGE_DOWN"),
            hotkey("Toggle option", "TOGGLE", YELLOW, "SPACE"),
            hotkey("Cancel", "ESC", ORANGE, "ESCAPE"),
            hotkey("Close settings", "CLOSE", RED, "ALT", "F4"),
        ],
    ),
    "caja": layout(
        "In App",
        "IA",
        [
            hotkey("Back", "BACK", LIME, "ALT", "LEFT_ARROW"),
            hotkey("Up one folder", "UP", LIME, "ALT", "UP_ARROW"),
            hotkey("Forward", "FWD", LIME, "ALT", "RIGHT_ARROW"),
            hotkey("Copy", "COPY", GREEN, "CONTROL", "C"),
            hotkey("Paste", "PASTE", GREEN, "CONTROL", "V"),
            hotkey("Cut", "CUT", ORANGE, "CONTROL", "X"),
            hotkey("Rename", "RENAME", ORANGE, "F2"),
            hotkey("Open item", "OPEN", GREEN, "ENTER"),
            hotkey("Search", "SEARCH", LIME, "CONTROL", "F"),
            hotkey("Show hidden files", "HIDDEN", YELLOW, "CONTROL", "H"),
            hotkey("Move to trash", "TRASH", RED, "DELETE"),
            hotkey("New folder", "FOLD+", GREEN, "CONTROL", "SHIFT", "N"),
        ],
    ),
    "krita": layout(
        "In App",
        "IA",
        [
            hotkey("Freehand brush", "BRUSH", GREEN, "B"),
            hotkey("Eraser mode", "ERASE", YELLOW, "E"),
            hotkey("Brush editor", "BR-SET", YELLOW, "F5"),
            hotkey("Smaller brush", "SIZE-", LIME, "LEFT_BRACKET"),
            hotkey("Larger brush", "SIZE+", LIME, "RIGHT_BRACKET"),
            hotkey("Mirror canvas", "MIRROR", YELLOW, "M"),
            hotkey("Undo", "UNDO", YELLOW, "CONTROL", "Z"),
            hotkey("Redo", "REDO", YELLOW, "CONTROL", "SHIFT", "Z"),
            hotkey("Save", "SAVE", GREEN, "CONTROL", "S"),
            hotkey("New paint layer", "LAYER+", GREEN, "INSERT"),
            hotkey("Previous layer", "LYR-", LIME, "PAGE_UP"),
            hotkey("Next layer", "LYR+", LIME, "PAGE_DOWN"),
        ],
    ),
    "libreoffice": layout(
        "In App",
        "IA",
        [
            hotkey("Save", "SAVE", GREEN, "CONTROL", "S"),
            hotkey("Undo", "UNDO", YELLOW, "CONTROL", "Z"),
            hotkey("Redo", "REDO", YELLOW, "CONTROL", "Y"),
            hotkey("Copy", "COPY", GREEN, "CONTROL", "C"),
            hotkey("Paste", "PASTE", GREEN, "CONTROL", "V"),
            hotkey("Find", "FIND", LIME, "CONTROL", "F"),
            hotkey("Bold", "BOLD", YELLOW, "CONTROL", "B"),
            hotkey("Italic", "ITALIC", YELLOW, "CONTROL", "I"),
            hotkey("Underline", "UNDER", YELLOW, "CONTROL", "U"),
            hotkey("Align left", "LEFT", LIME, "CONTROL", "L"),
            hotkey("Align center", "CENTER", LIME, "CONTROL", "E"),
            hotkey("Align right", "RIGHT", LIME, "CONTROL", "R"),
        ],
    ),
    "blender": layout(
        "In App",
        "IA",
        [
            hotkey("Move", "MOVE", LIME, "G"),
            hotkey("Rotate", "ROTATE", LIME, "R"),
            hotkey("Scale", "SCALE", LIME, "S"),
            hotkey("Constrain X", "AXIS-X", YELLOW, "X"),
            hotkey("Constrain Y", "AXIS-Y", YELLOW, "Y"),
            hotkey("Constrain Z", "AXIS-Z", YELLOW, "Z"),
            hotkey("Add object", "ADD", GREEN, "SHIFT", "A"),
            hotkey("Duplicate", "DUP", GREEN, "SHIFT", "D"),
            hotkey("Delete", "DELETE", RED, "X"),
            hotkey("Apply transform", "APPLY", ORANGE, "CONTROL", "A"),
            hotkey("Edit mode", "EDIT", YELLOW, "TAB"),
            hotkey("Operator search", "SEARCH", LIME, "F3"),
        ],
    ),
}


PRIMARY_FILL = {
    "quicklaunch": (6, [
        launcher("Launch VLC", "VLC", GREEN, "vlc"),
        launcher("Audio mixer", "AUDIO", GREEN, "pavucontrol"),
        launcher("System settings", "SET", ORANGE, "xfce4-settings-manager"),
        launcher("Calculator", "CALC", GREEN, "qalculate-gtk"),
        launcher("Image editor", "GIMP", GREEN, "gimp"),
        terminal("System monitor", "MON", GREEN, "btop"),
    ]),
    "system-control": (5, [
        launcher("Lock screen", "LOCK", ORANGE, "i3lock"),
        terminal("Suspend", "SUSP", ORANGE, "systemctl suspend"),
        terminal("Hibernate", "HIBER", ORANGE, "systemctl hibernate"),
        hotkey("i3 logout prompt", "LOGOUT", RED, "GUI", "SHIFT", "E"),
        hotkey("Reload i3 config", "I3-CFG", YELLOW, "GUI", "SHIFT", "C"),
        hotkey("Open terminal", "TERM", GREEN, "GUI", "ENTER"),
        hotkey("Application launcher", "MENU", GREEN, "GUI", "D"),
    ]),
    "terminal-manjaro": (0, [
        text("Check updates", "CHECK", LIME, "pamac checkupdates -a"),
        text("Upgrade system", "UPDATE", ORANGE, "pamac upgrade -a"),
        text("Pacman full update", "S-SYU", ORANGE, "sudo pacman -Syu"),
        text("Search packages", "SEARCH", GREEN, "pamac search "),
        text("Install package", "INSTAL", YELLOW, "pamac install "),
        text("Build AUR package", "AUR", ORANGE, "pamac build "),
        text("Remove package", "REMOVE", RED, "pamac remove "),
        text("Package info", "INFO", LIME, "pamac info "),
        text("List orphans", "ORPHAN", YELLOW, "pamac list -o"),
        text("Clean package cache", "CLEAN", RED, "sudo paccache -rk3"),
        text("Service status", "SVC", YELLOW, "systemctl status "),
        text("Boot warnings", "LOG", RED, "journalctl -b -p warning"),
    ]),
}


def render(profile):
    def dumped(value):
        return json.dumps(value, ensure_ascii=False)

    lines = [
        "{",
        f'  "schema_version": {profile["schema_version"]},',
        f'  "id": {dumped(profile["id"])},',
        f'  "name": {dumped(profile["name"])},',
        f'  "icon": {dumped(profile.get("icon", ""))},',
        f'  "subprofile_name": {dumped(profile["subprofile_name"])},',
        f'  "brightness": {profile["brightness"]},',
        '  "keys": [',
    ]
    for index, item in enumerate(profile["keys"]):
        lines.append("    " + dumped(item) + ("," if index < 11 else ""))
    lines.extend(
        [
            "  ],",
            f'  "encoder_press": {dumped(profile["encoder_press"])},',
            '  "subprofiles": [',
        ]
    )
    for sub_index, subprofile in enumerate(profile["subprofiles"]):
        lines.extend(
            [
                "    {",
                f'      "name": {dumped(subprofile["name"])},',
                f'      "icon": {dumped(subprofile["icon"])},',
                f'      "brightness": {subprofile["brightness"]},',
                '      "keys": [',
            ]
        )
        for key_index, item in enumerate(subprofile["keys"]):
            lines.append("        " + dumped(item) + ("," if key_index < 11 else ""))
        lines.extend(
            [
                "      ]",
                "    }" + ("," if sub_index < len(profile["subprofiles"]) - 1 else ""),
            ]
        )
    lines.extend(["  ]", "}", ""])
    return "\n".join(lines)


def main():
    index = json.loads((PROFILE_ROOT / "index.json").read_text(encoding="utf-8"))
    expected = {entry["id"] for entry in index["profiles"]} - {"i3wm", "options"}
    if set(SPECS) != expected:
        raise RuntimeError(
            "profile spec mismatch: missing={} extra={}".format(
                sorted(expected - set(SPECS)),
                sorted(set(SPECS) - expected),
            )
        )

    for entry in index["profiles"]:
        profile_id = entry["id"]
        if profile_id in ("i3wm", "options"):
            continue
        path = PROFILE_ROOT / entry["file"]
        profile = json.loads(path.read_text(encoding="utf-8"))
        primary_name, subprofiles = SPECS[profile_id]
        if profile_id in PRIMARY_FILL:
            start, replacements = PRIMARY_FILL[profile_id]
            profile["keys"][start : start + len(replacements)] = replacements
        profile["subprofile_name"] = primary_name
        profile["encoder_press"] = {
            "name": "Next subprofile",
            "oled_label": "NEXT",
            "steps": [],
        }
        profile["subprofiles"] = list(subprofiles)
        if profile_id in IN_APP_LAYOUTS:
            profile["subprofiles"].append(IN_APP_LAYOUTS[profile_id])
        if profile_id == "terminal-manjaro":
            for terminal_layout in [profile] + profile["subprofiles"]:
                wrapped = []
                for item in terminal_layout["keys"]:
                    steps = item.get("steps", [])
                    if len(steps) == 1 and steps[0].get("type") == "text":
                        wrapped.append(
                            terminal_template(
                                item["name"],
                                item["oled_label"],
                                item["idle_color"],
                                steps[0].get("text", ""),
                            )
                        )
                    else:
                        wrapped.append(item)
                terminal_layout["keys"] = wrapped
        path.write_text(render(profile), encoding="utf-8")
        print(
            "built {}: {}".format(
                profile_id,
                ", ".join(
                    [primary_name]
                    + [item["name"] for item in profile["subprofiles"]]
                ),
            )
        )


if __name__ == "__main__":
    main()
