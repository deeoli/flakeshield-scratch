import sys
import types
import json
from pathlib import Path

from flakeshield.storage import connect


def fake_embed_texts(texts):
    import numpy as np

    return [np.ones(8, dtype=np.float32) for _ in texts]


def test_risk_tier_integration(tmp_path, monkeypatch):
    # similar to earlier integration test but we just check for risk_tier
    db_path = str(tmp_path / "fs.db")

    dummy = types.ModuleType("flakeshield.embeddings")
    dummy.embed_texts = fake_embed_texts
    dummy.MODEL_NAME = "dummy-model"

    def make_failure_text(message, traceback):
        return message or traceback

    dummy.make_failure_text = make_failure_text
    monkeypatch.setitem(sys.modules, "flakeshield.embeddings", dummy)
    monkeypatch.setattr("flakeshield.cli.embed_texts", fake_embed_texts, raising=False)
    monkeypatch.setattr("flakeshield.cli.MODEL_NAME", dummy.MODEL_NAME, raising=False)
    monkeypatch.setattr(
        "flakeshield.cli.get_embedding", lambda conn, fp, m: None, raising=False
    )
    monkeypatch.setattr(
        "flakeshield.cli.upsert_embedding", lambda conn, fp, m, v: None, raising=False
    )

    # build simple runs with two different failures
    msgs = ["foo", "bar"]
    for i, msg in enumerate(msgs):
        xml = f"""<?xml version='1.0'?>
<testsuites>
  <testsuite name='s' tests='1' failures='1'>
    <testcase classname='s' name='t{i}' time='0.1'><failure message='{msg}'>x</failure></testcase>
  </testsuite>
</testsuites>
"""
        (tmp_path / f"r{i+1}.xml").write_text(xml)

    # force classify_known_novel to mark both as novel
    def fake_classify(
        conn,
        failure_groups,
        model_name,
        embed_texts_fn,
        get_embedding,
        upsert_embedding,
        current_run_ids=None,
    ):
        from flakeshield.fingerprint import fingerprint_failure

        return ([], [fingerprint_failure(m, None) for m in msgs])

    monkeypatch.setattr(
        "flakeshield.cli.classify_known_novel", fake_classify, raising=False
    )

    from flakeshield.cli import build_reports

    out_prefix = str(tmp_path / "out")
    build_reports(str(tmp_path / "r*.xml"), out_prefix, db_path, enable_semantic=True)
    report = json.load(open(out_prefix + ".json"))
    ra = report.get("risk_assessment", {})
    assert ra, "risk_assessment missing"
    for fp, info in ra.items():
        assert "risk_score" in info
        assert 0.0 <= info["risk_score"] <= 1.0
        assert "risk_tier" in info
        assert info["risk_tier"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
