import sys
import types
import json
from pathlib import Path

from flakeshield.storage import connect


def fake_embed_texts(texts):
    # simple dummy embedding
    import numpy as np

    return [np.ones(8, dtype=np.float32) for _ in texts]


def test_flaky_penalty_prefers_novel(tmp_path, monkeypatch):
    # Create DB path
    db_path = str(tmp_path / "fs.db")

    # Dummy embeddings module to satisfy semantic path
    dummy = types.ModuleType("flakeshield.embeddings")
    dummy.embed_texts = fake_embed_texts
    dummy.MODEL_NAME = "dummy-model"

    # make_failure_text used by semantic_grouping
    def make_failure_text(message, traceback):
        return message or traceback

    dummy.make_failure_text = make_failure_text
    monkeypatch.setitem(sys.modules, "flakeshield.embeddings", dummy)

    # Patch cli usage site for embed_texts
    monkeypatch.setattr("flakeshield.cli.embed_texts", fake_embed_texts, raising=False)
    monkeypatch.setattr("flakeshield.cli.MODEL_NAME", dummy.MODEL_NAME, raising=False)
    # Provide simple stubs for embedding store functions so the semantic branch runs
    monkeypatch.setattr(
        "flakeshield.cli.get_embedding", lambda conn, fp, m: None, raising=False
    )
    monkeypatch.setattr(
        "flakeshield.cli.upsert_embedding", lambda conn, fp, m, v: None, raising=False
    )

    # Prepare 10 runs: flaky test fails 9 times, novel test fails 6 times
    runs = []
    flaky_msg = "Flaky failure occurred"
    novel_msg = "Novel regression occurred"

    for i in range(10):
        if i < 9:
            flaky_case = f"<testcase classname='s' name='test_flaky' time='0.1'><failure message='{flaky_msg}'>t</failure></testcase>"
        else:
            flaky_case = (
                "<testcase classname='s' name='test_flaky' time='0.1'></testcase>"
            )

        if i < 6:
            novel_case = f"<testcase classname='s' name='test_novel' time='0.1'><failure message='{novel_msg}'>t</failure></testcase>"
        else:
            # Omit novel test entirely in later runs so it is not marked as flaky
            novel_case = ""

        xml = f"""<?xml version='1.0'?>
<testsuites>
  <testsuite name='s' tests='2' failures='1'>
    {flaky_case}
    {novel_case}
  </testsuite>
</testsuites>
"""
        p = tmp_path / f"r{i+1}.xml"
        p.write_text(xml)

    # Monkeypatch classify_known_novel to mark novel fingerprint as novel
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

        novel_fp = fingerprint_failure(novel_msg, None)
        return ([], [novel_fp])

    monkeypatch.setattr(
        "flakeshield.cli.classify_known_novel", fake_classify, raising=False
    )

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

    ra = report.get("risk_assessment", {})
    from flakeshield.fingerprint import fingerprint_failure

    flaky_fp = fingerprint_failure(flaky_msg, None)
    novel_fp = fingerprint_failure(novel_msg, None)

    assert flaky_fp in ra
    assert novel_fp in ra

    flaky_score = ra[flaky_fp]["risk_score"]
    novel_score = ra[novel_fp]["risk_score"]

    # After applying flaky penalty, novel should not score lower than flaky
    # (equality is acceptable if penalty exactly offsets rate differences).
    assert (
        novel_score >= flaky_score
    ), f"expected novel {novel_score} >= flaky {flaky_score}"
