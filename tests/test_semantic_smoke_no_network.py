import sys
import types
import json
import numpy as np
import tempfile
from pathlib import Path

import pytest

from flakeshield.storage import connect


def fake_embed_texts(texts):
    # Return stable vectors of ones (dim=8) for any input
    return [np.ones(8, dtype=np.float32) for _ in texts]


def test_semantic_smoke_no_network(tmp_path, monkeypatch, capsys):
    # Prepare a temp DB path
    db_path = str(tmp_path / "fs.db")

    # Insert a dummy flakeshield.embeddings module into sys.modules so
    # imports inside build_reports don't try to load HuggingFace.
    dummy = types.ModuleType("flakeshield.embeddings")
    dummy.embed_texts = fake_embed_texts
    dummy.MODEL_NAME = "dummy-model"
    monkeypatch.setitem(sys.modules, "flakeshield.embeddings", dummy)

    # Also set attribute on cli module import site (safe, non-raising)
    monkeypatch.setattr("flakeshield.cli.embed_texts", fake_embed_texts, raising=False)

    # Create two minimal JUnit XML files (one pass, one fail)
    junit_run1 = """<?xml version='1.0' encoding='UTF-8'?>
<testsuites>
  <testsuite name="suite1" tests="1" failures="0">
    <testcase classname="suite1" name="test_pass" time="0.1"/>
  </testsuite>
</testsuites>
"""

    junit_run2 = """<?xml version='1.0' encoding='UTF-8'?>
<testsuites>
  <testsuite name="suite1" tests="1" failures="1">
    <testcase classname="suite1" name="test_fail" time="0.2">
      <failure message="boom">Traceback line</failure>
    </testcase>
  </testsuite>
</testsuites>
"""

    run1 = tmp_path / "report1.xml"
    run2 = tmp_path / "report2.xml"
    run1.write_text(junit_run1)
    run2.write_text(junit_run2)

    # Call build_reports (import here to use CLI builder)
    from flakeshield.cli import build_reports

    out_prefix = str(tmp_path / "out_report")

    # Run semantic-enabled report generation
    build_reports(
        xml_glob=str(tmp_path / "report*.xml"),
        out_prefix=out_prefix,
        db_path=db_path,
        enable_semantic=True,
    )

    # Load generated JSON report
    with open(f"{out_prefix}.json", "r", encoding="utf-8") as f:
        report = json.load(f)

    # Basic assertions on semantic metadata
    assert isinstance(report.get("known_failures"), list)
    assert isinstance(report.get("novel_failures"), list)
    assert isinstance(report.get("novel_failure_matches"), dict)
    assert isinstance(report.get("risk_analysis"), dict)
    assert report.get("metrics", {}).get("semantic_enabled") is True

    # Best-effort: ensure no HuggingFace import warnings printed to stderr
    captured = capsys.readouterr()
    assert "HuggingFace" not in captured.err
