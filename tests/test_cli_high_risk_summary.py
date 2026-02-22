import sys
import types
import json
from pathlib import Path

import numpy as np

from flakeshield.storage import connect


def fake_embed_texts(texts):
    return [np.ones(8, dtype=np.float32) for _ in texts]


def test_cli_high_risk_summary(tmp_path, monkeypatch, capsys):
    # Dummy embeddings module
    dummy = types.ModuleType("flakeshield.embeddings")
    dummy.embed_texts = fake_embed_texts
    dummy.MODEL_NAME = "dummy-model"

    def make_failure_text(message, traceback):
        return message or traceback

    dummy.make_failure_text = make_failure_text
    monkeypatch.setitem(sys.modules, "flakeshield.embeddings", dummy)
    monkeypatch.setattr("flakeshield.cli.embed_texts", fake_embed_texts, raising=False)

    # Create runs: one high-frequency failure and one low-frequency
    high_msg = "High failure occurred"
    low_msg = "Low flake occurred"
    for i in range(6):
        if i < 5:
            xml = f"""<?xml version='1.0'?>
<testsuites>
  <testsuite name='s' tests='2' failures='1'>
    <testcase classname='s' name='test_high' time='0.1'>
      <failure message='{high_msg}'>trace</failure>
    </testcase>
    <testcase classname='s' name='test_low' time='0.1'></testcase>
  </testsuite>
</testsuites>
"""
        else:
            xml = f"""<?xml version='1.0'?>
<testsuites>
  <testsuite name='s' tests='2' failures='1'>
    <testcase classname='s' name='test_high' time='0.1'></testcase>
    <testcase classname='s' name='test_low' time='0.1'>
      <failure message='{low_msg}'>trace</failure>
    </testcase>
  </testsuite>
</testsuites>
"""
        p = tmp_path / f"r{i+1}.xml"
        p.write_text(xml)

    # Pre-insert embedding for low to make it known/low-risk
    from flakeshield.fingerprint import fingerprint_failure

    low_fp = fingerprint_failure(low_msg, None)
    conn = connect(str(tmp_path / "fs.db"))
    try:
        import numpy as np
        from flakeshield.embeddings_store import upsert_embedding

        upsert_embedding(conn, low_fp, dummy.MODEL_NAME, np.zeros(8, dtype=np.float32))
    finally:
        conn.close()

    # Run builder
    from flakeshield.cli import build_reports

    out_prefix = str(tmp_path / "out_report")
    build_reports(
        str(tmp_path / "r*.xml"),
        out_prefix,
        str(tmp_path / "fs.db"),
        enable_semantic=True,
    )

    captured = capsys.readouterr()
    out = captured.out

    assert "High Risk Failures:" in out
    assert "1." in out  # at least one numbered entry
