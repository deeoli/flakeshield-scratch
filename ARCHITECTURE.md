# FlakeShield — Architecture

**Purpose:** Reduce CI noise via deterministic, explainable post-test analysis.

**Current shape:** CLI-first, local-first, DB-backed, reproducible.

---

## 1. Product Shape: Now vs Next vs Later

### Evolution Path

```
PAST
  [JUnit XML parser]
       ↓
  [Fingerprint grouping]
       ↓
  [Flake detection]
       ↓
  [JSON report]

NOW (Today)
  [JUnit XML / CI]
       ↓
  [Deterministic core] ---- authoritative
       ↓
  [Semantic advisory layer] ---- optional, gated
       ↓
  [Risk scoring + tiers]
       ↓
  [Regression detection]
       ↓
  [Policy flags]
       ↓
  [CLI / JSON / PR summary / GitHub Action]

NEXT (3-6 months)
  [GitHub Action validated externally]
       ↓
  [Release + reusable adoption]
       ↓
  [Multi-repo history]
       ↓
  [Hosted ingestion]
       ↓
  [Dashboard + notifications]
       ↓
  [FlakeShield Plus platform]
```

**Mental Model:** FlakeShield today tells you **what is happening** in CI. FlakeShield next tells you **what matters most**. FlakeShield Plus later enforces **how CI should respond**.

---

## 2. Design Principles

- **Deterministic-first**: core engine is authoritative, repeatable, explainable
- **Semantic advisory**: ML-assisted features are optional, gated, non-blocking, never authoritative
- **CLI-first**: local execution, CI-friendly, composable with existing workflows
- **DB-backed**: SQLite as source of truth; reports are derived views
- **Explainable**: all decisions traceable to underlying data and rules
- **CI-safe**: failures in semantic layer do not block pipelines
- **No schema magic**: contract frozen; extensions only via new tables or computed fields

---

## 3. Current Architecture (Shipped)

### 2.1 Ingestion Pipeline

```
(CI job output / JUnit XML files)
           ↓
    [CLI Entry: flakeshield]
           ↓
    [Report Discovery]
    - glob patterns for XML files
    - assign run_id per report
           ↓
    [JUnit XML Parser]
    - canonical schema (run_id, suite, test_id, status, message, traceback, duration)
    - validate and normalize events
           ↓
    [Canonical Events: List[TestCase]]
    - run_id, suite, test_id, status
    - duration_sec, failure_type
    - message, traceback (if failed/error)
```

### 2.2 Fingerprinting

```
    [Canonical Events]
           ↓
    [Fingerprint Builder]
    - normalize message/traceback
      (strip volatile tokens: IDs, paths, line numbers, timestamps)
    - produce stable hash string
    - deterministic and repeatable
           ↓
    [Fingerprinted Events]
    - added field: fingerprint (stable identifier)
```

### 2.3 Persistence & Analytics

```
    [Fingerprinted Events]
           ↓
    [SQLite Persistence: flakeshield.db]
    - idempotent inserts (UNIQUE constraints)
    - authoritative source of truth
           ↓
    [DB-only Analytics Layer]
    
    ├─ Flake Detection (multi-run)
    │  - pass/fail variance per test_id
    │  - flaky rates + stability confidence
    │  - run count thresholds
    │
    ├─ Failure Groups by fingerprint
    │  - deterministically group failed/error by fingerprint
    │  - counts + representative cases
    │
    ├─ Scoring + Confidence
    │  - explainable confidence metrics
    │  - deterministic scoring
    │
    ├─ Risk Analysis (deterministic)
    │  - risk scores for each fingerprint
    │  - deterministic ranking
    │
    └─ Regression Detection
       - compare fingerprints in latest vs previous run
       - identify newly-failing tests
```

### 2.4 Semantic Advisory Layer (Optional)

