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
    parser.add_argument("--version", action="version", version="VORTEX 0.1.0")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # vortex run
    run_parser = subparsers.add_parser("run", help="Run optimization cycle(s)")
    run_parser.add_argument("manifest", type=Path, help="Path to YAML manifest")
    run_parser.add_argument("--cycle", action="store_true", help="Run single cycle only")
    run_parser.add_argument("--fresh-baseline", action="store_true", help="Force new baseline")
    run_parser.add_argument("--dry-run", action="store_true", help="Simulate without executing")
    run_parser.add_argument("--max-cycles", type=int, default=None, help="Max cycles to run")

    # vortex analyze
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a project")
    analyze_parser.add_argument("project", type=Path, help="Path to project")
    analyze_parser.add_argument("--focus", choices=["security", "performance", "quality", "all"], default="all")

    # vortex research
    research_parser = subparsers.add_parser("research", help="Run research cycle")
    research_parser.add_argument("--topic", type=str, help="Specific research topic")
    research_parser.add_argument("--depth", type=int, default=1, help="Research depth")

    # vortex projects
    projects_parser = subparsers.add_parser("projects", help="Manage projects")
    projects_sub = projects_parser.add_subparsers(dest="projects_command")
    projects_sub.add_parser("list", help="List all projects")
    add_parser = projects_sub.add_parser("add", help="Add a project")
    add_parser.add_argument("path", type=Path, help="Project path")

    # vortex status
    subparsers.add_parser("status", help="Show status")

    # vortex hooks
    hooks_parser = subparsers.add_parser("hooks", help="Manage hooks")
    hooks_sub = hooks_parser.add_subparsers(dest="hooks_command")
    hooks_sub.add_parser("list", help="List hooks")
    hooks_create = hooks_sub.add_parser("create", help="Create a hook")
    hooks_create.add_argument("name", type=str)
    hooks_create.add_argument("--trigger", type=str, required=True)
    hooks_create.add_argument("--command", type=str, required=True)

    # vortex skills
    skills_parser = subparsers.add_parser("skills", help="Manage skills")
    skills_sub = skills_parser.add_subparsers(dest="skills_command")
    skills_sub.add_parser("list", help="List skills")
    skills_create = skills_sub.add_parser("create", help="Create a skill")
    skills_create.add_argument("name", type=str)
    skills_create.add_argument("--description", type=str, default="")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

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
    elif args.command == "skills":
        return _cmd_skills(args)

    parser.print_help()
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    """Execute the run command."""
    from vortex.engine import Optimizer

    print(f"Starting VORTEX optimization for {args.manifest}")
    optimizer = Optimizer(args.manifest, dry_run=args.dry_run)
    optimizer.run(max_cycles=1 if args.cycle else args.max_cycles)
    return 0


def _cmd_analyze(args: argparse.Namespace) -> int:
    """Execute the analyze command."""
    print(f"Analyzing project at {args.project} (focus: {args.focus})")
    # Basic file structure analysis
    if not args.project.exists():
        print(f"Error: {args.project} does not exist")
        return 1
    py_files = list(args.project.rglob("*.py"))
    print(f"  Python files: {len(py_files)}")
    print(f"  Total files: {len(list(args.project.rglob('*')))}")
    return 0


def _cmd_research(args: argparse.Namespace) -> int:
    """Execute the research command."""
    from vortex.research import ResearchAgent

    topics = [args.topic] if args.topic else ["self-improving agents", "LLM optimization"]
    agent = ResearchAgent(Path.cwd())
    report = agent.research_cycle(topics)
    print(f"Research complete: {report.findings_count} findings, {report.relevant_count} relevant")
    for rec in report.recommendations:
        print(f"  [{rec.priority}] {rec.title}")
    return 0


def _cmd_projects(args: argparse.Namespace) -> int:
    """Execute the projects command."""
    from vortex.registry import ProjectRegistry

    registry = ProjectRegistry()
    if args.projects_command == "list":
        projects = registry.list_projects()
        if not projects:
            print("No registered projects.")
        for p in projects:
            print(f"  {p.name} ({p.status}) — {p.path}")
    elif args.projects_command == "add":
        entry = registry.register(args.path.name, args.path, args.path / "vortex.yaml")
        print(f"Added project: {entry.name} ({entry.id})")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    """Execute the status command."""
    from pathlib import Path as P
    vortex_dir = P(__file__).parent.parent.parent
    src_files = list((vortex_dir / "src" / "vortex").glob("*.py"))
    test_files = list((vortex_dir / "tests").glob("test_*.py"))
    print(f"VORTEX v0.1.0")
    print(f"  Modules: {len(src_files)}")
    print(f"  Test files: {len(test_files)}")
    print(f"  GitHub: https://github.com/jul-ienfr/Vortex")
    print(f"  Install: pip install -e .")
    print(f"  Usage: vortex run manifest.yaml")
    return 0


def _cmd_hooks(args: argparse.Namespace) -> int:
    """Execute the hooks command."""
    from vortex.hooks import HookManager

    manager = HookManager(Path.cwd())
    if args.hooks_command == "list":
        hooks = manager.list_hooks()
        if not hooks:
            print("No hooks configured.")
        for h in hooks:
            print(f"  {h.name} ({h.trigger}) — {'enabled' if h.enabled else 'disabled'}")
    elif args.hooks_command == "create":
        hook = manager.create_hook(args.name, args.trigger, args.command)
        print(f"Created hook: {hook.name} ({hook.id})")
    return 0


def _cmd_skills(args: argparse.Namespace) -> int:
    """Execute the skills command."""
    from vortex.skill_library import SkillLibrary

    lib = SkillLibrary(Path.cwd())
    if args.skills_command == "list":
        skills = lib.list_skills()
        if not skills:
            print("No skills.")
        for s in skills:
            c = " [crystallized]" if s.crystallized else ""
            print(f"  {s.name}{c} — success: {s.success_count}, failure: {s.failure_count}")
    elif args.skills_command == "create":
        skill = lib.create_skill(args.name, args.description, "template")
        print(f"Created skill: {skill.name} ({skill.id})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
