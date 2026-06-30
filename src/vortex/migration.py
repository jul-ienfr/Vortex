"""Manifest migration for version upgrades."""

from __future__ import annotations

import shutil
from pathlib import Path

import yaml


class MigrationError(Exception):
    """Raised when migration fails."""


class Migration_1_0_to_1_1:
    """Migrate from v1.0 to v1.1."""

    target_version = "1.1"

    def apply(self, manifest: dict) -> dict:
        """Apply migration."""
        # Add optimizer section if missing
        if "optimizer" not in manifest:
            manifest["optimizer"] = {"cli": "claude"}
        manifest["version"] = self.target_version
        return manifest


class Migration_1_1_to_2_0:
    """Migrate from v1.1 to v2.0."""

    target_version = "2.0"

    def apply(self, manifest: dict) -> dict:
        """Apply migration."""
        # Rename deprecated fields
        if "max_changes" in manifest.get("optimizer", {}):
            manifest["optimizer"]["max_changes_per_cycle"] = manifest["optimizer"].pop("max_changes")
        manifest["version"] = self.target_version
        return manifest


class ManifestMigrator:
    """Migrates manifest files to the current version."""

    VERSION = "2.0"
    MIGRATIONS = {
        "1.0": Migration_1_0_to_1_1(),
        "1.1": Migration_1_1_to_2_0(),
    }

    def migrate(self, manifest_path: Path) -> Path:
        """Migrate a manifest to the current version."""
        manifest = yaml.safe_load(manifest_path.read_text())
        current_version = manifest.get("version", "1.0")

        if current_version == self.VERSION:
            return manifest_path

        # Run migrations
        while current_version != self.VERSION:
            migration = self.MIGRATIONS.get(current_version)
            if not migration:
                raise MigrationError(f"No migration from {current_version} to {self.VERSION}")
            manifest = migration.apply(manifest)
            current_version = migration.target_version

        # Backup original
        backup_path = manifest_path.with_suffix(f".v{current_version}.yaml")
        shutil.copy2(manifest_path, backup_path)

        # Write migrated
        manifest_path.write_text(yaml.dump(manifest, default_flow_style=False))
        return manifest_path