```
    [Fingerprinted Events + DB State]
           ↓
    [Semantic Grouping] (--enable-semantic flag)
    - embed failure text (message + traceback)
    - group by cosine similarity (default threshold 0.80)
    - known vs novel classification (relative to historical fingerprints)
    - top-k similar historical cases
           ↓
    [Semantic Enrichment]
    - advisory grouping (never replaces fingerprint groups)
    - fragmentation metrics
    - clearly labeled as assistive / non-authoritative
           
    NOTE: Optional, gated by flag, non-blocking on failure.
          Semantic logic does NOT create policy decisions alone.
```

### 2.5 Decision Intelligence Layer

```
    [Deterministic Core + Optional Semantic Enrichment]
           ↓
    [Risk Scoring]
    - per-fingerprint risk score (0.0 - 1.0)
    - combines flake rate, novelty, frequency
           ↓
    [Risk Tiers]
    - classify fingerprints: LOW / MEDIUM / HIGH / CRITICAL
    - tier threshold configuration (default: flake_rate, novelty, frequency)
           ↓
    [Regression Detection]
    - deterministic: compare latest run fingerprints vs previous run
    - identify failures that are new since the prior run
           ↓
    [Policy Evaluation]
    - warn-on-high: print warning if any fingerprint reaches HIGH/CRITICAL
    - fail-on-critical: exit nonzero if any CRITICAL fingerprint present
    - max-risk-threshold: exit nonzero if any risk_score >= threshold
    - all policy flags are boolean gates, not advisory
```

### 2.6 Report Generation

```
    [Analysis Results]
           ↓
    ├─ [JSON Report]
    │  - flaky_tests, failure_groups
    │  - risk_assessment, risk_analysis
    │  - regressions, novel_failures, known_failures
    │  - metrics: semantic_enabled, fragmentation_delta, etc.
    │  - outputs/flake_report.json
    │
    ├─ [Markdown Report]
    │  - human-readable summary
    │  - sections: flaky tests, failures, metrics
    │  - outputs/flake_report.md
    │
    ├─ [CLI High-Risk Summary]
    │  - printed to stdout
    │  - top failing fingerprints ranked by risk
    │
    ├─ [PR Summary Markdown]
    │  - compact summary (max ~30 lines)
    │  - sections: flaky, high-risk, regressions, novel
    │  - outputs/pr_comment.md
    │
    └─ [Exit Code / Policy Result]
       - policy flags determine exit code
       - semantic failures do not affect exit code
```

---

## 4. Current Data Model

### 3.1 Primary Table: `test_results`

| Column | Type | Notes |
|--------|------|-------|
| `run_id` | TEXT | unique identifier per test run |
| `test_id` | TEXT | FQDN or relative test name |
| `suite` | TEXT | optional suite/module name |
| `status` | TEXT | passed, failed, error, skipped |
| `message` | TEXT | failure message (nullable) |
| `traceback` | TEXT | full stack trace (nullable) |
| `fingerprint` | TEXT | normalized hash (nullable, only for failed/error) |
| `duration_sec` | REAL | execution time |
| `created_at` | TIMESTAMP | insertion timestamp |

**Uniqueness:** `UNIQUE(run_id, test_id)` ensures idempotent inserts.  
**Indexes:** `run_id`, `test_id`, `status`, `fingerprint` for query performance.

### 3.2 Reserved Table: `failure_embeddings`

| Column | Type | Notes |
|--------|------|-------|
| `fingerprint` | TEXT | failed test fingerprint |
| `model_name` | TEXT | e.g. "sentence-transformers/all-MiniLM-L6-v2" |
| `dim` | INTEGER | embedding dimension (e.g., 384) |
| `vector` | BLOB | embedding vector (binary serialized) |
| `created_at` | TIMESTAMP | insertion timestamp |

**Status:** Reserved for future use. Currently, embeddings are not persisted (computed in-memory only during semantic analysis).

### 3.3 Reports as Derived Artifacts

