import json
from pathlib import Path

import pytest

from macropad_configurator import device_io
from macropad_configurator.device_io import (
    DeviceError,
    DeviceInfo,
    backup_device,
    compare_projects,
    device_health,
    export_library_archive,
    import_library_archive,
    list_device_backups,
    parse_boot_out,
    parse_serial_json,
    read_device_project,
    sync_project,
)
from macropad_configurator.models import new_project


def make_device(root: Path) -> DeviceInfo:
    root.mkdir()
    (root / "boot_out.txt").write_text(
        "Adafruit CircuitPython 10.2.1\nBoard ID:adafruit_macropad_rp2040\nUID:ABC123\n",
        encoding="utf-8",
    )
    profiles = root / "profiles"
    profiles.mkdir()
    project = new_project()
    sync_project(DeviceInfo(root, "ABC123"), project)
    return DeviceInfo(root, "ABC123")


def test_parse_boot_out_and_round_trip(tmp_path):
    device = make_device(tmp_path / "CIRCUITPY")
    info = parse_boot_out(device.mount)
    assert info and info.uid == "ABC123"
    imported = read_device_project(device)
    assert imported["profiles"][0]["name"] == "Editing"
    assert len(imported["profiles"][0]["keys"]) == 12


def test_sync_round_trip_preserves_subprofiles(tmp_path):
    device = make_device(tmp_path / "CIRCUITPY")
    project = new_project()
    project["profiles"][0]["subprofile_name"] = "Primary"
    project["profiles"][0]["subprofiles"] = [
        {
            "name": "Second",
            "icon": "S2",
            "brightness": 7,
            "keys": project["profiles"][0]["keys"],
        }
    ]
    sync_project(device, project)
    restored = read_device_project(device)
    profile = restored["profiles"][0]
    assert profile["subprofile_name"] == "Primary"
    assert [item["name"] for item in profile["subprofiles"]] == ["Second"]
    assert profile["subprofiles"][0]["brightness"] == 7


def test_sync_commits_index_and_removes_stale_profile(tmp_path):
    device = make_device(tmp_path / "CIRCUITPY")
    stale = device.mount / "profiles" / "stale.json"
    stale.write_text("{}", encoding="utf-8")
    project = new_project()
    project["keyboard_layout"] = "de"
    revision = sync_project(device, project)
    config = json.loads((device.mount / "device_config.json").read_text())
    index = json.loads((device.mount / "profiles" / "index.json").read_text())
    assert config["keyboard_layout"] == "de"
    assert index["profiles"][0]["file"].endswith(f".{revision}.json")
    assert (device.mount / "profiles" / "revision.txt").read_text().strip() == revision
    assert not stale.exists()


def test_interrupted_sync_keeps_old_index(tmp_path, monkeypatch):
    device = make_device(tmp_path / "CIRCUITPY")
    before = (device.mount / "profiles" / "index.json").read_text()
    original = device_io._write_json_temp
    calls = 0

    def fail_on_config(destination, data):
        nonlocal calls
        calls += 1
        if destination.name == "device_config.json":
            raise OSError("disconnected")
        return original(destination, data)

    monkeypatch.setattr(device_io, "_write_json_temp", fail_on_config)
    project = new_project()
    project["profiles"].append({**project["profiles"][0], "id": "second", "name": "Second"})
    with pytest.raises(DeviceError, match="interrupted"):
        sync_project(device, project)
    assert (device.mount / "profiles" / "index.json").read_text() == before


def test_serial_json_ignores_circuitpython_terminal_prefix():
    line = '\x1b]0;🐍code.py | 10.2.1\x1b\\{"event":"response","cmd":"ping","ok":true}'
    assert parse_serial_json(line) == {"event": "response", "cmd": "ping", "ok": True}


def test_compare_backup_and_library_archive(tmp_path):
    device = make_device(tmp_path / "CIRCUITPY")
    local = read_device_project(device)
    local["keyboard_layout"] = "de"
    local["profiles"][0]["brightness"] = 77
    changes = compare_projects(local, read_device_project(device))
    assert any("Keyboard layout" in change for change in changes)
    assert any("brightness" in change for change in changes)

    backup = backup_device(device, tmp_path / "backups")
    assert backup in list_device_backups(tmp_path / "backups", "ABC123")

    archive = tmp_path / "library.macropad.zip"
    export_library_archive(archive, local, ["#112233"])
    restored, palette = import_library_archive(archive)
    assert restored == local
    assert palette == ["#112233"]


def test_device_health_reports_version_and_missing_files(tmp_path, monkeypatch):
    device = make_device(tmp_path / "CIRCUITPY")
    monkeypatch.setattr(
        device_io,
        "send_command",
        lambda command, uid, timeout=2.0: {"firmware_version": "1.1.0", "profile": "editing"},
    )
    health = device_health(device)
    assert health["firmware_version"] == "1.1.0"
    assert not health["healthy"]
    assert "code.py" in health["missing"]
