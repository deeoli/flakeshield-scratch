
---

# 📦 GitHub Release Notes Draft (v0.4.0)

Title:

FlakeShield v0.4.0 — Validated CI Intelligence with Policy Enforcement

Body:

---

## Overview

FlakeShield is a deterministic-first CI signal reduction engine with optional semantic intelligence.

Version 0.4.0 introduces Docker-based GitHub Action, policy flags for CI enforcement, regression detection, and external runtime validation.

---

## Highlights

* Docker-based GitHub Action (externally validated)
* Policy flags: `warn_on_high`, `fail_on_critical`, `max-risk-threshold`
* Regression detection (latest vs previous run)
* PR summary generation and auto-commenting
* Risk tier classification (LOW/MEDIUM/HIGH/CRITICAL)
* Config file support
* Simulation harness for testing
* 62 passing tests
* Frozen JSON contract

---

## Design Principles

* Deterministic core is authoritative
* Semantic intelligence is optional and reversible
* Policy flags can block CI when enabled
* External runtime validation completed
* CI safety guaranteed

---

## Installation

```bash
pip install -e .
```

---

## GitHub Action Example

```yaml
- uses: flakeshield/action@v0.4.0
  with:
    reports: "outputs/junit.xml"
    enable_semantic: "true"
    warn_on_high: "true"
    fail_on_critical: "true"
    max-risk-threshold: "0.80"
```

---

## Breaking Changes

None.

## After Release

## After Release

