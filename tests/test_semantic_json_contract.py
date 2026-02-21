"""
Golden snapshot test: freeze the semantic-enabled JSON report contract.

This test ensures the JSON structure remains stable across refactors.
No exact fingerprints or float values asserted—only structure, types, and keys.

Normalized fields:
- Lists sorted consistently
- Dict keys sorted
- Float scores rounded to 4 decimals
- Types and presence of all keys verified
"""

import json
import tempfile
from pathlib import Path

from flakeshield.cli import build_reports


def _normalize_report_for_comparison(report: dict) -> dict:
    """
    Normalize report by sorting for consistent comparison.

    Keeps structure and types.
    Ensures nested lists/dicts are ordered consistently.
    """
    normalized = {}

    # runs_considered: list of strings (sort for stable comparison)
    normalized["runs_considered"] = sorted(report.get("runs_considered", []))

    # run_count: integer
    normalized["run_count"] = report.get("run_count", 0)

    # flaky_tests: dict; sort outer keys
    flaky = report.get("flaky_tests", {})
    normalized["flaky_tests"] = {k: flaky[k] for k in sorted(flaky.keys())}

    # failure_groups: dict with structure {fingerprint: {count, examples}}
    # Keep as-is but ensure examples are sorted
    failure_groups = report.get("failure_groups", {})
    normalized["failure_groups"] = {}
    for fp in sorted(failure_groups.keys()):
        group = failure_groups[fp]
        if isinstance(group, dict) and "examples" in group:
            # Sort examples by test_id
            sorted_examples = sorted(
                group.get("examples", []), key=lambda e: e.get("test_id", "")
            )
            normalized["failure_groups"][fp] = {
                "count": group.get("count", 0),
                "examples": sorted_examples,
            }
        else:
            normalized["failure_groups"][fp] = group

    # semantic_failure_groups: list of dicts; sort by group_id for consistency
    semantic_groups = report.get("semantic_failure_groups", [])
    normalized["semantic_failure_groups"] = sorted(
        semantic_groups,
        key=lambda g: (
            g.get("group_id", float("inf")) if isinstance(g, dict) else float("inf")
        ),
    )

    # novel_failures: list of strings (sort)
    normalized["novel_failures"] = sorted(report.get("novel_failures", []))

    # known_failures: list of strings (sort)
    normalized["known_failures"] = sorted(report.get("known_failures", []))

    # novel_failure_matches: dict of lists; sort keys and matches
    novel_matches = report.get("novel_failure_matches", {})
    normalized["novel_failure_matches"] = {}
    for fp in sorted(novel_matches.keys()):
        match_list = novel_matches[fp]
        # Sort matches by fingerprint, round scores
        normalized_matches = [
            {
                "fingerprint": m["fingerprint"],
                "score": round(float(m["score"]), 4),
            }
            for m in match_list
        ]
        normalized_matches.sort(key=lambda m: m["fingerprint"])
        normalized["novel_failure_matches"][fp] = normalized_matches

    # risk_analysis: dict of dicts; sort keys and round scores
    risk = report.get("risk_analysis", {})
    normalized["risk_analysis"] = {}
    for fp in sorted(risk.keys()):
        analysis = risk[fp]
        # Round scores to 4 decimals
        normalized["risk_analysis"][fp] = {
            "risk_score": round(float(analysis.get("risk_score", 0.0)), 4),
            "components": {
                "flake_rate": round(
                    float(analysis.get("components", {}).get("flake_rate", 0.0)), 4
                ),
                "novelty": round(
                    float(analysis.get("components", {}).get("novelty", 0.0)), 4
                ),
                "similarity": round(
                    float(analysis.get("components", {}).get("similarity", 0.0)), 4
                ),
            },
        }  # metrics: dict with stable keys
    metrics = report.get("metrics", {})
    normalized["metrics"] = {
        "semantic_enabled": metrics.get("semantic_enabled", False),
        "fingerprint_group_count": metrics.get("fingerprint_group_count", 0),
        "semantic_group_count": metrics.get("semantic_group_count"),
        "fragmentation_delta": metrics.get("fragmentation_delta"),
    }

    return normalized


import pytest


def fake_embed(texts):
    import numpy as np

    return [np.zeros(384, dtype=np.float32) for _ in texts]


@pytest.fixture(autouse=True)
def patch_embed_texts(monkeypatch):
    import sys
    import types
    import numpy as np

    class DummyModel:
        def __init__(self, *args, **kwargs):
            pass

        def encode(self, texts, normalize_embeddings=True, convert_to_numpy=False):
            return [np.zeros(384, dtype=np.float32) for _ in texts]

    dummy_mod = types.ModuleType("sentence_transformers")
    dummy_mod.SentenceTransformer = DummyModel
    monkeypatch.setitem(sys.modules, "sentence_transformers", dummy_mod)

    # Patch the embedding function on the embeddings module (import will use dummy model)
    monkeypatch.setattr("flakeshield.embeddings.embed_texts", fake_embed, raising=False)


