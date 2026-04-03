import sys
import types
import json
import tempfile
from pathlib import Path

import numpy as np

from flakeshield.storage import connect


def fake_embed_texts(texts):
    return [np.ones(8, dtype=np.float32) for _ in texts]


def test_risk_integration(tmp_path, monkeypatch):
    # Prepare tmp DB and pre-insert a known embedding for low-risk fingerprint
    db_path = str(tmp_path / "fs.db")

    # Prepare dummy embeddings module to avoid HF
    dummy = types.ModuleType("flakeshield.embeddings")
    dummy.embed_texts = fake_embed_texts
    dummy.MODEL_NAME = "dummy-model"

    # Provide make_failure_text used by semantic_grouping
    def make_failure_text(message, traceback):
        return message or traceback

    dummy.make_failure_text = make_failure_text
    monkeypatch.setitem(sys.modules, "flakeshield.embeddings", dummy)

    # Patch cli usage site
    monkeypatch.setattr("flakeshield.cli.embed_texts", fake_embed_texts, raising=False)

    # Create multiple runs where high test fails frequently, low test rarely
    runs = []
    high_msg = "High failure occurred"
    low_msg = "Low flake occurred"

    # Create 6 runs: high fails in 5 runs, low fails in 1 run
    for i in range(6):
        if i < 5:
            # high fails
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
            # low fails only in last run
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

    # Compute low fingerprint to pre-insert embedding so it's known
    from flakeshield.fingerprint import fingerprint_failure

    low_fp = fingerprint_failure(low_msg, None)

    # Pre-insert embedding for low_fp so it is treated as known
    conn = connect(db_path)
    try:
        import numpy as np
        from flakeshield.embeddings_store import upsert_embedding

        upsert_embedding(conn, low_fp, dummy.MODEL_NAME, np.zeros(8, dtype=np.float32))
    finally:
        conn.close()

    # Run build_reports
    from flakeshield.cli import build_reports

    out_prefix = str(tmp_path / "out_report")

    build_reports(
        xml_glob=str(tmp_path / "r*.xml"),
        out_prefix=out_prefix,
        db_path=db_path,
        enable_semantic=True,
    )

    with open(f"{out_prefix}.json", "r", encoding="utf-8") as f:
        report = json.load(f)

    assert "risk_assessment" in report
    ra = report["risk_assessment"]
    assert isinstance(ra, dict)

    # There should be an entry for the high fingerprint (generated from message)
    high_fp = fingerprint_failure(high_msg, None)
    assert high_fp in ra
    assert low_fp in ra

    high_score = ra[high_fp]["risk_score"]
    low_score = ra[low_fp]["risk_score"]

    assert 0.0 <= high_score <= 1.0
    assert 0.0 <= low_score <= 1.0
    assert high_score > low_score
