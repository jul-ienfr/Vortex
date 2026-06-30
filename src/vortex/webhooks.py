"""Webhook notifications for VORTEX."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


@dataclass
class WebhookConfig:
    """Configuration for a webhook."""

    url: str
    events: list[str] = field(default_factory=lambda: ["cycle_complete", "optimization_complete"])
    enabled: bool = True
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class WebhookPayload:
    """Payload sent to webhook."""

    event: str
    project: str
    data: dict = field(default_factory=dict)


class WebhookManager:
    """Manages webhook notifications."""

    def __init__(self, project_path: Path):
        self.config_path = project_path / ".vortex" / "webhooks.json"
        self.webhooks: list[WebhookConfig] = []
        self._load()

    def _load(self) -> None:
        if self.config_path.exists():
            data = json.loads(self.config_path.read_text())
            self.webhooks = [WebhookConfig(**w) for w in data.get("webhooks", [])]

    def _save(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps({
            "webhooks": [asdict(w) for w in self.webhooks]
        }, indent=2))

    def add_webhook(self, url: str, events: list[str] | None = None) -> WebhookConfig:
        """Add a webhook."""
        webhook = WebhookConfig(
            url=url,
            events=events or ["cycle_complete", "optimization_complete"],
        )
        self.webhooks.append(webhook)
        self._save()
        return webhook

    def remove_webhook(self, url: str) -> None:
        """Remove a webhook."""
        self.webhooks = [w for w in self.webhooks if w.url != url]
        self._save()

    def notify(self, event: str, project: str, data: dict | None = None) -> list[bool]:
        """Send notifications to all matching webhooks."""
        results = []
        for webhook in self.webhooks:
            if not webhook.enabled or event not in webhook.events:
                continue
            try:
                payload = WebhookPayload(event=event, project=project, data=data or {})
                response = requests.post(
                    webhook.url,
                    json=asdict(payload),
                    headers=webhook.headers,
                    timeout=10,
                )
                results.append(response.status_code == 200)
            except Exception as e:
                logger.warning("Webhook %s failed: %s", webhook.url, e)
                results.append(False)
        return results

    def list_webhooks(self) -> list[WebhookConfig]:
        """List all webhooks."""
        return self.webhooks
