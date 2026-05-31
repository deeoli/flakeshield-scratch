"""Deterministic markdown UX helpers for actionable report output."""

from __future__ import annotations

import re
from typing import Any


def human_title(
    message: str | None = None,
    test_id: str | None = None,
    fingerprint: str | None = None,
) -> str:
    """Return a human-readable issue title from failure signals."""
    combined = " ".join(
        part for part in (message or "", fingerprint or "", test_id or "") if part
    ).lower()

    if "timeout" in combined or "timed out" in combined:
        return "Network timeout while calling task service"
    if "race condition" in combined or (
        "race" in combined and ("async" in combined or "condition" in combined)
    ):
        return "Race condition in task fetch"
    if any(
        token in combined
        for token in (
            "connection refused",
            "econnrefused",
            "connection error",
            "connection timed",
            "connection reset",
        )
    ):
        return "Connection failure to dependency"
    if "unable to find" in combined or (
        "not found" in combined and ("element" in combined or "role=" in combined)
    ):
        return "UI element or resource not found"
    if "assert" in combined or "assertion" in combined:
        if message:
            excerpt = _first_meaningful_clause(message)
            if excerpt:
                return f"Assertion mismatch: {excerpt}"
        return "Assertion mismatch in test behavior"

    if test_id:
        return _humanize_test_id(test_id)
    if fingerprint:
        return _compact_text(fingerprint, max_chars=80)
    return "Unknown failure"


def failure_status(
    *,
    is_novel: bool,
    is_flaky_related: bool,
    group_count: int,
    seen_runs: int,
) -> str:
    """Classify a failure group for Fix First display."""
    if is_novel:
        return "New"
    if is_flaky_related:
        return "Flaky"
    if group_count > 1 or seen_runs > 1:
        return "Recurring"
    return "New"


def why_this_matters_text(
    status: str,
    *,
    flake_rate: float = 0.0,
) -> str:
    """Short deterministic explanation for prioritization."""
    if status == "New":
        return "New failure pattern that may indicate a regression."
    if status == "Flaky":
        return "Intermittent failure reducing CI reliability."
    if status == "Recurring":
        if flake_rate >= 0.5:
            return "Most common failure cluster in recent runs."
        return "Repeated failure signal worth triaging before lower-risk noise."
    return "Failure signal detected in recent CI runs."


def compute_overview_metrics(
    runs: list[dict[str, Any]],
    failure_groups: dict[str, Any],
    flaky_tests: dict[str, Any],
) -> dict[str, int]:
    """Compute batch-level overview counts from parsed runs."""
    total_tests: set[str] = set()
    failures = 0

    for run in runs:
        for case in run.get("cases", []):
            test_id = case.get("test_id")
            if test_id:
                total_tests.add(test_id)
            if case.get("status") in ("failed", "error"):
                failures += 1

    return {
        "total_tests": len(total_tests),
        "failures": failures,
        "flaky_tests": len(flaky_tests),
        "failure_groups": len(failure_groups),
    }


def suggested_next_steps(items: list[dict[str, Any]]) -> list[str]:
    """Return up to three deterministic recommendation bullets."""
    steps: list[str] = []
    seen: set[str] = set()

    for item in items:
        combined = " ".join(
            str(item.get(key, "") or "")
            for key in ("title", "message", "fingerprint", "test_id")
        ).lower()

        if "timeout" in combined and "timeout" not in seen:
            steps.append("Investigate service availability and retry behavior")
            seen.add("timeout")
        elif (
            "race" in combined or "async" in combined or "synchron" in combined
        ) and "race" not in seen:
            steps.append("Review async synchronization and timing dependencies")
            seen.add("race")
        elif ("assert" in combined or "assertion" in combined) and "assert" not in seen:
            steps.append("Review recent behavioral changes in affected tests")
            seen.add("assert")
        elif any(
            token in combined
            for token in ("connection", "econnrefused", "dependency", "refused")
        ) and "connection" not in seen:
            steps.append("Verify dependency health and network connectivity")
            seen.add("connection")

        if len(steps) >= 3:
            break

    return steps[:3]


