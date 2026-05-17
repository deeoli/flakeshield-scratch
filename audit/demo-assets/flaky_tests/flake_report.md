# FlakeShield Report

- Runs considered: **4**

## 📊 Summary
- 0 failure groups
- 2 flaky tests
- 0 high-risk failures

## ⚠️ Flaky Tests

Detected after accumulating historical data across runs. Confidence thresholds met.

| Test ID | Flake Rate | Runs | Passes | Fails | Confidence |
|---|---:|---:|---:|---:|---|
| `integration::test_auth_flow` | 60% | 5 | 2 | 3 | High |
| `integration::test_db_migration` | 50% | 4 | 2 | 2 | Medium |

## 🧭 What This Means

Your CI has **recurring flakiness** in authentication and database migration flows.

**Recommendation:** These tests are failing intermittently — not deterministic bugs, but environment/timing sensitivity. Investigate:

- `test_auth_flow` — timing-dependent mocks? Race condition in setup?
- `test_db_migration` — state pollution between runs? Concurrent table access?

## 📊 Failure Group Details

### Group 1 — 3 occurrences
- Fingerprint: `timeout: auth service took > 5000ms`
- Examples:
  - `run_100` — **integration::test_auth_flow** — TimeoutError: auth service took > 5000ms
  - `run_102` — **integration::test_auth_flow** — TimeoutError: auth service took > 5000ms
  - `run_104` — **integration::test_auth_flow** — TimeoutError: auth service took > 5000ms

### Group 2 — 2 occurrences
- Fingerprint: `deadlockdetectederror: mysql deadlock`
- Examples:
  - `run_101` — **integration::test_db_migration** — mysql.connector.errors.DatabaseError: 1213 (40001): Deadlock found when trying to get lock
  - `run_103` — **integration::test_db_migration** — mysql.connector.errors.DatabaseError: 1213 (40001): Deadlock found when trying to get lock

## Runs included
- `run_100.xml`
- `run_101.xml`
- `run_102.xml`
- `run_103.xml`

