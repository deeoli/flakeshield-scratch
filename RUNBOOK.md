# FlakeShield Runbook (local)

## Setup (Windows + Git Bash)

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -U pip
pip install -r requirements.txt


### Sanity check (semantic actually enabled)
Open `outputs/flake_report.json` and confirm:

- `"semantic_enabled": true`
- `"fragmentation_delta"` is present (may be null if no failures)
