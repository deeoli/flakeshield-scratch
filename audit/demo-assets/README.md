# FlakeShield Demo Assets

This directory contains polished, production-ready examples of FlakeShield output for documentation, README, and onboarding purposes.

## Asset Descriptions

### 1. Healthy Run (`healthy_run/`)
**Use case:** Show what a healthy CI looks like

- `flake_report.md` — Full deterministic report (0 failures, 0 flaky tests)
- `flake_report.json` — JSON report format
- `junit_run1.xml`, `junit_run2.xml` — Input test reports

**When to use:** README intro, onboarding, "best case" visuals

**Key talking points:**
- "No noise detected across 2 runs"
- "Developers can focus on shipping, not triage"

---

### 2. Failure Heavy (`failure_heavy/`)
**Use case:** Show rich failure analysis and grouping

- `flake_report.md` — Full report with 5 failure groups
- `flake_report_pr_comment.md` — Compact PR comment version
- `flake_report.json` — JSON structure
- Database snapshots for persistence demo

**When to use:** Feature showcase, "Fix First" demo, README examples

**Key talking points:**
- "5 unique failure patterns detected"
- "Deterministic fingerprinting groups similar failures"
- "No min_runs threshold yet (early detection)"

---

### 3. Flaky Test Example (`flaky_tests/` - to be created)
**Use case:** Show flaky detection after multiple runs

**Expected contents:**
- 4 JUnit XML files (one per run)
- Report showing tests with 50-75% failure rate
- Confidence scoring
- Regression detection

**Key talking points:**
- "After 4 runs, test_auth_flow identified as 60% flaky"
- "Historical memory prevents false blame"

---

### 4. PR Comment Example (`pr_comment/` - reference)
**Use case:** Show GitHub integration

**Expected contents:**
- `pr_comment.md` — What appears in PR threads
- Visual explanation of update logic (no duplicates)
- Example showing idempotent behavior

**Key talking points:**
- "Updates single PR comment, never duplicates"
- "Developers see actionable summary immediately"

---

## Usage

### For README Screenshots
Reference `flake_report.md` files directly or link to rendered versions:
```markdown
[See example healthy run report](audit/demo-assets/healthy_run/flake_report.md)
[See example failure analysis report](audit/demo-assets/failure_heavy/flake_report.md)
```

### For Feature Demonstration
Use JSON files for API documentation:
```markdown
[Full JSON schema](audit/demo-assets/healthy_run/flake_report.json)
```

### For Contributor Onboarding
Point new contributors here:
> "Run these examples locally to understand output format:
> ```bash
> flakeshield --reports audit/demo-assets/failure_heavy/junit*.xml --out /tmp/demo
> ```"

---

## Maintenance

- Keep examples realistic and relatable
- Update when report format changes
- Add new examples for new features
- Version examples alongside releases