Reports are **not stored in the database**. They are generated on-demand from `test_results`:

- `flake_report.json` — machine-readable summary
- `flake_report.md` — human-readable summary
- `pr_comment.md` — PR-friendly digest
- CLI high-risk summary — stdout output

---

## 5. Product Flow

### Ingestion & Analysis Flow

```
JUnit XML → CLI / GitHub Action → Canonical Events → Fingerprinting → 
SQLite Persistence → Risk / Regression / Policy → Reports + PR Summary
```

### Policy Flow

```
Risk tiers → warn-on-high → fail-on-critical → max-risk-threshold
```

All policy flags are boolean gates (not advisory). Deterministic scores drive all policy decisions. Semantic layer never directly triggers policy.

### Distribution Flow

```
CLI → GitHub Action (Docker) → Future hosted platform
```

- **Local:** `flakeshield run --reports <pattern>` for any CI system
- **GitHub:** `uses: flakeshield/flakeshield-action@v0.4.0` with auto-PR comments
- **Docker:** Self-contained image; works in any containerized environment
- **Future:** Centralized ingestion API, multi-repo aggregation, team workflows

---

## 6. Current Output Surface

| Output | Status | Purpose |
|--------|--------|---------|
| CLI | Shipped | Local and CI command-line invocation |
| JSON report | Shipped | Machine-readable contract for downstream tooling |
| Markdown report | Shipped | Human-readable artifact for CI artifacts |
| CLI high-risk summary | Shipped | Immediate prioritization signal on stdout |
| PR summary markdown | Shipped | Review-friendly context in PR comments |
| GitHub Action (Docker-based) | Shipped | Drop-in CI integration; auto-posts PR comments |
| Config file (JSON) | Shipped | `.flakeshield.json` for defaults and settings |
| Simulation harness | Shipped | External validation tool for testing |
| Hosted API | Future | Centralized ingestion and team workflows |
| Web dashboard | Future | Trend and multi-repo visibility |

---

## 7. Operating Guarantees

### Deterministic Core (Authoritative)

- ✓ Fingerprinting is stable and repeatable
- ✓ Failure grouping is deterministic
- ✓ Flakiness detection is based on pass/fail variance
- ✓ Confidence scoring is explainable
- ✓ All outputs are reproducible given the same input

### Semantic Layer (Optional, Non-Blocking)

- ✓ Never required for core analysis
- ✓ Failures degrade gracefully (skip semantic, continue deterministic)
- ✓ Clearly labeled in reports as "advisory"
- ✓ Never affects policy decisions alone
- ✓ Can be toggled off via `--enable-semantic` flag

### Database as Source of Truth

- ✓ SQLite is the single source of truth
- ✓ Reports are views over DB state
- ✓ Idempotent inserts prevent duplication
- ✓ Schema is frozen; extensions only via new tables

### CI-Safety

- ✓ Semantic layer failures do not block pipelines
- ✓ Policy decisions are explicit (warn-on-high, fail-on-critical, max-risk-threshold)
- ✓ Default behavior is non-blocking unless policy flags set
- ✓ GitHub Action continues even if PR comment step fails

---

## 8. Architecture Diagram (Text)

