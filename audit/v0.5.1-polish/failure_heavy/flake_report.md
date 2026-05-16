# FlakeShield Report

- Runs considered: **3**

## 📊 Summary
- 5 failure groups
- 0 flaky tests
- 0 high-risk failures

## 🔥 Fix First
✅ No prioritized failure groups yet.
## 🔎 Failure Group Details
### Group 1 — 3 occurrences
- Fingerprint: `assert 1 == 2`
- Examples:
  - `report_run4.xml` — **test_sample::test_always_fails** — assert 1 == 2
  - `report_run5.xml` — **test_sample::test_always_fails** — assert 1 == 2
  - `report_run6.xml` — **test_sample::test_always_fails** — assert 1 == 2

### Group 2 — 3 occurrences
- Fingerprint: `assert false
 +  where false = choice([true, false])
 +    where choice = random.choice`
- Examples:
  - `report_run4.xml` — **test_sample::test_flaky** — assert False | + where False = choice([True, False]) | + where choice = random.choice
  - `report_run5.xml` — **test_sample::test_flaky** — assert False | + where False = choice([True, False]) | + where choice = random.choice
  - `report_run6.xml` — **test_sample::test_flaky** — assert False | + where False = choice([True, False]) | + where choice = random.choice

### Group 3 — 1 occurrences
- Fingerprint: `assertionerror: error user missing for id=999
assert false`
- Examples:
  - `report_run6.xml` — **test_sample::test_same_bug_variant_2** — AssertionError: ERROR user missing for id=999 | assert False

### Group 4 — 1 occurrences
- Fingerprint: `assertionerror: lookup failed: user not found (id=555)
assert false`
- Examples:
  - `report_run6.xml` — **test_sample::test_same_bug_variant_3** — AssertionError: lookup failed: user not found (id=555) | assert False

### Group 5 — 1 occurrences
- Fingerprint: `assertionerror: user not found: id=123
assert false`
- Examples:
  - `report_run6.xml` — **test_sample::test_same_bug_variant_1** — AssertionError: user not found: id=123 | assert False

## 📊 Top flakiest tests

| Test ID | Runs | Passes | Fails |
|---|---:|---:|---:|
| `test_sample::test_same_bug_variant_1` | 2 | 1 | 1 |
| `test_sample::test_same_bug_variant_2` | 2 | 1 | 1 |
| `test_sample::test_same_bug_variant_3` | 2 | 1 | 1 |

## Runs included
- `examples\report_run4.xml`
- `examples\report_run5.xml`
- `examples\report_run6.xml`
