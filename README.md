# FlakeShield

**Detect flaky tests, reduce CI noise, and know what to fix first.**

FlakeShield turns repeated JUnit runs into a concise CI triage signal:

- groups repeated failures into stable fingerprints
- highlights flaky tests separately from deterministic failures
- generates a compact GitHub-friendly summary
- prioritizes fixable issues, not noisy traces

FlakeShield is built for teams that want faster CI review without dashboards or SaaS.

## Fast install

Use the official GitHub Action for `v0.5.1`:

```yaml
uses: deeoli/flakeshield-scratch@v0.5.1
with:
  reports: "outputs/junit_run*.xml"
  out_prefix: outputs/flake_report
  db_path: outputs/flakeshield.db
  enable_semantic: "true"
  warn_on_high: "true"
  fail_on_critical: "false"
```

This is the recommended integration path for external developer adoption.

## Quickstart

A minimal GitHub Actions job looks like this:

```yaml
name: FlakeShield CI

on:
  pull_request:
  workflow_dispatch:

jobs:
  flakeshield:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -e .

      - name: Run tests to produce JUnit XML
        run: |
          pytest --junitxml=outputs/junit_run1.xml || true
          pytest --junitxml=outputs/junit_run2.xml || true

      - name: Run FlakeShield
        uses: deeoli/flakeshield-scratch@v0.5.1
        with:
          reports: "outputs/junit_run*.xml"
          out_prefix: outputs/flake_report
          db_path: outputs/flakeshield.db
          enable_semantic: "true"
          warn_on_high: "true"
          fail_on_critical: "false"
```

## Why FlakeShield

FlakeShield helps teams move faster by converting noisy CI output into action:

- **Reduce noise:** separate flaky tests from real failures
- **Fix first:** prioritize issues that matter most
- **Stable signal:** group failures by deterministic fingerprint
- **CI-friendly:** designed for GitHub Actions and PR workflows
- **No SaaS required:** everything runs inside your repo

## What you get

When FlakeShield runs, it writes:

- `outputs/flake_report.json` — structured report for automation
- `outputs/flake_report.md` — readable summary for reviewers
- `outputs/flakeshield.db` — historic run state for flake detection
- `outputs/pr_comment.md` — PR comment source for GitHub merges

A good report is short and usable, not a giant trace dump.

## Recommended pattern

1. restore `outputs/flakeshield.db` from cache
2. run tests to produce JUnit XML
3. run FlakeShield against those XML files
4. upload or comment summary output

### Cache example

```yaml
- name: Restore FlakeShield DB cache
  uses: actions/cache@v4
  with:
    path: outputs/flakeshield.db
    key: flakeshield-db-${{ github.ref }}
    restore-keys: |
      flakeshield-db-${{ github.ref }}-

# run FlakeShield here

- name: Save FlakeShield DB cache
  if: always()
  uses: actions/cache@v4
  with:
    path: outputs/flakeshield.db
    key: flakeshield-db-${{ github.ref }}
```

## Recommended GitHub workflow

For a complete example, see `examples/canonical-workflow.yml`.

That workflow shows the best practice for:

- caching branch-specific state
- generating JUnit XML files
- running FlakeShield in CI
- producing PR-friendly markdown
- keeping the same comment updated over time

## PR comment output

FlakeShield is designed to support a compact GitHub PR summary that surfaces:

- flaky tests
- high-priority failures
- regressions
- novel issues

A typical PR summary looks like:

```markdown
### Flaky tests
- **tests/test_example.py::test_flaky** (runs=4, rate=0.50)

### Fix First
- **fp12345** — HIGH (0.82)
- **fp67890** — regression since run_456
```

## Notes for maintainers

- `outputs/flakeshield.db` stores historical failure state.
- the CLI is deterministic first; semantic mode is advisory.
- the action supports the same report format as the CLI.
- keep `reports` pointed at JUnit XML output from your test steps.

## License

MIT
