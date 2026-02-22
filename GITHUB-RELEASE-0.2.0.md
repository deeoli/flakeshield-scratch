
---

# 📦 GitHub Release Notes Draft (v0.2.0)

Title:

FlakeShield v0.2.0 — Installable CI Risk Intelligence

Body:

---

## Overview

FlakeShield is a deterministic-first CI signal reduction engine with optional semantic intelligence.

Version 0.2.0 introduces packaging, CLI risk summaries, and a stabilized advisory risk layer.

---

## Highlights

* Installable CLI (`flakeshield`)
* Deterministic flake detection with confidence scoring
* Stateful persistence via SQLite
* Known vs novel failure detection
* Top-k historical similarity (semantic mode)
* Advisory risk scoring layer
* CLI high-risk summary
* Frozen JSON contract
* Fully non-blocking semantic layer
* 46 passing tests

---

## Design Principles

* Deterministic core is authoritative
* Semantic intelligence is optional and reversible
* CI safety guaranteed (semantic failures never block builds)
* JSON output contract is test-frozen

---

## Installation

```bash
pip install -e .
```

---

## Example

```bash
flakeshield --reports "examples/report*.xml" --out outputs/flake_report --enable-semantic
```

---

No breaking changes.
No CI behavior changes.

---

## After Release

