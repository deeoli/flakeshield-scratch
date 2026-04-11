---

# FlakeShield

**Deterministic CI signal reduction with optional semantic intelligence.**

FlakeShield analyzes JUnit test results and turns CI failure noise into prioritized, actionable insight — without blocking your pipeline.

---

## What It Solves

Modern CI pipelines suffer from:

* Flaky tests masking real regressions
* Repeated “known” failures wasting triage time
* Poor prioritization of failures
* Fragmented error grouping

FlakeShield reduces noise and surfaces:

* Flaky tests (with confidence levels)
* Deterministic failure groups
* Known vs novel failures
* Top-k similar historical failures (semantic mode)
* Advisory risk scoring
* CLI high-risk summary

---

## Quick Start

### Installation

```bash
pip install -e .
```

---

## Deterministic Mode (Default)

Analyze test failures using fingerprinting only (no ML, no network):

```bash
flakeshield --reports "examples/report*.xml" --out outputs/flake_report --db outputs/flakeshield.db
```

This will:

1. Parse JUnit XML files
2. Persist results to SQLite
3. Generate:

   * `outputs/flake_report.json` (machine-readable)
   * `outputs/flake_report.md` (human-readable)

Deterministic mode is always authoritative.

---

## Optional: Semantic Mode (ML-Assisted, Non-Blocking)

Enable semantic grouping, similarity lookup, and advisory risk scoring:

```bash
flakeshield --reports "examples/report*.xml" --out outputs/flake_report --db outputs/flakeshield.db --enable-semantic
```

First run may download an embedding model (a few seconds).
Subsequent runs use cached model.

The semantic layer is:

* **Optional** — deterministic mode works without it
* **Advisory-only** — never authoritative
* **Non-blocking** — failures degrade gracefully
* **CI-safe** — semantic errors do not fail builds

When enabled, CLI also prints:

```
High Risk Failures:
1. <fingerprint> — 0.83
2. <fingerprint> — 0.71
```

---

## Commands

```bash
# Show help
flakeshield --help

# Deterministic run (no network/model required)
flakeshield --reports "examples/report*.xml" --out outputs/flake_report

# Semantic-enabled run
flakeshield --reports "examples/report*.xml" --out outputs/flake_report --enable-semantic

# Custom database path
flakeshield --reports "examples/report*.xml" --out outputs/flake_report --db /tmp/custom.db --enable-semantic

# Pretty-print JSON report
cat outputs/flake_report.json | python -m json.tool
```

---

## GitHub Action (Validated)

Use FlakeShield as a drop-in CI step with the Docker-based GitHub Action:

```yaml
name: FlakeShield

on:
  pull_request:
  workflow_dispatch:

jobs:
  flakecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: |
          mkdir -p outputs
          pytest --junitxml=outputs/junit.xml
      - uses: ./            # or flakeshield/action@v0.4.0
        with:
          reports: "outputs/junit.xml"
          enable_semantic: "true"        # optional
          warn_on_high: "true"           # optional
          fail_on_critical: "true"       # optional
          max-risk-threshold: "0.80"     # optional
```

**Behavior:**
- By default, FlakeShield is **non-blocking** and provides advisory output
- When policy flags are enabled (`warn_on_high`, `fail_on_critical`, `max-risk-threshold`), it can fail CI
- Generates artifacts: `outputs/flake_report.json`, `outputs/flake_report.md`, `outputs/flakeshield.db`
- On PRs, automatically posts/updates a comment with the report summary

**Inputs:**
- `reports` – glob for XMLs (required)
- `enable_semantic` – enable semantic mode (default: "false")
- `warn_on_high` – print warnings for HIGH/CRITICAL risks (default: "false")
- `fail_on_critical` – exit nonzero on CRITICAL risks (default: "false")
- `max-risk-threshold` – exit nonzero if any risk_score ≥ threshold (default: "")
- `out_prefix` – output path prefix (default: "outputs/flake_report")
- `db_path` – SQLite database path (default: "outputs/flakeshield.db")

---

## GitHub Action Example

See the complete example workflow at [examples/flakeshield-action-example.yml](examples/flakeshield-action-example.yml).

Quick start:

```yaml
- name: Run FlakeShield
  uses: deeoli/flakeshield-scratch@v0.4.0
  with:
    reports: "outputs/junit.xml"
    enable_semantic: "true"
```

---

## GitHub Actions: Database Persistence & Historical Detection

To accumulate flake history across workflow runs (required for `min_runs=4` detection threshold), configure cache and unique XML filenames:

### 1. Cache the Database

Add cache restore before FlakeShield runs, save after:

```yaml
jobs:
  flakeshield:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: |
          mkdir -p outputs
          pytest --junitxml=outputs/junit_run1_${{ github.run_id }}.xml || true
          pytest --junitxml=outputs/junit_run2_${{ github.run_id }}.xml || true

      - name: Restore FlakeShield DB cache
        uses: actions/cache@v4
        with:
          path: outputs/flakeshield.db
          key: flakeshield-db-${{ github.ref }}-${{ github.run_id }}
          restore-keys: |
            flakeshield-db-${{ github.ref }}-

      - name: Run FlakeShield
        uses: deeoli/flakeshield-scratch@v0.4.0
        with:
          reports: "outputs/junit_run*.xml"
          enable_semantic: "true"

      - name: Save FlakeShield DB cache
        if: always()
        uses: actions/cache/save@v4
        with:
          path: outputs/flakeshield.db
          key: flakeshield-db-${{ github.ref }}-${{ github.run_id }}
```

### 2. ⚠️ CRITICAL: Unique XML Filenames Per Run

**Each workflow run must generate unique XML filenames**, otherwise FlakeShield's database deduplication prevents history accumulation.

**❌ WRONG** (DB won't grow):
```yaml
pytest --junitxml=outputs/junit.xml
```

**✅ CORRECT** (DB accumulates):
```yaml
pytest --junitxml=outputs/junit_${{ github.run_id }}.xml
```

**Why:** `run_id` is derived from XML basename (e.g., `"junit_12345.xml"`). The database uses `UNIQUE(run_id, test_id)` to prevent duplicate test results within the same run. Static filenames create identical run_ids across runs, silently rejecting new history.

### 3. Verify Accumulation

Check DB growth between runs:

```bash
sqlite3 outputs/flakeshield.db "SELECT COUNT(*) FROM test_results;"
```

Each run should increase the count. First run: N rows. Second run: N + M rows (where M = new test observations).

### Branch-Aware Caching

The cache key strategy enables per-branch history:

- **main** → `flakeshield-db-refs/heads/main-*`
- **feature/foo** → `flakeshield-db-refs/heads/feature/foo-*`
- **PR** → `flakeshield-db-pull/123/merge-*`

Each branch accumulates independent history. Merging a feature branch to main starts with main's history, not feature's.

---

## Architecture


FlakeShield follows a strict layered design:

### Deterministic Core (Authoritative)

* Fingerprint normalization
* Failure grouping
* Flakiness detection
* Confidence scoring
* DB-backed analytics

### Semantic Layer (Advisory)

* Embedding persistence
* Known vs novel detection
* Top-k similarity matching
* Risk scoring
* CLI high-risk summary

The deterministic layer is always the source of truth.

---

## Development

Run tests:

```bash
pytest -q
```

Run with coverage:

```bash
pytest tests/ --cov=flakeshield --cov-report=term-missing
```

All semantic features are fully test-covered and CI-safe.

---

## Version

Current version: **0.4.0**

---

## License

MIT

---

