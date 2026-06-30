# Contributing to VORTEX

Thank you for your interest in contributing!

## Development Setup

```bash
git clone https://github.com/jul-ienfr/Vortex.git
cd Vortex
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest tests/ -v
pytest tests/ -v --cov=vortex
```

## Code Style

- Python 3.11+
- Type hints on all public functions
- `from __future__ import annotations` in every file
- `logging.getLogger(__name__)` for logging
- Dataclasses for data structures
- Path-based I/O (no string paths)

## Adding a New Module

1. Create `src/vortex/your_module.py`
2. Create `tests/test_your_module.py`
3. Add at least 3 tests
4. Run `pytest tests/test_your_module.py -v`
5. Update README.md if needed

## Adding a New CLI Command

1. Add subparser in `cli.py`
2. Implement `_cmd_your_command(args)`
3. Add tests in `tests/test_cli.py`

## Pull Request Process

1. Create a feature branch
2. Make your changes
3. Add tests
4. Run `pytest tests/ -v`
5. Submit PR with description

## Reporting Issues

- Use GitHub Issues
- Include Python version, OS, and VORTEX version
- Provide minimal reproduction steps
