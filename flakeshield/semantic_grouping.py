"""
Semantic failure grouping (v0.1)

Goal:
Group failures by semantic similarity using embeddings.

Rules:
- Runs in parallel with string fingerprints (do not replace)
- Deterministic thresholding
- No training, no ML "decisions" beyond similarity + threshold
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from flakeshield.embeddings import embed_texts, make_failure_text


def _cosine(a: List[float], b: List[float]) -> float:
    # embeddings are normalized, so dot product == cosine similarity
    return sum(x * y for x, y in zip(a, b))


def semantic_groups_from_cases(
    cases: List[Dict[str, Any]],
    threshold: float = 0.80,
    max_examples: int = 5,
) -> List[Dict[str, Any]]:
    """
    Input: list of testcase dicts (from your canonical schema) for FAILED/ERROR cases only.

    Output: list of groups:
      [
        {
          "group_id": 1,
          "size": int,
          "representative": {"test_id","run_id","message"},
          "members": [... up to max_examples ...]
        },
        ...
      ]

    Clustering method:
    - Greedy single-link: each new item joins first group whose representative is similar enough.
    - Simple, explainable baseline. Good enough to validate value.
    """
    texts: List[str] = []
    rows: List[Dict[str, Any]] = []

    for c in cases:
        t = make_failure_text(c.get("message"), c.get("traceback"))
        if t is None:
            continue
        texts.append(t)
        rows.append(c)

    if not rows:
        return []

    vecs = embed_texts(texts)

    groups: List[Dict[str, Any]] = []

    for row, vec in zip(rows, vecs):
        placed = False

        for g in groups:
            rep_vec = g["_rep_vec"]
            if _cosine(vec, rep_vec) >= threshold:
                g["_members"].append((row, vec))
                placed = True
                break

        if not placed:
            groups.append(
                {
                    "_rep_vec": vec,
                    "_members": [(row, vec)],
                }
            )

    # Convert internal format to report-friendly groups
    out: List[Dict[str, Any]] = []
    for i, g in enumerate(
        sorted(groups, key=lambda x: len(x["_members"]), reverse=True), start=1
    ):
        members = g["_members"]
        rep_row, _ = members[0]

        out.append(
            {
                "group_id": i,
                "size": len(members),
                "representative": {
                    "test_id": rep_row.get("test_id"),
                    "run_id": rep_row.get("run_id"),
                    "message": rep_row.get("message"),
                },
                "members": [
                    {
                        "test_id": r.get("test_id"),
                        "run_id": r.get("run_id"),
                        "message": r.get("message"),
                    }
                    for (r, _) in members[:max_examples]
                ],
            }
        )

    return out
