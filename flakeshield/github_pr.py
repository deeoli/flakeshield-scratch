"""GitHub PR comment helpers for idempotent PR comment updates."""

import os
import requests

FLAKESHIELD_MARKER = "<!-- FlakeShield"


def find_flakeshield_comment(
    github_token: str, repo_owner: str, repo_name: str, issue_number: int
) -> int | None:
    """Find existing FlakeShield comment by marker.

    Returns comment ID if found, None otherwise.
    """
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{issue_number}/comments"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        comments = response.json()

        for comment in comments:
            if FLAKESHIELD_MARKER in comment.get("body", ""):
                return comment["id"]
    except Exception:
        pass

    return None


def update_or_create_comment(
    github_token: str, repo_owner: str, repo_name: str, issue_number: int, markdown: str
) -> int:
    """Update existing FlakeShield comment or create new one.

    Returns comment ID (created or updated).
    """
    existing_id = find_flakeshield_comment(
        github_token, repo_owner, repo_name, issue_number
    )

    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    if existing_id:
        # Update existing comment
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/comments/{existing_id}"
        response = requests.patch(
            url, json={"body": markdown}, headers=headers, timeout=10
        )
        response.raise_for_status()
        return existing_id
    else:
        # Create new comment
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{issue_number}/comments"
        response = requests.post(
            url, json={"body": markdown}, headers=headers, timeout=10
        )
        response.raise_for_status()
        return response.json()["id"]