def build_fix_first_item(
    fp: str,
    info: dict[str, Any],
    group: dict[str, Any],
    *,
    flaky_tests: dict[str, Any],
    total_runs: int,
) -> dict[str, Any]:
    """Build a normalized Fix First record for markdown/PR rendering."""
    examples = group.get("examples", []) if isinstance(group, dict) else []
    test_id = examples[0].get("test_id") if examples else None
    message = examples[0].get("message") if examples else None
    seen_runs = len({ex.get("run_id") for ex in examples if ex.get("run_id")})
    group_count = int(group.get("count", 0)) if isinstance(group, dict) else 0

    reasons = info.get("reasons", {}) if isinstance(info, dict) else {}
    is_novel = bool(reasons.get("novel", False))
    flake_rate = float(reasons.get("flake_rate", 0.0))

    is_flaky_related = False
    for ex in examples:
        tid = ex.get("test_id")
        if tid and tid in flaky_tests:
            is_flaky_related = True
            break

    status = failure_status(
        is_novel=is_novel,
        is_flaky_related=is_flaky_related,
        group_count=group_count,
        seen_runs=seen_runs,
    )

    tier = info.get("risk_tier", "UNKNOWN") if isinstance(info, dict) else "UNKNOWN"
    score = float(info.get("risk_score", 0.0)) if isinstance(info, dict) else None

    return {
        "fingerprint": fp,
        "title": human_title(message=message, test_id=test_id, fingerprint=fp),
        "test_id": test_id,
        "message": message,
        "status": status,
        "risk_tier": tier,
        "risk_score": score,
        "seen_runs": seen_runs,
        "total_runs": total_runs,
        "why": why_this_matters_text(status, flake_rate=flake_rate),
        "preview": message,
    }


def build_fix_first_list(
    failure_groups: dict[str, Any],
    risk_assessment: dict[str, Any],
    flaky_tests: dict[str, Any],
    total_runs: int,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Build prioritized Fix First items from risk output or failure groups."""
    items: list[dict[str, Any]] = []

    if risk_assessment:
        risk_sorted = sorted(
            risk_assessment.items(),
            key=lambda kv: (-float(kv[1].get("risk_score", 0.0)), kv[0]),
        )
        for fp, info in risk_sorted[:limit]:
            group = failure_groups.get(fp, {})
            items.append(
                build_fix_first_item(
                    fp,
                    info,
                    group,
                    flaky_tests=flaky_tests,
                    total_runs=total_runs,
                )
            )
        return items

    sorted_groups = sorted(
        failure_groups.items(),
        key=lambda kv: (-kv[1].get("count", 0), kv[0]),
    )
    for fp, group in sorted_groups[:limit]:
        items.append(
            build_fix_first_item(
                fp,
                {},
                group,
                flaky_tests=flaky_tests,
                total_runs=total_runs,
            )
        )
    return items


def _humanize_test_id(test_id: str) -> str:
    name = test_id.split("::")[-1] if "::" in test_id else test_id
    name = re.sub(r"[_\-]+", " ", name).strip()
    if not name:
        return test_id
    return name[0].upper() + name[1:]


def _first_meaningful_clause(message: str) -> str:
    cleaned = re.sub(r"\s+", " ", message.replace("\n", " ")).strip()
    for sep in (":", "—", "-"):
        if sep in cleaned:
            part = cleaned.split(sep, 1)[-1].strip()
            if part:
                cleaned = part
                break
    return _compact_text(cleaned, max_chars=72)


def _compact_text(text: str, max_chars: int = 120) -> str:
    cleaned = re.sub(r"\s+", " ", text.replace("\n", " ")).strip()
    if len(cleaned) <= max_chars:
        return cleaned
    cut = cleaned[: max_chars - 1]
    split_at = cut.rfind(" ")
    if split_at > max_chars // 2:
        cut = cut[:split_at]
    return cut.rstrip(" .,;:") + "..."