```
                        ┌───────────────────────────────────────┐
                        │       INPUT LAYER                     │
                        │                                       │
                        │ CI / Local CLI / JUnit XML / API      │
                        └───────────────┬───────────────────────┘
                                        ▼
                    ┌───────────────────────────────────────────┐
                    │   DETERMINISTIC CORE (Authoritative)      │
                    │                                           │
                    │ • Parse JUnit XML                         │
                    │ • Fingerprint failures                    │
                    │ • Group by fingerprint                    │
                    │ • Detect flaky tests                      │
                    │ • Compute confidence                      │
                    └───────────────┬───────────────────────────┘
                                    │
                    ┌───────────────┴──────────────────────────┐
                    ▼                                           ▼
        ┌───────────────────────────────┐    ┌────────────────────────────────┐
        │   RISK ANALYSIS               │    │ SEMANTIC LAYER (Optional)      │
        │   (Deterministic)             │    │                                │
        │                               │    │ • Embed text                   │
        │ • Risk scoring                │    │ • Known vs novel               │
        │ • Risk tiers (LOW-CRITICAL)   │    │ • Similarity matching          │
        │ • Regression detection        │    │ • Semantic grouping            │
        │ • Policy evaluation           │    │                                │
        │ • (warn/fail/threshold)       │    │ NOTE: advisory only            │
        └───────────────┬───────────────┘    └──────────────┬─────────────────┘
                        │                                    │
                        └────────────────┬───────────────────┘
                                         ▼
                        ┌───────────────────────────────────┐
                        │   STATE LAYER (SQLite)            │
                        │                                   │
                        │ • test_results (authoritative)    │
                        │ • failure_embeddings (reserved)   │
                        │ • run history (canonical)         │
                        └───────────────┬───────────────────┘
                                        ▼
                        ┌───────────────────────────────────┐
                        │    OUTPUT LAYER (Derived)         │
                        │                                   │
                        │ • JSON report                     │
                        │ • Markdown report                 │
                        │ • PR comment summary              │
                        │ • CLI high-risk summary           │
                        │ • Exit codes (policy driven)      │
                        └───────────────┬───────────────────┘
                                        ▼
                        ┌───────────────────────────────────┐
                        │   DISTRIBUTION LAYER              │
                        │                                   │
                        │ • GitHub Action (Docker)          │
                        │ • GitHub PR comments              │
                        │ • Markdown/JSON artifacts         │
                        └───────────────────────────────────┘
```

---

## 9. Near-Term Evolution

### GitHub Action Validation (Now)

- External test repos confirm action runs correctly
- Artifact upload validated in real workflows
- PR comment posting tested end-to-end

### Release & Adoption (Next)

- Tag v0.4.0 and publish to GitHub Marketplace
- Create example repos demonstrating integration
- Document first-use experience

### Multi-Run Trend Intelligence (2–4 weeks)

- Extend analytics: flake rate over time per test_id
- Top noisy fingerprints (sorted by frequency + stability)
- "New failure groups since last N runs"
- Allowlist / ignore rules via config file

### Policy Engine Maturity (2–4 weeks)

- Refine risk tier thresholds via real-world usage
- Add team/org-level policy defaults (config inheritance)
- Support conditional policies (e.g., fail only on certain branches)

---

## 10. Future Product Surface (FlakeShield Plus)

### Hosted Ingestion (3–6 months)

- Centralized API endpoint for JUnit uploads
- Multi-repo history aggregation
- Team workspaces and access control
- Database: migration from SQLite to Postgres

### Dashboard & Visibility (4–8 months)

- Web UI for trend analysis
- Multi-repo CI health view
- Risk distribution across teams
- Historical failure timelines
- Search and filter across runs

### Notifications & Workflows (4–8 months)

- Slack integration for high-risk alerts
- Email weekly health reports
- GitHub PR check status integration
- Auto-linking to bug tracking systems

### FlakeShield Plus Platform (6–12 months)

