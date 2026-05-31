# FlakeShield (Archived)

This repository has been **archived**. Development and releases continue in the split repositories:

| Repository | Purpose |
|---|---|
| [deeoli/flakeshield-action](https://github.com/deeoli/flakeshield-action) | Public GitHub Action install layer (MIT) |
| [deeoli/flakeshield-core](https://github.com/deeoli/flakeshield-core) | Private engine (closed beta) |

## Install

Use the public action for new integrations:

```yaml
uses: deeoli/flakeshield-action@v0.6.0-beta.1
with:
  reports: "outputs/junit_run*.xml"
  out_prefix: outputs/flake_report
  db_path: outputs/flakeshield.db
  enable_semantic: "true"
  warn_on_high: "true"
  fail_on_critical: "false"
```

See [examples/canonical-workflow.yml](https://github.com/deeoli/flakeshield-action/blob/main/examples/canonical-workflow.yml) in the action repo.

## Historical tags

Existing tags on this repo (`v0.4.x`, `v0.5.x`) remain for reference. New releases publish from `flakeshield-action` and `flakeshield-core` only.

## License

Historical MIT license applies to this archived monolith. The current FlakeShield engine is proprietary; the public action wrapper is MIT.
