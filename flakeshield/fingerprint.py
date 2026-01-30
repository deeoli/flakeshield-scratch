"""
Failure fingerprinting (v0.1)

Goal:
Turn noisy failure messages / tracebacks into
stable, comparable signatures for grouping.
"""

import re
from typing import Optional


def fingerprint_failure(
    message: Optional[str],
    traceback: Optional[str],
) -> Optional[str]:
    """
    Produce a normalized fingerprint string for a failure.

    Strategy (simple, explainable):
    - Prefer message if present
    - Fallback to traceback
    - Lowercase
    - Remove file paths
    - Remove line numbers
    - Collapse whitespace
    """

    if not message and not traceback:
        return None

    text = message or traceback
    text = text.lower()

    # Remove file paths (Windows + Unix)
    text = re.sub(r"[a-zA-Z]:\\\\[^\\s]+", "<path>", text)
    text = re.sub(r"/[^\\s]+", "<path>", text)

    # Remove line numbers
    text = re.sub(r"line \\d+", "line <n>", text)
    text = re.sub(r":\\d+", ":<n>", text)

    # Collapse whitespace
    text = re.sub(r"\\s+", " ", text).strip()

    return text
