"""Manifest configuration and validation for VORTEX."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator


class MetricDef(BaseModel):
    """Definition of a single metric to track."""

    name: str
    source: str  # shell command that outputs JSON or a number
    direction: Literal["up", "down"]
    weight: float = 1.0
    baseline_samples: int = 1
    min_improvement_pct: float = 0.0


class OptimizerConfig(BaseModel):
    """Configuration for the optimizer engine."""

    cli: Literal["claude", "codex", "hermes"] = "claude"
    max_changes_per_cycle: int = 3
    max_moves_per_cycle: int | None = None  # None = unlimited
    rollback_on_regression: bool = True
    measurement_window_days: int = 0
    max_cycles: int | None = None  # None = run forever
    hypothesis_prompt_extra: str | None = None

    # Tree search
    tree_search_branches: int = 3

    # Reflection
    reflection_depth: int = 1

    # Skill library
    skill_library_enabled: bool = True

    # Self-improvement
    self_improve_enabled: bool = True

    # Constitutional rules
    constitutional_rules: list[str] = Field(default_factory=list)

    # Constraint gates
    constraint_gates: list[str] = Field(
        default_factory=lambda: [
            "tests_pass",
            "size_limits",
            "semantic_preservation",
            "no_regression",
            "review_required",
        ]
    )
    auto_discovered_gates: list[str] = Field(default_factory=list)

    # Research
    research_interval: int = 10
    research_topics: list[str] = Field(default_factory=list)
    auto_research_on_stagnation: bool = True

    # Multi-agent & swarm
    execution_mode: Literal["auto", "sequential", "parallel", "swarm"] = "auto"
    swarm_size: int = 3
    max_concurrent_agents: int = 3

    # Self-scheduling
    auto_reschedule_on_failure: bool = True
    auto_crystallize_on_success: bool = True
    budget_limit_usd: float = 5.0

    # Debate
    debate_enabled: bool = True
    debate_method: Literal[
        "standard", "oxford", "advocate", "socratic", "delphi",
        "brainstorm", "tradeoff", "red_team", "premortem",
        "six_hats", "dialectic", "steelman", "panel",
    ] = "standard"
    debate_rounds: int = 3
    debate_agents: int | None = None  # None = adaptive
    debate_roles: list[str] = Field(default_factory=lambda: ["optimist", "skeptic", "pragmatist"])
    debate_auto_method: bool = True

    # LLM model configuration
    model: str | None = None
    model_proxy: str | None = None
    model_api_key: str | None = None
    model_temperature: float = 0.7
    model_max_tokens: int = 4096

    # Convergence
    convergence_stagnation_limit: int = 10
    convergence_window_size: int = 20
    convergence_threshold: float = 0.001
    convergence_target_score: float | None = None
    convergence_min_cycles: int = 5


class ManifestConfig(BaseModel):
    """Root manifest configuration."""

    name: str
    description: str | None = None
    project_path: Path
    metrics: list[MetricDef]
    constraints: list[str] = Field(default_factory=list)
    optimizer: OptimizerConfig = Field(default_factory=OptimizerConfig)

    @classmethod
    def from_yaml(cls, path: Path) -> ManifestConfig:
        """Load and validate a manifest from a YAML file."""
        raw = yaml.safe_load(path.read_text())
        return cls(**raw)

    @model_validator(mode="after")
    def validate_project_path(self) -> ManifestConfig:
        if not self.project_path.exists():
            raise ValueError(f"project_path does not exist: {self.project_path}")
        return self