def test_semantic_json_contract_enabled():
    """
    Golden test: verify semantic-enabled JSON report structure is locked.

    Creates minimal test runs and generates reports with semantic enabled.
    Verifies all required fields and types are present.
    Does not assert exact values (those vary based on embeddings).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        report_prefix = str(Path(tmpdir) / "report")

        # Create minimal test runs (2 runs minimum to detect flakiness)
        # Run 1: pass
        junit_run1 = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="suite1" tests="1" failures="0">
    <testcase classname="suite1" name="test_pass" time="1.0">
    </testcase>
  </testsuite>
</testsuites>
"""

        # Run 2: fail
        junit_run2 = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="suite1" tests="1" failures="1">
    <testcase classname="suite1" name="test_fail" time="1.0">
      <failure message="Connection error">
        Error: Connection refused at line 50
      </failure>
    </testcase>
  </testsuite>
</testsuites>
"""

        # Write JUnit files
        run1_path = Path(tmpdir) / "report1.xml"
        run2_path = Path(tmpdir) / "report2.xml"
        run1_path.write_text(junit_run1)
        run2_path.write_text(junit_run2)

        # Run report generation with semantic enabled
        build_reports(
            xml_glob=str(Path(tmpdir) / "report*.xml"),
            out_prefix=report_prefix,
            db_path=db_path,
            enable_semantic=True,
        )

        # Load generated JSON report
        json_path = f"{report_prefix}.json"
        with open(json_path, "r") as f:
            report = json.load(f)

        # Normalize for comparison
        normalized = _normalize_report_for_comparison(report)

        # === Assert frozen structure ===

        # Top-level keys
        required_keys = [
            "runs_considered",
            "run_count",
            "flaky_tests",
            "failure_groups",
            "semantic_failure_groups",
            "novel_failures",
            "known_failures",
            "novel_failure_matches",
            "risk_analysis",
            "metrics",
        ]
        for key in required_keys:
            assert key in normalized, f"Missing required key: {key}"

        # runs_considered
        assert isinstance(
            normalized["runs_considered"], list
        ), "runs_considered must be list"
        assert all(
            isinstance(r, str) for r in normalized["runs_considered"]
        ), "All run IDs must be strings"
        assert len(normalized["runs_considered"]) >= 2, "Must have at least 2 runs"

        # run_count
        assert isinstance(normalized["run_count"], int), "run_count must be int"
        assert normalized["run_count"] >= 2, "run_count must be >= 2"

        # flaky_tests
        assert isinstance(normalized["flaky_tests"], dict), "flaky_tests must be dict"
        # Might be empty (all deterministic) or populated

        # failure_groups
        assert isinstance(
            normalized["failure_groups"], dict
        ), "failure_groups must be dict"
        for fp, group in normalized["failure_groups"].items():
            assert isinstance(fp, str), "Fingerprint must be string"
            assert isinstance(group, dict), "Each group must be dict"
            assert "count" in group, "Group must have count"
            assert "examples" in group, "Group must have examples"
            assert isinstance(group["count"], int), "count must be int"
            assert isinstance(group["examples"], list), "examples must be list"
            for example in group["examples"]:
                assert isinstance(example, dict), "Each example must be dict"
                assert "test_id" in example, "Example must have test_id"

        # semantic_failure_groups
        assert isinstance(
            normalized["semantic_failure_groups"], list
        ), "semantic_failure_groups must be list"
        for group in normalized["semantic_failure_groups"]:
            assert isinstance(group, dict), "Each group must be dict"
            assert "group_id" in group, "Each group must have group_id"
            assert "members" in group, "Each group must have members"
            members = group["members"]
            assert isinstance(members, list), "members must be list"
            if members:
                first = members[0]
                assert isinstance(first, dict), "Each member must be dict"
                assert "run_id" in first, "Member must have run_id"
                assert "test_id" in first, "Member must have test_id"
                assert "message" in first, "Member must have message"

        # novel_failures
        assert isinstance(
            normalized["novel_failures"], list
        ), "novel_failures must be list"
        assert all(
            isinstance(fp, str) for fp in normalized["novel_failures"]
        ), "All novel_failures must be strings"

        # known_failures
        assert isinstance(
            normalized["known_failures"], list
        ), "known_failures must be list"
        assert all(
            isinstance(fp, str) for fp in normalized["known_failures"]
        ), "All known_failures must be strings"

        # novel_failure_matches
        assert isinstance(
            normalized["novel_failure_matches"], dict
        ), "novel_failure_matches must be dict"
        for fp, matches in normalized["novel_failure_matches"].items():
            assert isinstance(fp, str), "Match fingerprint must be string"
            assert isinstance(matches, list), "Matches must be list"
            for match in matches:
                assert isinstance(match, dict), "Each match must be dict"
                assert "fingerprint" in match, "Match must have fingerprint"
                assert "score" in match, "Match must have score"
                assert isinstance(match["fingerprint"], str), "Match FP must be string"
                assert isinstance(match["score"], (int, float)), "Score must be numeric"
                assert (
                    -1 <= match["score"] <= 1
                ), f"Score out of [-1, 1]: {match['score']}"

        # risk_analysis
        assert isinstance(
            normalized["risk_analysis"], dict
        ), "risk_analysis must be dict"
        for fp, analysis in normalized["risk_analysis"].items():
            assert isinstance(fp, str), "Risk analysis FP must be string"
            assert isinstance(analysis, dict), "Each risk analysis must be dict"
            assert "risk_score" in analysis, "Risk analysis must have risk_score"
            assert "components" in analysis, "Risk analysis must have components"

            risk_score = analysis["risk_score"]
            assert isinstance(risk_score, (int, float)), "risk_score must be numeric"
            assert (
                0.0 <= risk_score <= 1.0
            ), f"risk_score out of [0.0, 1.0]: {risk_score}"

            components = analysis["components"]
            assert isinstance(components, dict), "components must be dict"
            assert "flake_rate" in components, "components must have flake_rate"
            assert "novelty" in components, "components must have novelty"
            assert "similarity" in components, "components must have similarity"

            for key in ["flake_rate", "novelty", "similarity"]:
                val = components[key]
                assert isinstance(val, (int, float)), f"component {key} must be numeric"
                assert 0.0 <= val <= 1.0, f"component {key} out of [0.0, 1.0]: {val}"

        # metrics
        assert isinstance(normalized["metrics"], dict), "metrics must be dict"
        assert (
            "semantic_enabled" in normalized["metrics"]
        ), "metrics must have semantic_enabled"
        assert (
            normalized["metrics"]["semantic_enabled"] is True
        ), "semantic_enabled must be True"
        assert (
            "fingerprint_group_count" in normalized["metrics"]
        ), "metrics must have fingerprint_group_count"
        assert (
            "semantic_group_count" in normalized["metrics"]
        ), "metrics must have semantic_group_count"
        assert (
            "fragmentation_delta" in normalized["metrics"]
        ), "metrics must have fragmentation_delta"


def test_semantic_json_contract_disabled():
    """
    Golden test: verify JSON structure with semantic DISABLED.

    Semantic fields should be empty/null, but deterministic fields present.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        report_prefix = str(Path(tmpdir) / "report")

        # Minimal test runs (2 required)
        junit_run1 = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="suite1" tests="1" failures="0">
    <testcase classname="suite1" name="test_pass" time="1.0">
    </testcase>
  </testsuite>
