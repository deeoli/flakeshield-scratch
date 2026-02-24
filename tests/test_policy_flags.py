import os
import subprocess
import sys
from pathlib import Path


def make_xml(path: Path, msg: str):
    xml = f"""<?xml version='1.0'?>
<testsuites>
  <testsuite name='s' tests='1' failures='1'>
    <testcase classname='s' name='t' time='0.1'><failure message='{msg}'>x</failure></testcase>
  </testsuite>
</testsuites>
"""
    path.write_text(xml)


def run_cli(args, env=None, cwd=None):
    base_env = os.environ.copy()
    if env:
        base_env.update(env)
    proc = subprocess.run(
        [sys.executable, "-m", "flakeshield.cli"] + args,
        env=base_env,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return proc


def test_no_enforcement_when_semantic_disabled(tmp_path):
    # create two runs so flake detection works
    make_xml(tmp_path / "r1.xml", "fail")
    make_xml(tmp_path / "r2.xml", "fail")
    res = run_cli(
        [
            "--reports",
            str(tmp_path / "r*.xml"),
            "--out",
            str(tmp_path / "out"),
            "--db",
            str(tmp_path / "fs.db"),
            "--fail-on-critical",
        ]
    )
    assert res.returncode == 0


def test_fail_on_critical_when_semantic_enabled(tmp_path):
    # create 10 identical runs to push confidence_factor -> 1.0
    for i in range(10):
        make_xml(tmp_path / f"r{i+1}.xml", "fail")
    env = {
        "FLAKESHIELD_DUMMY_EMBEDS": "1",
        "FLAKESHIELD_FORCE_NOVEL": "1",
    }
    res = run_cli(
        [
            "--reports",
            str(tmp_path / "r*.xml"),
            "--out",
            str(tmp_path / "out"),
            "--db",
            str(tmp_path / "fs.db"),
            "--enable-semantic",
            "--fail-on-critical",
        ],
        env=env,
    )
    assert res.returncode == 1


def test_max_risk_threshold_trips(tmp_path):
    # produce many runs so high risk score
    for i in range(10):
        make_xml(tmp_path / f"r{i+1}.xml", "fail")
    env = {
        "FLAKESHIELD_DUMMY_EMBEDS": "1",
        "FLAKESHIELD_FORCE_NOVEL": "1",
    }
    res = run_cli(
        [
            "--reports",
            str(tmp_path / "r*.xml"),
            "--out",
            str(tmp_path / "out"),
            "--db",
            str(tmp_path / "fs.db"),
            "--enable-semantic",
            "--max-risk-threshold",
            "0.8",
        ],
        env=env,
    )
    assert res.returncode == 1
