"""Tests for GitHub PR comment helpers."""

import json
from unittest.mock import MagicMock, patch

import pytest

from flakeshield.github_pr import find_flakeshield_comment, update_or_create_comment


@pytest.fixture
def mock_requests():
    with patch("flakeshield.github_pr.requests") as mock:
        yield mock


class TestFindFlakeshieldComment:
    def test_find_comment_when_exists(self, mock_requests):
        """Finding existing FlakeShield comment returns correct ID."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"id": 1, "body": "Other comment"},
            {"id": 2, "body": "<!-- FlakeShield --> report data"},
            {"id": 3, "body": "Another comment"},
        ]
        mock_requests.get.return_value = mock_response

        result = find_flakeshield_comment("token", "owner", "repo", 42)

        assert result == 2
        mock_requests.get.assert_called_once()

    def test_find_comment_when_not_exists(self, mock_requests):
        """No marker → returns None."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"id": 1, "body": "Comment 1"},
            {"id": 2, "body": "Comment 2"},
        ]
        mock_requests.get.return_value = mock_response

        result = find_flakeshield_comment("token", "owner", "repo", 42)

        assert result is None

    def test_find_comment_empty_list(self, mock_requests):
        """Empty comments list → returns None."""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_requests.get.return_value = mock_response

        result = find_flakeshield_comment("token", "owner", "repo", 42)

        assert result is None

    def test_find_comment_api_error(self, mock_requests):
        """API error → returns None gracefully."""
        mock_requests.get.side_effect = Exception("API error")

        result = find_flakeshield_comment("token", "owner", "repo", 42)

        assert result is None


class TestUpdateOrCreateComment:
    def test_create_comment_when_not_exists(self, mock_requests):
        """New comment created if none exists."""
        # First call: find_flakeshield_comment → no existing
        find_response = MagicMock()
        find_response.json.return_value = []

        # Second call: create_comment → success
        create_response = MagicMock()
        create_response.json.return_value = {"id": 5}

        mock_requests.get.return_value = find_response
        mock_requests.post.return_value = create_response

        result = update_or_create_comment(
            "token", "owner", "repo", 42, "# Report\n\n<!-- FlakeShield -->"
        )

        assert result == 5
        mock_requests.post.assert_called_once()
        call_kwargs = mock_requests.post.call_args[1]
        assert call_kwargs["json"]["body"] == "# Report\n\n<!-- FlakeShield -->"

    def test_update_comment_when_exists(self, mock_requests):
        """Existing comment is updated."""
        # First call: find_flakeshield_comment → existing ID 3
        find_response = MagicMock()
        find_response.json.return_value = [
            {"id": 1, "body": "Other"},
            {"id": 3, "body": "<!-- FlakeShield --> old content"},
        ]

        # Second call: update_comment → success
        update_response = MagicMock()

        mock_requests.get.return_value = find_response
        mock_requests.patch.return_value = update_response

        result = update_or_create_comment(
            "token", "owner", "repo", 42, "# New Report\n\n<!-- FlakeShield -->"
        )

        assert result == 3
        mock_requests.patch.assert_called_once()
        call_url = mock_requests.patch.call_args[0][0]
        assert "comments/3" in call_url

    def test_idempotency_same_content(self, mock_requests):
        """Running twice with same markdown → updates same comment ID."""
        # Simulate finding the same comment both times
        find_response = MagicMock()
        find_response.json.return_value = [
            {"id": 10, "body": "<!-- FlakeShield --> content"},
        ]
        update_response = MagicMock()

        mock_requests.get.return_value = find_response
        mock_requests.patch.return_value = update_response

        markdown = "# Report\n\n<!-- FlakeShield -->"

        # First call
        result1 = update_or_create_comment("token", "owner", "repo", 42, markdown)
        # Second call
        result2 = update_or_create_comment("token", "owner", "repo", 42, markdown)

        assert result1 == result2 == 10
        assert mock_requests.patch.call_count == 2  # Both times should update
