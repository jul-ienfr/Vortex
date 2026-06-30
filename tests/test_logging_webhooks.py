"""Tests for logging and webhooks."""

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

from vortex.logging_config import setup_logging
from vortex.webhooks import WebhookConfig, WebhookManager


def test_setup_logging():
    """Test logging setup."""
    setup_logging("DEBUG")
    logger = logging.getLogger("vortex")
    assert logger.level == logging.DEBUG


def test_webhook_crud(tmp_project: Path):
    """Test webhook CRUD."""
    manager = WebhookManager(tmp_project)
    webhook = manager.add_webhook("http://example.com/hook", ["cycle_complete"])
    assert webhook.url == "http://example.com/hook"
    assert len(manager.list_webhooks()) == 1
    manager.remove_webhook("http://example.com/hook")
    assert len(manager.list_webhooks()) == 0


def test_webhook_notify(tmp_project: Path):
    """Test webhook notification."""
    manager = WebhookManager(tmp_project)
    manager.add_webhook("http://example.com/hook", ["test_event"])

    with patch("vortex.webhooks.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        results = manager.notify("test_event", "test_project", {"key": "value"})
        assert len(results) == 1
        assert results[0] is True
        mock_post.assert_called_once()


def test_webhook_event_filter(tmp_project: Path):
    """Test webhook event filtering."""
    manager = WebhookManager(tmp_project)
    manager.add_webhook("http://example.com/hook", ["event_a"])

    with patch("vortex.webhooks.requests.post") as mock_post:
        # Should not be called for event_b
        results = manager.notify("event_b", "test_project")
        assert len(results) == 0
        mock_post.assert_not_called()
