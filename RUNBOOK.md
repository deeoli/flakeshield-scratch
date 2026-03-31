# FlakeShield Runbook (local)

## Setup

### Windows + Git Bash

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -U pip
pip install -r requirements.txt
```

## Quick Start

### Deterministic Mode (Default)

Analyze test failures using fingerprinting (no ML):

```bash
python -m flakeshield.cli --reports "examples/report*.xml" --out outputs/flake_report --db outputs/flakeshield.db
```

This will:
1. Parse JUnit XML files (glob pattern)
2. Persist results to SQLite DB (`outputs/flakeshield.db`)
3. Generate deterministic reports:
   - `outputs/flake_report.json` (machine-readable)
   - `outputs/flake_report.md` (human-readable)

### Optional: Semantic Mode (ML-Assisted, Experimental)

Add semantic failure grouping via embeddings:

```bash
python -m flakeshield.cli --enable-semantic --reports "examples/report*.xml" --out outputs/flake_report --db outputs/flakeshield.db
```

When `--enable-semantic` is enabled:
- Fingerprint groups remain authoritative (primary)
- Semantic groups added as advisory view (clearly labeled "experimental")
- `metrics.semantic_enabled` set to `true`
- `metrics.fragmentation_delta` shows semantic improvement (if any)
- If embedding model download fails: CLI continues with deterministic results only (non-blocking)

### ⚠️ Semantic Mode Notes (Model Download & CI)

Semantic mode uses a local embedding model (via sentence-transformers).

First Run Behavior

On the first run with --enable-semantic, the embedding model may download from HuggingFace Hub:

- This can take a few seconds.
- A warning about unauthenticated requests may appear.
- This does not affect deterministic results.

Subsequent runs will use the cached model and be fast.

CI Usage

Semantic mode is now validated for CI use as an advisory layer:

- Works in GitHub Actions Docker environment
- Failures are non-blocking (degrade to deterministic-only)
- HF Hub unauthenticated warning is acceptable
- `embeddings.position_ids` unexpected load note is normal
- Use `enable_semantic: "true"` in GitHub Action inputs

Semantic failures (model load errors, network issues, etc.) are:

- Non-blocking
- Automatically downgraded to deterministic-only mode
- Reported with `metrics.semantic_enabled = false`


## GitHub Action Runtime Validation

### Step 1: Local Action Testing

Test the Docker action locally before CI deployment:

```bash
# Build the action image
docker build -t flakeshield-action .

# Test with sample data
docker run --rm -v $(pwd):/workspace \
  -e INPUT_REPORTS="examples/report*.xml" \
  -e INPUT_ENABLE_SEMANTIC="true" \
  -e INPUT_WARN_ON_HIGH="true" \
  flakeshield-action
```

### Step 2: Workflow Integration

Add to `.github/workflows/ci.yml`:

```yaml
- name: Run tests
  run: pytest --junitxml=outputs/junit.xml

- uses: ./  # or your published action
  with:
    reports: "outputs/junit.xml"
    enable_semantic: "true"
    warn_on_high: "true"
    fail_on_critical: "true"
    max-risk-threshold: "0.80"
```

### Step 3: Policy Flag Testing

Test blocking behavior:

```yaml
# Warning mode (non-blocking)
- uses: ./ 
  with:
    reports: "outputs/junit.xml"
    enable_semantic: "true"
    warn_on_high: "true"

# Blocking mode
- uses: ./
  with:
    reports: "outputs/junit.xml"
    enable_semantic: "true"
    max-risk-threshold: "0.80"  # Fails CI if any score >= 0.80
```

### Troubleshooting

**HF Hub unauthenticated warning:**
- Expected and non-fatal
- Model downloads work without authentication
- No action needed

**embeddings.position_ids unexpected load note:**
- Normal for this model architecture
- Does not affect functionality
- Safe to ignore

**Semantic layer failures:**
- Automatically degrades to deterministic-only
- CI continues running
- Check `metrics.semantic_enabled` in report

**Policy enforcement not working:**
- Ensure `enable_semantic: "true"` is set
- Policy flags only work with semantic mode enabled
- Check that `max-risk-threshold` input is a string (e.g., "0.80")

### Step 1: Run Deterministic Command

```bash
python -m flakeshield.cli --reports "examples/report*.xml" --out outputs/flake_report --db outputs/flakeshield.db
```

### Step 2: Confirm Output Files

```bash
ls -lh outputs/
# Should show:
# - flake_report.json
# - flake_report.md
# - flakeshield.db
```

### Step 3: Verify Database Schema

```python
import sqlite3

