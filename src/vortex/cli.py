"""CLI entry point for VORTEX."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="vortex",
        description="VORTEX — Manifest-driven self-improving optimization engine",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # vortex run
    run_parser = subparsers.add_parser("run", help="Run optimization cycle(s)")
    run_parser.add_argument("manifest", type=Path, help="Path to YAML manifest")
    run_parser.add_argument("--cycle", action="store_true", help="Run single cycle only")
    run_parser.add_argument("--fresh-baseline", action="store_true", help="Force new baseline")
    run_parser.add_argument("--dry-run", action="store_true", help="Simulate without executing")
    run_parser.add_argument("--max-cycles", type=int, default=None, help="Max cycles to run")
    run_parser.add_argument("--budget", type=float, default=None, help="Max budget in USD")

    # vortex analyze
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a project")
    analyze_parser.add_argument("project", type=Path, help="Path to project")
    analyze_parser.add_argument("--focus", choices=["security", "performance", "quality", "all"], default="all")
    analyze_parser.add_argument("--generate-manifest", action="store_true", help="Generate vortex.yaml")

    # vortex research
    research_parser = subparsers.add_parser("research", help="Run research cycle")
    research_parser.add_argument("manifest", type=Path, nargs="?", help="Path to YAML manifest")
    research_parser.add_argument("--topic", type=str, help="Specific research topic")
    research_parser.add_argument("--depth", type=int, default=1, help="Research depth")
    research_parser.add_argument("--update-deps", action="store_true", help="Update dependencies")

    # vortex projects
    projects_parser = subparsers.add_parser("projects", help="Manage projects")
    projects_sub = projects_parser.add_subparsers(dest="projects_command")
    projects_sub.add_parser("list", help="List all projects")
    add_parser = projects_sub.add_parser("add", help="Add a project")
    add_parser.add_argument("path", type=Path, help="Project path")
    add_parser.add_argument("--manifest", type=Path, help="Manifest path")
    create_parser = projects_sub.add_parser("create", help="Create a new project")
    create_parser.add_argument("name", type=str, help="Project name")
    create_parser.add_argument("--type", type=str, help="Project type")
    create_parser.add_argument("--language", type=str, default="python")

    # vortex status
    status_parser = subparsers.add_parser("status", help="Show status")
    status_parser.add_argument("manifest", type=Path, nargs="?", help="Path to YAML manifest")

    # vortex hooks
    hooks_parser = subparsers.add_parser("hooks", help="Manage hooks")
    hooks_sub = hooks_parser.add_subparsers(dest="hooks_command")
    hooks_sub.add_parser("list", help="List hooks")
    hooks_create = hooks_sub.add_parser("create", help="Create a hook")
    hooks_create.add_argument("name", type=str)
    hooks_create.add_argument("--trigger", type=str, required=True)
    hooks_create.add_argument("--command", type=str, required=True)
    hooks_sub.add_parser("delete", help="Delete a hook").add_argument("hook_id", type=str)

    # vortex plugins
    plugins_parser = subparsers.add_parser("plugins", help="Manage plugins")
    plugins_sub = plugins_parser.add_subparsers(dest="plugins_command")
    plugins_sub.add_parser("list", help="List plugins")
    plugins_install = plugins_sub.add_parser("install", help="Install a plugin")
    plugins_install.add_argument("source", type=str)
    plugins_sub.add_parser("delete", help="Delete a plugin").add_argument("plugin_id", type=str)

    # vortex skills
    skills_parser = subparsers.add_parser("skills", help="Manage skills")
    skills_sub = skills_parser.add_subparsers(dest="skills_command")
    skills_sub.add_parser("list", help="List skills")
    skills_create = skills_sub.add_parser("create", help="Create a skill")
    skills_create.add_argument("name", type=str)
    skills_create.add_argument("--steps", type=Path, help="Steps YAML file")
    skills_sub.add_parser("delete", help="Delete a skill").add_argument("skill_id", type=str)

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    # Dispatch to commands
    if args.command == "run":
        return _cmd_run(args)
    elif args.command == "analyze":
        return _cmd_analyze(args)
    elif args.command == "research":
        return _cmd_research(args)
    elif args.command == "projects":
        return _cmd_projects(args)
    elif args.command == "status":
        return _cmd_status(args)
    elif args.command == "hooks":
        return _cmd_hooks(args)
    elif args.command == "plugins":
        return _cmd_plugins(args)
    elif args.command == "skills":
        return _cmd_skills(args)

    parser.print_help()
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    """Execute the run command."""
    from vortex.manifest import ManifestConfig
    from vortex.metrics import BaselineManager, MetricsCollector

    manifest = ManifestConfig.from_yaml(args.manifest)
    collector = MetricsCollector(manifest)
    baseline = BaselineManager(manifest)

    if args.fresh_baseline or baseline.load_baseline() is None:
        print("Establishing baseline...")
        bl = baseline.establish_baseline(collector)
        print(f"Baseline: {bl}")
    else:
        bl = baseline.load_baseline()
        print(f"Using existing baseline: {bl}")

    # Collect current metrics
    current = collector.collect()
    print(f"Current metrics: {current}")

    # Score
    score, deltas = baseline.score(current, bl)
    print(f"Score: {score:.3f}")
    print(f"Deltas: {deltas}")

    return 0


def _cmd_analyze(args: argparse.Namespace) -> int:
    """Execute the analyze command."""
    print(f"Analyzing project at {args.project} (focus: {args.focus})")
    # TODO: Implement full analysis
    return 0


def _cmd_research(args: argparse.Namespace) -> int:
    """Execute the research command."""
    print("Running research cycle...")
    # TODO: Implement research
    return 0


def _cmd_projects(args: argparse.Namespace) -> int:
    """Execute the projects command."""
    if args.projects_command == "list":
        print("Registered projects:")
        # TODO: List from registry
    elif args.projects_command == "add":
        print(f"Adding project at {args.path}")
    elif args.projects_command == "create":
        print(f"Creating project '{args.name}'")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    """Execute the status command."""
    print("VORTEX status:")
    print("  Version: 0.1.0")
    print("  Status: OK")
    return 0


def _cmd_hooks(args: argparse.Namespace) -> int:
    """Execute the hooks command."""
    print("Hooks management")
    return 0


def _cmd_plugins(args: argparse.Namespace) -> int:
    """Execute the plugins command."""
    print("Plugins management")
    return 0


def _cmd_skills(args: argparse.Namespace) -> int:
    """Execute the skills command."""
    print("Skills management")
    return 0


if __name__ == "__main__":
    sys.exit(main())
