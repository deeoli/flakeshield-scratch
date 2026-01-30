# FlakeShield – JUnit XML Ingestion Rules (v0.1)

This document defines the canonical parsing rules for Pytest JUnit XML.
These rules are a frozen contract for all downstream logic.

---

## Parsing Rules v0.1

### 1) run_id
- Source: derived
- Rule: use XML filename (e.g. `report.xml`)
- Rationale: stable per run; CI can override later

### 2) suite
- Source: `<testsuite @name>`
- Example: `pytest`

### 3) test_id
- Source: `<testcase @classname>` + `::` + `<testcase @name>`
- Example: `test_sample::test_always_fails`
- Rationale: stable across repeated runs

### 4) status
- Rule:
  - if `<failure>` exists → `failed`
  - else if `<error>` exists → `error`
  - else if `<skipped>` exists → `skipped`
  - else → `passed`

### 5) duration_sec
- Source: `<testcase @time>`
- Type: float (seconds)

### 6) message
- Source priority:
  1. `<failure @message>`
  2. `<error @message>`
  3. `<skipped @message>`
- Example: `assert 1 == 2`

### 7) traceback
- Source:
  - inner text of `<failure>` or `<error>`
  - inner text of `<skipped>` (optional)
- Stored raw (no normalization at ingestion)

### 8) failure_type
- Source: `<failure @type>` or `<error @type>`
- If missing → `null`

### 9) fingerprint
- Not parsed at ingestion
- Derived later from normalized message/traceback

---

## Notes

- Parsing must be deterministic.
- Missing optional fields must not fail ingestion.
- No ML or heuristics at this stage.
