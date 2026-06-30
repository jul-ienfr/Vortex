# VORTEX

**Manifest-driven self-improving optimization engine.**

VORTEX optimizes any project using YAML manifests — and can optimize itself.

## Features

- **Manifest-driven**: Define what to optimize in YAML
- **Metrics collection**: Shell commands → baseline → score
- **Training loop**: 6-step optimization (rollout → reflect → aggregate → select → update → evaluate)
- **3-layer memory**: Traces → Reflections → Knowledge
- **Skill library**: Reusable patterns with crystallization
- **Tree search**: Explore multiple change branches (archive-based evolution)
- **Multi-agent debate**: 13 debate methods with diverse agent personalities
- **Swarm exploration**: Distributed optimization agents
- **Research agent**: Auto-discovery of new papers and techniques
- **Self-improvement**: Optimizes its own parameters
- **Convergence detection**: Stops when improvement plateaus

## Quick Start

```bash
# Install
pip install -e .

# Analyze a project
vortex analyze /path/to/project

# Run optimization
vortex run manifest.yaml

# Single cycle
vortex run manifest.yaml --cycle

# Research
vortex research --topic "self-improving agents"
```

## Manifest Example

```yaml
name: my-project
project_path: /path/to/project
metrics:
  - name: test_coverage
    source: "python -m pytest --co -q | wc -l"
    direction: up
  - name: security_score
    source: "bandit -r src/ -f json | jq '.metrics._totals.severity'"
    direction: down
constraints:
  - "Don't break existing API"
optimizer:
  cli: claude
  debate_enabled: true
  debate_method: standard
  model: claude-sonnet-4-6
```

## Architecture

```
src/vortex/
├── manifest.py        # YAML manifest parsing
├── metrics.py         # Metrics collection + baseline
├── execution.py       # Training loop + git operations
├── convergence.py     # When to stop
├── history.py         # 3-layer memory system
├── skill_library.py   # Reusable optimization patterns
├── tree_search.py     # Explore change space
├── debate.py          # Multi-agent debate (13 methods)
├── swarm.py           # Distributed exploration
├── research.py        # Auto-discovery of research
├── self_improve.py    # Self-optimization
├── hooks.py           # Dynamic hooks
├── registry.py        # Multi-project management
└── engine.py          # Main optimization loop
```

## License

MIT
