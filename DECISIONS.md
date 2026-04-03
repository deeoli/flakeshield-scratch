# FlakeShield — Architectural & Product Decisions (Locked)

This document records **explicit, frozen decisions** made during development.
Its purpose is to prevent scope creep, hindsight rewrites, and accidental regressions.

If a behavior exists in the system and is not documented here, it is **not guaranteed**.

Each decision includes:
- Context
- Evidence (when applicable)
- Constraints (locked)
- Revisit criteria

---

## Decision: Canonical Ingestion & Minimal Schema (Week 1)

**Status:** Active  
**Date:** Week 1  
**Owner:** FlakeShield Core  
**Evidence:** Initial ingestion + DB schema

### Context

CI systems produce noisy, inconsistent outputs.
Before any intelligence can be applied, inputs must be deterministic and stable.

### Decision

FlakeShield ingests **Pytest JUnit XML only** and extracts a **canonical minimal schema**
per test case, per run.

The schema is frozen early and treated as a contract.

### Why

- Prevents downstream logic from compensating for messy inputs
- Mirrors ML best practice: define features before modeling
- Enables reproducible analysis across runs

### Constraints (Locked)

- No flexible / schema-less ingestion
- No auto-detection of test frameworks
- No enrichment during parsing
- Parsing must be boring, explicit, and deterministic

### Revisit Criteria

Only revisit if:
- A second test framework is added deliberately
- A new field is required for a proven signal (not speculation)

Until then, this decision is **frozen**.

---

## Decision: Deterministic Heuristics Before ML (Week 2)

**Status:** Active  
**Date:** Week 2  
**Owner:** FlakeShield Core  
**Evidence:** DB-only flake detection + fingerprint grouping

### Context

Flaky tests and repeated failures are well-defined reliability problems.
They can be detected with clear rules before introducing probabilistic systems.

### Decisions

1. **Flakiness Definition**
   - A test is flaky if it has **multiple terminal outcomes across runs**
   - Detection is rule-based, not probabilistic

2. **Failure Grouping**
   - Failures are grouped via normalized string fingerprints
   - Identical fingerprints = identical failure cause

3. **Persistence**
   - All analysis is DB-backed (SQLite)
   - Reports are views over persisted history, not filesystem state

4. **Confidence Thresholds**
   - A test is not called flaky until it has ≥ N runs
   - Confidence levels are explicit and explainable

### Why

- Establishes a trustworthy baseline
- Reduces false positives early
- Prevents ML from being blamed for solvable logic problems

### Constraints (Locked)

- Deterministic logic is authoritative
- ML must not replace heuristics without evidence
- Reports must reflect persisted state, not input artifacts
- CI decisions must remain explainable

### Revisit Criteria

Only revisit if:
- Deterministic rules fail on real datasets
- Heuristics become unmaintainable at scale

Until then, this decision is **frozen**.

---

## Decision: Semantic Failure Grouping (Week 3)

**Status:** Active (ML-assisted, gated)  
**Date:** Week 3  
**Owner:** FlakeShield Core  
**Evidence:** Controlled fragmentation test  
`outputs/flake_report.json` (report_run6)

### Context

Deterministic fingerprint-based failure grouping is the authoritative baseline.
We evaluated whether ML-based semantic embeddings could reduce fragmentation
(i.e., split representations of the same underlying failure).

### Evidence

A controlled fragmentation experiment was run with:
- Semantically identical failures
- Textually different failure messages

Measured results:
- fingerprint_group_count = 5
- semantic_group_count = 3
- fragmentation_delta = +2

This demonstrates reduced noise for human triage.

### Decision

Semantic failure grouping is **kept** as an **ML-assisted, non-authoritative signal**.

### Constraints (Locked)

- Deterministic fingerprint grouping remains the primary source of truth
- Semantic grouping is optional and reversible
- Semantic grouping must be clearly labeled as experimental / assistive
- No persistence of embeddings
- No threshold tuning at this stage
- No ML-based decisions that block CI

### Revisit Criteria

Revisit only if:
- Real-world datasets show incorrect merges or regressions
- Embeddings introduce maintenance or performance issues
- A new dataset justifies persistence or similarity tuning

Until then, this decision is **frozen**.

---

## Decision: Policy Flags Can Block CI (Week 4)

**Status:** Active  
**Date:** Week 4  
**Owner:** FlakeShield Core  
**Evidence:** External runtime validation complete, policy enforcement working

### Context

FlakeShield provides advisory risk intelligence. Teams may want to enforce quality gates based on risk scores.

### Decision

Policy flags (`warn_on_high`, `fail_on_critical`, `max-risk-threshold`) are allowed to block CI pipelines when enabled.

### Constraints (Locked)

- Policy flags only work when semantic mode is enabled
- Default behavior remains non-blocking
- Policy decisions are based on deterministic risk scoring
- External validation confirmed blocking behavior works correctly

### Revisit Criteria

Only revisit if:
- Policy flags cause false failures in production
- Teams report blocking behavior is too aggressive

Until then, this decision is **frozen**.

---

## Decision: External Runtime Validation Completed (Week 4)

**Status:** Active  
**Date:** Week 4  
**Owner:** FlakeShield Core  
**Evidence:** GitHub Action tested in external repository, all features working

### Context

Before shipping, the GitHub Action needed validation in real CI environments.

### Decision

External runtime validation is complete. The Docker-based GitHub Action is production-ready.

### Constraints (Locked)

- Action inputs work correctly
- Semantic mode works in CI containers
- Policy enforcement works end-to-end
- PR comment posting works
- Artifact uploads work

### Revisit Criteria

Only revisit if:
- New CI environments break the action
- Major changes to action inputs are needed

Until then, this decision is **frozen**.

---

## Decision: GitHub Action is First-Class Product Surface (Week 4)

**Status:** Active  
**Date:** Week 4  
**Owner:** FlakeShield Core  
**Evidence:** Action validated, documented, and ready for adoption

### Context

FlakeShield needs accessible CI integration beyond CLI-only usage.

### Decision

The Docker-based GitHub Action is a first-class product surface, equal to the CLI.

### Constraints (Locked)

- Action mirrors CLI functionality
- Action is documented in README
- Action supports all validated inputs
- Action behavior matches CLI behavior

### Revisit Criteria

Only revisit if:
- Action becomes unmaintainable
- Teams prefer different CI integrations

Until then, this decision is **frozen**.

---

## Decision Policy (Meta)

- Decisions are added **only after evidence**
- Decisions are never silently modified
- Removing a decision requires a **new decision entry**
- Code must conform to decisions, not the other way around
