# FlakeShield Report

- Runs considered: **4**

## ⚠️ Flaky tests detected
- **test_sample::test_flaky** → `failed, passed`

## 🔥 Failure groups
### Group 1 — 4 occurrences
Fingerprint:
`assert 1 == 2`
Examples:
- `report.xml` — **test_sample::test_always_fails** — assert 1 == 2
- `report_run2.xml` — **test_sample::test_always_fails** — assert 1 == 2
- `report_run3.xml` — **test_sample::test_always_fails** — assert 1 == 2
- `report_run4.xml` — **test_sample::test_always_fails** — assert 1 == 2

### Group 2 — 1 occurrences
Fingerprint:
`assert false
 +  where false = choice([true, false])
 +    where choice = random.choice`
Examples:
- `report_run4.xml` — **test_sample::test_flaky** — assert False
 +  where False = choice([True, False])
 +    where choice = random.choice

## Runs included
- `examples\report.xml`
- `examples\report_run2.xml`
- `examples\report_run3.xml`
- `examples\report_run4.xml`
