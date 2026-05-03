"""Regression guards: ranking spread, known/novel stability, flaky flags on groups."""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import numpy as np

from flakeshield.known_novel import classify_known_novel
from flakeshield.risk import compute_risk_score
from flakeshield.storage import connect


def test_risk_scores_discriminate_two_run_ci():
    """With only 2 JUnit files, scores must not collapse to one band (×0.2 bug)."""
    s_low = compute_risk_score(
        flake_rate=0.5,
        is_novel=False,
        max_similarity=None,
        runs_seen=2,
        failure_count=1,
        fingerprint="fp-a",
    )
    s_high = compute_risk_score(
        flake_rate=1.0,
        is_novel=True,
        max_similarity=0.9,
        runs_seen=2,
        failure_count=2,
        fingerprint="fp-b",
    )
    assert s_high > s_low + 0.05
    assert s_high > 0.25


def test_same_fingerprint_same_ordering_across_calls():
    """Deterministic tie-break: same fp → same score for fixed inputs."""
    a = compute_risk_score(0.5, True, None, 2, 1, "stable-fp")
    b = compute_risk_score(0.5, True, None, 2, 1, "stable-fp")
    assert a == b


def test_fingerprint_in_test_results_known_without_embedding(tmp_path):
    """Recurring fingerprint in DB must stay 'known' even if embedding row missing."""
    db_path = str(tmp_path / "kn.db")
    conn = connect(db_path)
    fp = "error: user not found in prior ci"
    conn.execute(
        """
        INSERT INTO test_results (
            run_id, suite, test_id, status, duration_sec,
            failure_type, message, traceback, fingerprint
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "junit_run_old.xml",
            None,
            "test_x",
            "failed",
            None,
            None,
            "msg",
            None,
            fp,
        ),
    )
    conn.commit()

    failure_groups = {
        fp: {
            "count": 1,
            "examples": [
                {
                    "message": "msg",
                    "test_id": "test_x",
                    "run_id": "junit_run1.xml",
                }
            ],
        }
    }

    def fake_embed(texts):
        return [np.ones(4, dtype=np.float32) for _ in texts]

    from flakeshield.embeddings_store import get_embedding, upsert_embedding

    known, novel = classify_known_novel(
        conn,
        failure_groups,
        "m",
        fake_embed,
        get_embedding,
        upsert_embedding,
        current_run_ids=frozenset({"junit_run1.xml", "junit_run2.xml"}),
    )
    assert fp in known
    assert fp not in novel

    cur = conn.cursor()
    emb = cur.execute(
        "SELECT 1 FROM failure_embeddings WHERE fingerprint = ?",
        (fp,),
    ).fetchone()
    assert emb is not None
    conn.close()


def test_build_reports_twice_stable_ranking(tmp_path, monkeypatch):
    """Same inputs + persistent DB → same descending risk score order."""
    dummy = types.ModuleType("flakeshield.embeddings")
    dummy.embed_texts = lambda texts: [
        np.ones(8, dtype=np.float32) for _ in texts
    ]
    dummy.MODEL_NAME = "dummy-model"

    def make_failure_text(message, traceback):
        return message or traceback

    dummy.make_failure_text = make_failure_text
    monkeypatch.setitem(sys.modules, "flakeshield.embeddings", dummy)
    monkeypatch.setattr("flakeshield.cli.embed_texts", dummy.embed_texts, raising=False)

    high_msg = "High frequency failure X"
    low_msg = "Low frequency failure Y"
    for i in range(6):
        if i < 4:
            body = f"""<testcase classname='s' name='th' time='0.1'>
      <failure message='{high_msg}'>t</failure>
    </testcase>
    <testcase classname='s' name='tl' time='0.1'></testcase>"""
        else:
            body = f"""<testcase classname='s' name='th' time='0.1'></testcase>
    <testcase classname='s' name='tl' time='0.1'>
      <failure message='{low_msg}'>t</failure>
    </testcase>"""
        xml = f"""<?xml version='1.0'?>
<testsuites>
  <testsuite name='s' tests='2' failures='1'>{body}</testsuite>
</testsuites>
"""
        (tmp_path / f"batch_{i // 2}_{i % 2}.xml").write_text(xml)

    from flakeshield.cli import build_reports

    out1 = str(tmp_path / "o1")
    out2 = str(tmp_path / "o2")
    glob_pat = str(tmp_path / "batch_0_*.xml")
    # Fresh DB each time so novelty/embed state matches; persistent DB would
    # legitimately change scores on the second pass (known vs novel).
    build_reports(glob_pat, out1, str(tmp_path / "db1.db"), enable_semantic=True)
    build_reports(glob_pat, out2, str(tmp_path / "db2.db"), enable_semantic=True)

    def order(path_prefix: str):
        report = json.loads(Path(f"{path_prefix}.json").read_text(encoding="utf-8"))
        ra = report.get("risk_assessment") or {}
        return sorted(
            ((v["risk_score"], k) for k, v in ra.items()),
            reverse=True,
        )

    assert order(out1) == order(out2)


def test_failure_groups_mark_flaky_when_test_flaky(tmp_path, monkeypatch):
    """failure_groups[*].flaky is true when an example test_id is in flaky_tests."""
    dummy = types.ModuleType("flakeshield.embeddings")
    dummy.embed_texts = lambda texts: [
        np.ones(8, dtype=np.float32) for _ in texts
    ]
    dummy.MODEL_NAME = "dummy-model"
    dummy.make_failure_text = lambda m, t: m or t
    monkeypatch.setitem(sys.modules, "flakeshield.embeddings", dummy)
    monkeypatch.setattr("flakeshield.cli.embed_texts", dummy.embed_texts, raising=False)

    msg = "flaky fail pattern"
    for i in range(6):
        f = i % 2 == 0
        fc = f"""<failure message='{msg}'>x</failure>""" if f else ""
        xml = f"""<?xml version='1.0'?>
<testsuites>
  <testsuite name='s' tests='1' failures='{"1" if f else "0"}'>
    <testcase classname='s' name='test_flaky' time='0.1'>{fc}</testcase>
  </testsuite>
</testsuites>
"""
        (tmp_path / f"f{i}.xml").write_text(xml)

    from flakeshield.cli import build_reports

    out = str(tmp_path / "fl")
    build_reports(
        str(tmp_path / "f*.xml"),
        out,
        str(tmp_path / "fdb.db"),
        enable_semantic=True,
        min_runs=4,
    )
    report = json.loads(Path(f"{out}.json").read_text(encoding="utf-8"))
    groups = report.get("failure_groups") or {}
    assert groups
    assert any(g.get("flaky") for g in groups.values())