```
┌─────────────────────────────────────────────────────────────┐
│             FlakeShield Plus                                │
│         CI Reliability + QA Intelligence Platform           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [Org Dashboard]                                            │
│  - Multi-repo CI health                                     │
│  - Risk trends across teams                                 │
│  - Top flaky / novel / critical failures                    │
│                                                             │
│  [Team Settings]                                            │
│  - Policy governance (org-wide warn/fail rules)             │
│  - Alerting preferences                                     │
│  - Slack/email channels                                     │
│                                                             │
│  [Analytics & Reporting]                                    │
│  - Historical trends (30/60/90 day)                         │
│  - Failure growth / decline tracking                        │
│  - Team performance metrics                                 │
│                                                             │
│  [Integration Ecosystem]                                    │
│  - GitHub / GitLab / Bitbucket                              │
│  - Slack, Jira, PagerDuty                                   │
│  - Custom webhooks                                          │
│                                                             │
│  [Governance & Compliance]                                  │
│  - Audit logs                                               │
│  - Role-based access control                                │
│  - Enterprise SSO                                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 11. Product Roadmap Layers

### Layer 1: Engine (Shipped)
Deterministic grouping, flaky detection, semantic assist, scoring, policy, regression detection. JSON contract frozen.

### Layer 2: Product (Shipped)
Packaging, config layer, policy flags, PR summary markdown, GitHub Action wrapper, Docker runtime.

### Layer 3: Runtime Validation (Now)
External repo testing, artifact upload, PR comment integration, action hardening, release v0.4.0+.

### Layer 4: Distribution & Adoption (Next)
GitHub Marketplace publication, example repos, first external installs, usage feedback loop.

### Layer 5: Hosted Platform (3–6 months)
API ingestion, multi-repo aggregation, trends, dashboard, notifications, team settings, Postgres migration.

### Layer 6: FlakeShield Plus (6–12 months)
Organization governance, compliance features, integrations, SaaS revenue, team plans, enterprise features.

---

## 12. What We Explicitly Do Not Build (Yet)

- ❌ UI / dashboards (until Layer 5+)
- ❌ Orchestration / auto-quarantine / auto-reruns
- ❌ Model training / fine-tuning
- ❌ RAG / LLM explanations (until MVP value proven + data exists)
- ❌ Test generation / smart selection workflows
- ❌ Enterprise single-sign-on (Layer 6 only)

---

## 13. Decision Framework

**When adding a feature:**

1. Is it deterministic-first, or does it ship as optional/advisory only?
2. Does it fit the current product surface (CLI, JSON, MD, Action)?
3. Does it require schema changes? (parked until post-MVP)
4. Does it block pipelines? (only if explicitly policy-gated)
5. Can it be tested without external services?

**When considering a database change:**

- Is it a new table (safe) or a schema change to existing table (parked)?
- Does it preserve idempotent insert guarantees?
- Is migration path clear?

**When considering hosted mode:**

- Is the feature currently production-ready in single-repo mode?
- Is the multi-repo implication understood?
- What is the data residency / compliance requirement?

---

## 14. Current Repository Structure

```
flakeshield/
  ├── cli.py                  # CLI entrypoint, report generation
  ├── parse_junit.py          # JUnit XML parsing
  ├── fingerprint.py          # Deterministic fingerprinting
  ├── db_queries.py           # DB analytics (flaky, groups, etc.)
  ├── storage.py              # SQLite persistence
  ├── risk_scoring.py         # Deterministic risk analysis
  ├── policy.py               # Policy tiers and evaluation
  ├── regressions.py          # Regression detection
  ├── pr_summary.py           # PR-ready markdown generation
  ├── config.py               # Config file loading
  ├── detect_flakes.py        # Semantic flake detection
  ├── embeddings.py           # Semantic embeddings (lazy)
  ├── known_novel.py          # Semantic known/novel
  ├── similarity.py           # Semantic similarity lookup
  └── semantic_grouping.py    # Semantic grouping logic

tests/
  ├── test_*.py               # Comprehensive test suite (62+ tests)
  
.github/workflows/
  ├── flakeshield.yml         # CI workflow (runs tests, runs FlakeShield)

tools/simulation/
  ├── run_simulation.py       # External validation harness

action.yml                     # GitHub Action entry point
Dockerfile                     # Docker image for GitHub Action
entrypoint.sh                  # Docker entrypoint script

.flakeshield.json             # Example config file
pyproject.toml                # Package metadata, dependencies
requirements.txt              # Runtime dependencies
README.md                      # User documentation
ARCHITECTURE.md               # This document
```