</testsuites>
"""

        junit_run2 = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="suite1" tests="1" failures="1">
    <testcase classname="suite1" name="test_fail" time="1.0">
      <failure message="error">trace</failure>
    </testcase>
  </testsuite>
</testsuites>
"""

        run1_path = Path(tmpdir) / "report1.xml"
        run2_path = Path(tmpdir) / "report2.xml"
        run1_path.write_text(junit_run1)
        run2_path.write_text(junit_run2)

        # Run WITHOUT semantic enabled
        build_reports(
            xml_glob=str(Path(tmpdir) / "report*.xml"),
            out_prefix=report_prefix,
            db_path=db_path,
            enable_semantic=False,
        )

        # Load JSON
        json_path = f"{report_prefix}.json"
        with open(json_path, "r") as f:
            report = json.load(f)

        # === Assert semantic fields are empty ===
        assert (
            report["semantic_failure_groups"] == []
        ), "semantic_failure_groups must be empty list"
        assert report["novel_failures"] == [], "novel_failures must be empty list"
        assert report["known_failures"] == [], "known_failures must be empty list"
        assert (
            report["novel_failure_matches"] == {}
        ), "novel_failure_matches must be empty dict"
        assert report["risk_analysis"] == {}, "risk_analysis must be empty dict"

        # === Assert deterministic fields still present ===
        assert "failure_groups" in report, "failure_groups must be present"
        assert isinstance(report["failure_groups"], dict), "failure_groups must be dict"

        assert "flaky_tests" in report, "flaky_tests must be present"
        assert isinstance(report["flaky_tests"], dict), "flaky_tests must be dict"

        # === Assert metrics reflect disabled state ===
        assert (
            report["metrics"]["semantic_enabled"] is False
        ), "semantic_enabled must be False"


if __name__ == "__main__":
    test_semantic_json_contract_enabled()
    print("✅ Semantic enabled contract test passed")

    test_semantic_json_contract_disabled()
    print("✅ Semantic disabled contract test passed")

    print("\n✅ All golden contract tests passed")
