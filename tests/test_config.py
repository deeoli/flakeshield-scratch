import json
import os
import sys
import tempfile
import pytest

from flakeshield import config as config_mod
from flakeshield import cli


def test_no_config_returns_empty(tmp_path, monkeypatch):
    # ensure cwd has no config file
    monkeypatch.chdir(tmp_path)
    assert not (tmp_path / ".flakeshield.json").exists()
    cfg = config_mod.load_config(None)
    assert cfg == {}


def test_invalid_json_exits(tmp_path):
    path = tmp_path / "cfg.json"
    path.write_text("{not: valid json}")
    with pytest.raises(SystemExit) as exc:
        config_mod.load_config(str(path))
    assert "Failed to load config" in str(exc.value)


def test_config_defaults_applied_when_cli_missing(monkeypatch):
    # config returns both keys
    cfg = {"min_runs": 7, "enable_semantic": True}
    monkeypatch.setattr(cli, "load_config", lambda p: cfg)

    captured = {}

    def fake_build_reports(xml_glob, out_prefix, db_path, enable_semantic, min_runs):
        captured["enable_semantic"] = enable_semantic
        captured["min_runs"] = min_runs
        raise RuntimeError("stop")

    monkeypatch.setattr(cli, "build_reports", fake_build_reports)
    monkeypatch.setattr(sys, "argv", ["flakeshield"])

    with pytest.raises(RuntimeError):
        cli.main()

    assert captured.get("min_runs") == 7
    assert captured.get("enable_semantic") is True


def test_cli_overrides_config(monkeypatch):
    cfg = {"min_runs": 7, "enable_semantic": False}
    monkeypatch.setattr(cli, "load_config", lambda p: cfg)

    captured = {}

    def fake_build_reports(xml_glob, out_prefix, db_path, enable_semantic, min_runs):
        captured["enable_semantic"] = enable_semantic
        captured["min_runs"] = min_runs
        raise RuntimeError("stop")

    monkeypatch.setattr(cli, "build_reports", fake_build_reports)
    # include CLI flags to override
    monkeypatch.setattr(
        sys, "argv", ["flakeshield", "--min-runs", "3", "--enable-semantic"]
    )

    with pytest.raises(RuntimeError):
        cli.main()

    assert captured.get("min_runs") == 3
    assert captured.get("enable_semantic") is True
