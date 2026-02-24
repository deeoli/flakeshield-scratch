"""Configuration loader for FlakeShield.

Currently supports optional JSON file with minimal keys:
- min_runs: int
- enable_semantic: bool

No external dependencies; just uses stdlib json.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict


def load_config(path: str | None) -> Dict[str, Any]:
    """Return configuration dictionary.

    If *path* is ``None`` the loader looks for ``.flakeshield.json`` in the
    current working directory.  If the file doesn't exist, an empty dict is
    returned (FlakeShield behaviour remains unchanged).

    If the file exists it is parsed as JSON and must produce a mapping; other
    types or parse errors result in a ``SystemExit`` with a user-friendly
    message.  The caller is responsible for using only supported keys.
    """

    if path is None:
        path = os.path.join(os.getcwd(), ".flakeshield.json")

    if not path or not os.path.isfile(path):
        # no config present
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:  # parse error, IO error, etc.
        raise SystemExit(f"Failed to load config '{path}': {exc}")

    if not isinstance(data, dict):
        raise SystemExit(f"Config file '{path}' must contain a JSON object")

    return data
