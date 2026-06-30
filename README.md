# VORTEX

**Manifest-driven self-improving optimization engine.**

VORTEX optimizes any project using YAML manifests — and can optimize itself.

## Features

- **Manifest-driven**: Define what to optimize in YAML
- **Metrics collection**: Shell commands → baseline → score
- **Training loop**: 6-step optimization cycle
- **3-layer memory**: Traces → Reflections → Knowledge
- **Skill library**: Reusable patterns with crystallization
- **Tree search**: Explore multiple change branches
- **Multi-agent debate**: 13 debate methods with diverse personalities
- **Swarm exploration**: Distributed optimization agents
- **Research agent**: Auto-discovery of new papers from arXiv
- **Self-improvement**: Optimizes its own parameters
- **Convergence detection**: Stops when improvement plateaus
- **WAL**: Crash recovery with Write-Ahead Log
- **Sandbox**: Isolated Docker execution
- **Audit trail**: Immutable chain-hashed history
- **Feature flags**: Dynamic enable/disable
- **A/B testing**: Compare strategies statistically
- **Explainability**: Human-readable decision explanations
- **Hot reload**: Manifest changes without restart
- **Resource governor**: Rate limiting and budget control

## Quick Start

```bash
# Install
git clone https://github.com/jul-ienfr/Vortex.git
cd Vortex
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Analyze a project
vortex analyze /path/to/project

# Run optimization
vortex run manifest.yaml

# Research
vortex research --topic "self-improving agents"

# Status
vortex status
```

## Manifest Examples

### Basic optimization
```yaml
name: my-project
project_path: /path/to/project
metrics:
  - name: test_coverage
    source: "python -m pytest --co -q | wc -l"
    direction: up
optimizer:
  cli: claude
  debate_enabled: true
```

### Performance optimization
```yaml
name: api-performance
project_path: /path/to/api
metrics:
  - name: response_time
    source: "curl -w '%{time_total}' -o /dev/null -s http://localhost:3000/health"
    direction: down
  - name: memory_usage
    source: "ps aux | grep api | awk '{print $6/1024}'"
    direction: down
optimizer:
  cli: claude
  debate_method: tradeoff
  budget_limit_usd: 10.0
```

### Self-optimization
```yaml
name: self-optimizer
project_path: /home/jul/projects/vortex
metrics:
  - name: test_count
    source: "python3 -m pytest tests/ --co -q 2>/dev/null | tail -1 | grep -oP '\\d+'"
    direction: up
optimizer:
  cli: claude
  self_improve_enabled: false
```

## Architecture

```
src/vortex/
├── manifest.py          # YAML manifest parsing
├── metrics.py           # Metrics collection + baseline
├── execution.py         # Training loop + git operations
├── convergence.py       # When to stop
├── history.py           # 3-layer memory system
├── skill_library.py     # Reusable optimization patterns
├── tree_search.py       # Explore change space
├── debate.py            # Multi-agent debate (13 methods)
├── swarm.py             # Distributed exploration
├── research.py          # Auto-discovery of research
├── self_improve.py      # Self-optimization
├── hooks.py             # Dynamic hooks
├── registry.py          # Multi-project management
├── engine.py            # Main optimization loop
├── wal.py               # Crash recovery
├── sandbox.py           # Isolated execution
├── audit.py             # Immutable audit trail
├── feature_flags.py     # Dynamic enable/disable
├── resource_governor.py # Rate limiting
├── explainability.py    # Decision explanations
├── ab_testing.py        # Strategy comparison
├── hot_reload.py        # Manifest hot reload
├── migration.py         # Manifest version migration
├── marketplace.py       # Plugin ecosystem
├── dashboard.py         # Web dashboard
├── api.py               # REST API
└── cli.py               # CLI entry point
```

## CLI Commands

```bash
vortex run manifest.yaml              # Run optimization
vortex run manifest.yaml --cycle      # Single cycle
vortex run manifest.yaml --dry-run    # Simulate only
vortex analyze /path/to/project       # Analyze project
vortex research --topic "..."         # Research papers
vortex projects list                  # List projects
vortex hooks list                     # List hooks
vortex skills list                    # List skills
vortex status                         # Show status
vortex --version                      # Show version
```

## Testing

```bash
pytest tests/ -v                      # Run all tests
pytest tests/ -v --cov=vortex         # With coverage
pytest tests/test_debate.py -v        # Specific test file
```

## License

MIT