conn = sqlite3.connect('outputs/flakeshield.db')
cur = conn.cursor()

# List all tables
tables = cur.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall()

print("Tables in database:")
for table in tables:
    print(f"  - {table[0]}")

# Should output:
#   - failure_embeddings
#   - test_results

# Inspect test_results (required)
test_count = cur.execute("SELECT COUNT(*) FROM test_results").fetchone()[0]
print(f"\ntest_results rows: {test_count}")

# Inspect failure_embeddings (Week 4, reserved for future use)
embedding_count = cur.execute("SELECT COUNT(*) FROM failure_embeddings").fetchone()[0]
print(f"failure_embeddings rows: {embedding_count}")

conn.close()
```

### Step 4: Inspect JSON Report

```bash
# Linux/Mac:
cat outputs/flake_report.json | jq '.metrics'

# Windows PowerShell:
Get-Content outputs/flake_report.json | ConvertFrom-Json | Select-Object metrics
```

Expected output:
```json
{
  "semantic_enabled": false,
  "fingerprint_group_count": N,
  "semantic_group_count": null,
  "fragmentation_delta": null
}
```

If semantic enabled, expect:
```json
{
  "semantic_enabled": true,
  "fingerprint_group_count": N,
  "semantic_group_count": M,
  "fragmentation_delta": N - M
}
```

Extended semantic-enabled JSON (includes similarity + risk metadata):
```json
{
  "semantic_enabled": true,
  "fingerprint_group_count": N,
  "semantic_group_count": M,
  "fragmentation_delta": N - M,
  "risk_analysis": { "<fingerprint>": { "risk_score": 0.12, "components": { "flake_rate": 0.5, "novelty": 0.0, "similarity": 0.1 } } },
  "novel_failure_matches": { "<novel_fp>": [ { "fingerprint": "<hist_fp>", "score": 0.82 }, ... ] }
}
```

Short descriptions:
- `novel_failure_matches`: Top-k historical similar fingerprints (advisory)
- `risk_analysis`: Derived risk score per fingerprint (advisory, non-authoritative)

Why This Matters

Your system is now:

- Deterministic-first
- ML-assisted
- Non-blocking
- JSON-contract frozen
- CI-safe

The RUNBOOK reflects that maturity: semantic outputs are advisory and CI-friendly.

## Common Commands

### Testing

```bash
# Run all tests (41 passing)
python -m pytest tests/ -q

# Run all tests with verbose output
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_risk_scoring.py -v
python -m pytest tests/test_semantic_json_contract.py -v

# Run tests with coverage report
python -m pytest tests/ --cov=flakeshield --cov-report=term-missing

# Run single test
python -m pytest tests/test_risk_scoring.py::test_high_risk_novel_flaky_similar -v

# Run tests matching pattern
python -m pytest tests/ -k "risk_scoring" -v

# Golden contract tests only (JSON structure validation)
python -m pytest tests/test_semantic_json_contract.py -v
```

### CLI Usage

```bash
# Deterministic mode (default, no semantic)
python -m flakeshield.cli --reports "examples/report*.xml" --out outputs/flake_report

# With semantic analysis enabled (advisory layer)
python -m flakeshield.cli --reports "examples/report*.xml" --out outputs/flake_report --enable-semantic

# Custom database path
python -m flakeshield.cli --reports "examples/report*.xml" --out outputs/flake_report --db /tmp/custom.db --enable-semantic

# View generated report
cat outputs/flake_report.json | python -m json.tool

# Check report metrics (bash)
cat outputs/flake_report.json | jq '.metrics'

# Check report metrics (PowerShell)
Get-Content outputs/flake_report.json | ConvertFrom-Json | Select-Object metrics
```

### Development Workflow

```bash
# 1. Run all tests
python -m pytest tests/ -q

# 2. Run CLI on example reports
python -m flakeshield.cli --reports "examples/report*.xml" --out outputs/flake_report --enable-semantic

# 3. Inspect generated JSON report
cat outputs/flake_report.json | python -m json.tool

# 4. View markdown report
cat outputs/flake_report.md
```

```
usage: flakeshield [-h] [--reports REPORTS] [--out OUT] [--db DB] [--enable-semantic]

options:
  --reports REPORTS         Glob pattern for JUnit XML files (default: report*.xml)
  --out OUT                 Output prefix for JSON + Markdown reports (default: flake_report)
  --db DB                   SQLite database path (default: outputs/flakeshield.db)
  --enable-semantic         Enable ML-assisted semantic failure grouping (default: off, non-blocking)
```
