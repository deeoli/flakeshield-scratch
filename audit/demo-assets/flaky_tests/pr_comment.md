### Flaky tests
- **integration::test_auth_flow** (runs=5, rate=0.60)
- **integration::test_db_migration** (runs=4, rate=0.50)

### Regressions
- timeout: auth service took > 5000ms (since run_100)
- deadlockdetectederror: mysql deadlock (since run_101)

<!-- FlakeShield -->

