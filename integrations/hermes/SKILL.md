---
name: vortex
description: "Manifest-driven self-improving optimization engine"
version: 1.0.0
platforms: [linux]
metadata:
  hermes:
    tags: [optimizer, automation, metrics, self-improving]
---

# VORTEX Skill

Generic optimization engine that reads a YAML manifest and runs improvement cycles.

## When to use
- User wants to optimize a project based on measurable metrics
- User has a YAML manifest defining what to optimize
- Need to run iterative improvement with automatic rollback

## Commands

### Run optimizer
```bash
cd /home/jul/projects/vortex && source .venv/bin/activate && vortex run /path/to/manifest.yaml
```

### Analyze a project
```bash
cd /home/jul/projects/vortex && source .venv/bin/activate && vortex analyze /path/to/project
```

### Research
```bash
cd /home/jul/projects/vortex && source .venv/bin/activate && vortex research --topic "optimization"
```

### List projects
```bash
cd /home/jul/projects/vortex && source .venv/bin/activate && vortex projects list
```

## Manifest Format
```yaml
name: my-project
project_path: /path/to/project
metrics:
  - name: test_coverage
    source: "python -m pytest --co -q | wc -l"
    direction: up
    weight: 2.0
constraints:
  - "Don't break existing API"
optimizer:
  cli: claude
  debate_enabled: true
  debate_method: standard
  model: claude-sonnet-4-6
  max_moves_per_cycle: null  # unlimited
  research_interval: 10
```
