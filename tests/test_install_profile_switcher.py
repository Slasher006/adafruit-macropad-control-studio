import sys

from tools import install_profile_switcher


def test_replace_config_restarts_an_existing_service(tmp_path, monkeypatch):
    source_config = tmp_path / "source.json"
    source_config.write_text('{"rules": []}\n', encoding="utf-8")
    python = tmp_path / "python"
    python.touch()
    config_path = tmp_path / "config" / "switcher.json"
    unit_path = tmp_path / "systemd" / "switcher.service"
    calls = []

    monkeypatch.setattr(install_profile_switcher, "DEFAULT_CONFIG", source_config)
    monkeypatch.setattr(install_profile_switcher, "PYTHON", python)
    monkeypatch.setattr(install_profile_switcher, "CONFIG_PATH", config_path)
    monkeypatch.setattr(install_profile_switcher, "UNIT_PATH", unit_path)
    monkeypatch.setattr(
        install_profile_switcher.subprocess,
        "run",
        lambda command, check: calls.append(command),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["install_profile_switcher.py", "--replace-config"],
    )

    assert install_profile_switcher.main() == 0
    assert config_path.read_text(encoding="utf-8") == '{"rules": []}\n'
    assert calls == [
        ["systemctl", "--user", "daemon-reload"],
        ["systemctl", "--user", "enable", unit_path.name],
        ["systemctl", "--user", "restart", unit_path.name],
    ]
