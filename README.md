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

## GitHub Actions

Drop the following file in your repository at
`.github/workflows/flakeshield.yml` to get an automatic triage run on
every pull request.  It installs the package, runs your tests with
JUnit output, executes FlakeShield deterministically (and semantically
as an optional, non‑blocking step) and uploads the generated report
artifacts.

```yaml
name: FlakeShield

on:
  pull_request:
  workflow_dispatch:

jobs:
  flakeshield:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -e .
      - name: Run tests
        run: |
          mkdir -p outputs
          pytest --junitxml=outputs/junit.xml
      - name: Run FlakeShield (deterministic)
        run: |
          flakeshield --reports "outputs/junit.xml" \
                     --out outputs/flake_report \
                     --db outputs/flakeshield.db
      - name: Run FlakeShield (semantic, non-blocking)
        run: |
          flakeshield --reports "outputs/junit.xml" \
                     --out outputs/flake_report \
                     --db outputs/flakeshield.db \
                     --enable-semantic
        continue-on-error: true
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: flakeshield-reports
          path: |
            outputs/flake_report.json
            outputs/flake_report.md
            outputs/flakeshield.db
```

---


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

Current version: **0.2.0**

---

## License

MIT

---

