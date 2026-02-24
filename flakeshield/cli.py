"""
FlakeShield CLI (v0.1)

Goal: product-shaped entrypoint
- input: glob of junit xml files
- output: json + md reports
- prints summary to console
"""

import argparse
import glob
import json
import os

from flakeshield.config import load_config
from flakeshield.db_queries import get_failure_groups, get_flaky_tests
from flakeshield.fingerprint import fingerprint_failure
from flakeshield.known_novel import classify_known_novel
from flakeshield.parse_junit import parse_pytest_junit
from flakeshield.risk_scoring import compute_risk_analysis
from flakeshield.policy import classify_risk_tier
from flakeshield.scoring import top_flakiest
from flakeshield.similarity import get_top_k_similar
from flakeshield.storage import connect, insert_runs


def build_reports(
    xml_glob: str,
    out_prefix: str = "flake_report",
    db_path: str = "outputs/flakeshield.db",
    enable_semantic: bool = False,
    min_runs: int = 4,
) -> None:
    xml_paths = sorted(glob.glob(xml_glob))

    if len(xml_paths) < 2:
        raise SystemExit("Need at least 2 XML files to detect flakiness.")

    runs = [parse_pytest_junit(p) for p in xml_paths]
    run_ids = [r["run_id"] for r in runs]

    # Attach fingerprint to each failing/error case before storing/reporting
    for run in runs:
        for case in run["cases"]:
            if case["status"] in ("failed", "error"):
                case["fingerprint"] = fingerprint_failure(
                    case.get("message"), case.get("traceback")
                )

    # Ensure DB directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = connect(db_path)
    try:
        inserted = insert_runs(conn, runs)

        # DB-only analytics MUST happen while connection is open
        failure_groups = get_failure_groups(conn, limit=20)
        top_flakes = top_flakiest(conn, limit=10)
        flaky = get_flaky_tests(conn, min_runs=min_runs)
    finally:
        conn.close()

    print(f"Saved {inserted} test results to {db_path}")

    # --- ML-assisted semantic failure groups (OPT-IN, non-authoritative) ---
    semantic_groups = []
    semantic_group_count = None
    fragmentation_delta = None
    novel_failure_matches = {}
    risk_analysis = {}

    # NOTE: get_failure_groups returns dict-like in your implementation
    # If it returns a dict, len(...) gives number of groups.
    fingerprint_group_count = len(failure_groups) if failure_groups else 0

    if enable_semantic:
        # Import and run semantic-only logic when explicitly requested.
        # Wrap entire block so failures are non-blocking.
        try:
            from flakeshield.semantic_grouping import semantic_groups_from_cases

            failing_cases = [
                c
                for run in runs
                for c in run["cases"]
                if c["status"] in ("failed", "error")
            ]

            # Known vs novel classification using persisted embeddings (Week 4)
            known_failures = []
            novel_failures = []

            try:
                # local import to avoid loading model unless needed
                if os.getenv("FLAKESHIELD_DUMMY_EMBEDS"):
                    # test-mode: use lightweight stub to avoid HF downloads
                    import numpy as _np

                    def embed_texts(texts):
                        return [_np.ones(8, dtype=_np.float32) for _ in texts]

                    MODEL_NAME = "dummy-model"

                    def get_embedding(conn, fp, model):
                        return None

                    def upsert_embedding(conn, fp, model, vec):
                        return None

                else:
                    from flakeshield.embeddings import embed_texts, MODEL_NAME
                    from flakeshield.embeddings_store import (
                        get_embedding,
                        upsert_embedding,
                    )
            except Exception:
                # If embedding infra isn't available, skip known/novel classification
                embed_texts = None
                MODEL_NAME = None
                get_embedding = None
                upsert_embedding = None

            # Classify by fingerprint using DB persistence
            if os.getenv("FLAKESHIELD_FORCE_NOVEL"):
                # test-mode shortcut: mark every fingerprint as novel
                known_failures = []
                novel_failures = list(failure_groups.keys()) if failure_groups else []
            elif (
                failure_groups
                and MODEL_NAME
                and get_embedding
                and upsert_embedding
                and embed_texts
            ):
                conn2 = connect(db_path)
                try:
                    known_failures, novel_failures = classify_known_novel(
                        conn2,
                        failure_groups,
                        MODEL_NAME,
                        embed_texts,
                        get_embedding,
                        upsert_embedding,
                    )

                    # Similarity lookup for novel failures (Phase B Step 2)
                    # For each novel fingerprint, find top-k similar historical embeddings
                    if novel_failures and MODEL_NAME and get_embedding:
                        try:
                            for fp_novel in novel_failures:
                                vec_novel = get_embedding(conn2, fp_novel, MODEL_NAME)
                                if vec_novel is not None:
                                    matches = get_top_k_similar(
                                        conn2,
                                        vec_novel,
                                        MODEL_NAME,
                                        k=3,
                                        exclude_fingerprint=fp_novel,
                                    )
                                    novel_failure_matches[fp_novel] = [
                                        {"fingerprint": fp, "score": float(score)}
                                        for fp, score in matches
                                    ]
                        except Exception:
                            # Non-blocking: similarity lookup failure doesn't affect primary results
                            pass
                except Exception:
                    # Non-blocking: any error in classification reverts to empty lists
                    known_failures = []
                    novel_failures = []
                    novel_failure_matches = {}
                finally:
                    conn2.close()
            else:
                known_failures = []
                novel_failures = []
                novel_failure_matches = {}

            # Compute semantic groups (assistive view)
            semantic_groups = semantic_groups_from_cases(
                failing_cases,
                threshold=0.80,
            )

            semantic_group_count = len(semantic_groups)
            fragmentation_delta = fingerprint_group_count - semantic_group_count

            # Compute risk analysis for each fingerprint (Phase C)
            # Advisory layer: combines deterministic flake_rate with semantic novelty/similarity
            # Prepare risk assessment (advisory, semantic-only)
            from flakeshield.risk import compute_risk_score

            risk_assessment = {}

            for fp, group in failure_groups.items():
                # Deterministic: flake_rate based on frequency
                # (count / total_runs gives us how often this fingerprint occurs)
                failure_count = group.get("count", 0)
                total_runs = len(run_ids) if run_ids else 1
                flake_rate = min(1.0, failure_count / max(1, total_runs))

                # Semantic: is_novel
                is_novel = fp in novel_failures

                # Semantic: max_similarity_score
                max_similarity_score = None
                if fp in novel_failure_matches and novel_failure_matches[fp]:
                    # Get highest similarity score for this fingerprint
                    max_similarity_score = max(
                        m.get("score", 0.0) for m in novel_failure_matches[fp]
                    )

                # Compute risk
                risk_analysis[fp] = compute_risk_analysis(
                    flake_rate=flake_rate,
                    is_novel=is_novel,
                    max_similarity_score=max_similarity_score,
                )

                # Build risk_assessment entry (advisory)
                score = compute_risk_score(
                    flake_rate=flake_rate,
                    is_novel=is_novel,
                    max_similarity=max_similarity_score,
                    runs_seen=total_runs,
                )

                # Apply small penalty if this fingerprint is related to flaky tests
                # Definition: is_flaky_related = any example's test_id appears in `flaky` mapping
                is_flaky_related = False
                try:
                    examples = (
                        group.get("examples", []) if isinstance(group, dict) else []
                    )
                    for ex in examples:
                        test_id = ex.get("test_id")
                        if test_id and test_id in flaky:
                            is_flaky_related = True
                            break
                except Exception:
                    # Be conservative: if we can't determine, assume not flaky-related
                    is_flaky_related = False

                if is_flaky_related:
                    score = float(score) * 0.85

                # Clamp just in case
                if score < 0.0:
                    score = 0.0
                if score > 1.0:
                    score = 1.0

                tier = classify_risk_tier(score)
                risk_assessment[fp] = {
                    "risk_score": float(score),
                    "risk_tier": tier,
                    "reasons": {
                        "flake_rate": float(flake_rate),
                        "novel": bool(is_novel),
                        "max_similarity": (
                            float(max_similarity_score)
                            if max_similarity_score is not None
                            else None
                        ),
                        "runs_seen": int(total_runs),
                    },
                }
        except Exception as e:
            print(f"⚠️  Warning: Semantic grouping failed (non-blocking): {e}")
            print("   Continuing without semantic analysis.")
            semantic_groups = []
            semantic_group_count = None
            fragmentation_delta = None
            known_failures = []
            novel_failures = []
            novel_failure_matches = {}
            risk_analysis = {}
            risk_assessment = {}

    # Ensure output directory exists (if user passed a path like outputs/flake_report)
    out_dir = os.path.dirname(out_prefix)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    # JSON report
    report = {
        "runs_considered": run_ids,
        "run_count": len(run_ids),
        "flaky_tests": flaky,
        "failure_groups": failure_groups,
        "semantic_failure_groups": semantic_groups if enable_semantic else [],
        "novel_failures": novel_failures if enable_semantic else [],
        "known_failures": known_failures if enable_semantic else [],
        "novel_failure_matches": novel_failure_matches if enable_semantic else {},
        "risk_analysis": risk_analysis if enable_semantic else {},
        "risk_assessment": risk_assessment if enable_semantic else {},
        "metrics": {
            "semantic_enabled": enable_semantic,
            "fingerprint_group_count": fingerprint_group_count,
            "semantic_group_count": semantic_group_count,
            "fragmentation_delta": fragmentation_delta,
        },
    }

    json_path = f"{out_prefix}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Markdown report
    lines: list[str] = []
    lines.append("# FlakeShield Report")
    lines.append("")
    lines.append(f"- Runs considered: **{len(run_ids)}**")
    lines.append("")

    if not flaky:
        lines.append("✅ No flaky tests detected.")
    else:
        lines.append("## ⚠️ Flaky tests detected")
        for test_id, data in sorted(flaky.items()):
            lines.append(
                f"- **{test_id}** → "
                f"`{', '.join(data['statuses'])}` "
                f"(runs={data['runs_seen']}, "
                f"flake_rate={data['flake_rate']:.2f}, "
                f"confidence={data['confidence']})"
            )

    lines.append("")
    lines.append("## 🔥 Failure groups")
    if not failure_groups:
        lines.append("✅ No failures/errors to group.")
    else:
        # Your failure_groups appears dict-like: {fingerprint: {count, examples}}
        sorted_groups = sorted(
            failure_groups.items(),
            key=lambda kv: kv[1]["count"],
            reverse=True,
        )
        for i, (fp, data) in enumerate(sorted_groups, start=1):
            lines.append(f"### Group {i} — {data['count']} occurrences")
            lines.append("Fingerprint:")
            lines.append(f"`{fp[:180]}`")
            lines.append("Examples:")
            for ex in data["examples"]:
                lines.append(
                    f"- `{ex['run_id']}` — **{ex['test_id']}** — {ex.get('message')}"
                )
            lines.append("")

    # Semantic section ONLY when enabled
    if enable_semantic:
        lines.append("")
        lines.append("## 🧠 Semantic failure groups (ML-assisted, experimental)")
        lines.append("- Similarity threshold: **0.80**")
        lines.append("")

        if not semantic_groups:
            lines.append("✅ No semantic groups (no failures/errors to cluster).")
        else:
            for g in semantic_groups:
                rep = g["representative"]
                lines.append(
                    f"### Semantic Group {g['group_id']} — {g['size']} occurrences"
                )
                lines.append(f"- Representative: `{rep.get('message')}`")
                lines.append("Members:")
                for m in g["members"]:
                    lines.append(
                        f"- `{m['run_id']}` — **{m['test_id']}** — {m.get('message')}"
                    )
                lines.append("")

    lines.append("")
    lines.append("## 📊 Top flakiest tests")
    if not top_flakes:
        lines.append("✅ No flaky tests with enough history to score.")
    else:
        lines.append("| Test ID | Runs | Passes | Fails |")
        lines.append("|---|---:|---:|---:|")
        for test_id, runs_seen, pass_count, fail_count in top_flakes:
            lines.append(f"| `{test_id}` | {runs_seen} | {pass_count} | {fail_count} |")

    lines.append("")
    lines.append("## Runs included")
    for p in xml_paths:
        lines.append(f"- `{p}`")

    md_path = f"{out_prefix}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    # Console summary
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")

    if not flaky:
        print("No flaky tests detected (no status changes across runs).")
    else:
        print(f"Flaky tests detected (from {len(run_ids)} runs):")
        for test_id, data in sorted(flaky.items()):
            print(
                f"- {test_id}: {data['statuses']} "
                f"(runs={data['runs_seen']}, "
                f"flake_rate={data['flake_rate']:.2f}, "
                f"confidence={data['confidence']})"
            )

    # CLI summary: print top high-risk failures when semantic mode is enabled
    if enable_semantic:
        try:
            if risk_assessment:
                # Extract and sort top entries by risk_score desc
                items = sorted(
                    risk_assessment.items(),
                    key=lambda kv: float(kv[1].get("risk_score", 0.0)),
                    reverse=True,
                )[:5]

                if items:
                    print("\nHigh Risk Failures:")
                    for i, (fp, info) in enumerate(items, start=1):
                        score = float(info.get("risk_score", 0.0))
                        print(f"{i}. {fp} — {score:.2f}")
        except Exception:
            # Non-blocking: don't let summary printing affect exit code
            pass


