# FlakeShield

**Fast CI failure triage for teams that want signal, not noise.**

FlakeShield analyzes JUnit test results, labels flakiness, groups repeated failures, and surfaces the most important issues first. It is designed for developers who need a lightweight, reliable way to understand CI failures without adding dashboards or SaaS.

## 1. Install in 2 minutes

```bash
cd flakeshield-scratch
python -m pip install --upgrade pip
pip install -e .
```

If you want only the CLI and dependency isolation, install with:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

## 2. What it does

FlakeShield helps teams by:

- detecting flaky tests across repeated JUnit runs
- highlighting deterministic failures separately from noise
- storing history in SQLite so results improve over time
- optionally using semantic assistance to flag emerging risk
- generating both machine-readable and human-readable output

## 3. Minimal local CLI example

Run FlakeShield against JUnit XML files:

```bash
flakeshield --reports "examples/demo-repo/outputs/junit_run*.xml" \
           --out outputs/flake_report \
           --db outputs/flakeshield.db
```

This writes:

- `outputs/flake_report.json` — structured findings for scripts
- `outputs/flake_report.md` — quick human report
- `outputs/flakeshield.db` — historical test data

## 4. What output looks like

A typical human-readable report includes:

```markdown
### Flaky tests
- **tests/test_demo.py::test_flaky** (runs=2, rate=0.50)

### High risk failures
- **fingerprint:a1b2c3** (CRITICAL)

### Regressions
- fingerprint:d4e5f6 (since run_123)

### Novel failures
- fingerprint:abc123
```

The report is intentionally short and review-friendly.

## 5. Optional semantic mode

Semantic mode is an advisory layer that runs only when you opt in.

```bash
flakeshield --reports "examples/demo-repo/outputs/junit_run*.xml" \
           --out outputs/flake_report \
           --db outputs/flakeshield.db \
           --enable-semantic
```

Semantic mode adds:

- known vs novel failure detection
- top-k similarity suggestions
- advisory risk scores
- non-blocking ML assistance

It is **optional** and **safely degrades** if models or network are unavailable.

## 6. Why DB persistence matters

FlakeShield stores results in `outputs/flakeshield.db` so each workflow run learns from prior history.

That means:

- flaky tests are detected only after repeated runs
- risk scoring improves as the database grows
- failures are grouped across time, not just per run

### GitHub Actions cache pattern

Use a cache restore/save step around FlakeShield. Keep the cache scoped to the branch so history is preserved across runs:

```yaml
- name: Restore FlakeShield DB cache
  uses: actions/cache@v4
  with:
    path: outputs/flakeshield.db
    key: flakeshield-db-${{ github.ref }}
    restore-keys: |
      flakeshield-db-${{ github.ref }}-

# Run FlakeShield here

- name: Save FlakeShield DB cache
  if: always()
  uses: actions/cache@v4
  with:
    path: outputs/flakeshield.db
    key: flakeshield-db-${{ github.ref }}
```

## 7. Canonical GitHub workflow

See the recommended example at `examples/canonical-workflow.yml`.

It shows the clean flow:

1. restore DB cache
2. run tests twice with unique JUnit filenames
3. run FlakeShield
4. generate a PR summary markdown
5. post or update a PR comment
6. upload artifacts

## 8. Optional PR comments

FlakeShield can generate PR-ready markdown. The workflow example includes an idempotent commenter that updates the same comment on each run using a hidden marker.

### PR comment step

```yaml
- name: Post or update PR comment
  if: github.event_name == 'pull_request'
  uses: actions/github-script@v7
  with:
    script: |
      const fs = require('fs');
      const body = fs.readFileSync('outputs/pr_comment.md', 'utf8');
      const comments = await github.rest.issues.listComments({
        owner: context.repo.owner,
        repo: context.repo.repo,
        issue_number: context.issue.number,
      });
      const existing = comments.data.find(c =>
        c.body.includes('<!-- FlakeShield')
      );
      if (existing) {
        await github.rest.issues.updateComment({
          owner: context.repo.owner,
          repo: context.repo.repo,
          comment_id: existing.id,
          body,
        });
      } else {
        await github.rest.issues.createComment({
          owner: context.repo.owner,
          repo: context.repo.repo,
          issue_number: context.issue.number,
          body,
        });
      }
```

## 9. Example repo ready to run

Use `examples/demo-repo/` for a tiny runnable suite with a flaky test, a deterministic failure, and sample generated outputs.

```bash
cd examples/demo-repo
python -m pip install -r requirements.txt
mkdir -p outputs
pytest --junitxml=outputs/junit_run1_1.xml || true
DEMO_FLAKY=1 pytest --junitxml=outputs/junit_run2_1.xml || true
```

Then run FlakeShield:

```bash
cd ../..
flakeshield --reports "examples/demo-repo/outputs/junit_run*.xml" \
           --out examples/demo-repo/outputs/flake_report \
           --db examples/demo-repo/outputs/flakeshield.db \
           --enable-semantic
```

## 10. Useful commands

```bash
flakeshield --help
cat outputs/flake_report.json | python -m json.tool
pytest -q
```

## 11. Notes

- FlakeShield is intentionally focused on developer UX, not dashboards.
- The deterministic engine is the source of truth.
- Semantic mode is advisory and safe for CI.
- The `examples/canonical-workflow.yml` file is the recommended integration pattern.

---

## License

MIT
