# FlakeShield

**CI signal reduction tool**: Detect, group, and prioritize flaky test failures using fingerprinting and semantic analysis.

## Quick Start

### Installation

```bash
pip install -e .
```

### Deterministic Mode (Default)

Analyze test failures using fingerprinting (no ML required):

```bash
flakeshield --reports "examples/report*.xml" --out outputs/flake_report --db outputs/flakeshield.db
```

This will:
1. Parse JUnit XML files
2. Persist results to SQLite DB
3. Generate:
   - `outputs/flake_report.json` (machine-readable)
   - `outputs/flake_report.md` (human-readable)

### Optional: Semantic Mode (ML-Assisted)

Enable semantic failure grouping, similarity matching, and risk prioritization:

```bash
flakeshield --reports "examples/report*.xml" --out outputs/flake_report --db outputs/flakeshield.db --enable-semantic
```

**Note**: On first run with `--enable-semantic`, the embedding model may download from HuggingFace Hub (a few seconds). Subsequent runs use cached model. The semantic layer is:
- **Optional**: deterministic mode works without it
- **Advisory-only**: not authoritative
- **Non-blocking**: failures degrade gracefully to deterministic-only

## Commands

```bash
# Show help
flakeshield --help

# Deterministic run (no network/model required)
flakeshield --reports "examples/report*.xml" --out outputs/flake_report

# Semantic-enabled run (downloads model on first run)
flakeshield --reports "examples/report*.xml" --out outputs/flake_report --enable-semantic

# Custom database path
flakeshield --reports "examples/report*.xml" --out outputs/flake_report --db /tmp/custom.db --enable-semantic

# View generated report
cat outputs/flake_report.json | python -m json.tool
```

## Development

Run tests:

```bash
pytest -q
```

Run with coverage:

```bash
pytest tests/ --cov=flakeshield --cov-report=term-missing
```

## Architecture

- **Deterministic core**: Fingerprinting, flakiness detection, scoring (always authoritative)
- **Semantic layer**: Embeddings, similarity, risk assessment (advisory, optional, non-blocking)
- **Output**: JSON + Markdown reports with structured failure grouping

## License

MIT