def main() -> None:
    p = argparse.ArgumentParser(
        prog="flakeshield", description="CI signal reduction tool"
    )
    p.add_argument(
        "--reports",
        default="report*.xml",
        help="Glob for JUnit XML files (default: report*.xml)",
    )
    p.add_argument(
        "--out",
        default="flake_report",
        help="Output prefix (writes <out>.json and <out>.md)",
    )
    p.add_argument(
        "--db",
        default="outputs/flakeshield.db",
        help="SQLite DB path (default: outputs/flakeshield.db)",
    )
    p.add_argument(
        "--config",
        default=None,
        help="Path to JSON config file (default: ./.flakeshield.json)",
    )
    p.add_argument(
        "--min-runs",
        type=int,
        dest="min_runs",
        help="Minimum runs for flakiness detection (default: 4)",
    )
    p.add_argument(
        "--enable-semantic",
        action="store_true",
        help="Enable ML-assisted semantic failure grouping (default: off)",
    )
    p.add_argument(
        "--warn-on-high",
        action="store_true",
        help="Print warning if any fingerprint has tier HIGH or CRITICAL",
    )
    p.add_argument(
        "--fail-on-critical",
        action="store_true",
        help="Exit nonzero if any fingerprint has tier CRITICAL",
    )
    p.add_argument(
        "--max-risk-threshold",
        type=float,
        help="Exit nonzero if any risk_score >= threshold",
    )

    args = p.parse_args()
    # load configuration and apply defaults
    cfg = load_config(args.config)

    # determine effective options
    min_runs = args.min_runs if args.min_runs is not None else cfg.get("min_runs", 4)
    enable_semantic = args.enable_semantic or cfg.get("enable_semantic", False)

    build_reports(
        args.reports,
        args.out,
        args.db,
        enable_semantic=enable_semantic,
        min_runs=min_runs,
    )

    # policy enforcement (semantic-only)
    from flakeshield.policy import evaluate_policy

    # load report JSON file
    report_path = f"{args.out}.json"
    exit_code = 0
    warnings = []
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
        exit_code, warnings = evaluate_policy(
            report,
            warn_on_high=args.warn_on_high,
            fail_on_critical=args.fail_on_critical,
            max_risk_threshold=args.max_risk_threshold,
        )
        for w in warnings:
            print(w)
    except Exception:
        # if loading fails or policy eval fails, we silently ignore to keep CLI stable
        exit_code = 0

    if exit_code != 0:
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
