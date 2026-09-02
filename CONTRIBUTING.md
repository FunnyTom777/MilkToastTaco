# CONTRIBUTING.md

Welcome to Milk Toast Taco! :D

## Setup

Requires **Python 3.11+**.

With the dashboard (terminal dev console):

```
pip install -e ".[dashboard]"
```

With everything (dashboard + Phase 2 web dashboard + dev tooling):

```
pip install -e ".[dashboard,web,dev]"
```

Core systems only need the standard library — no third-party packages are
required to run or test them.

## Running tests

The project uses the built-in `unittest` framework:

```
python -m unittest discover -s core -p "test_*.py"
python -m unittest tests.test_player_manager
```

## Building

```
python -m build
```

## Project layout

- `core/` — the main Python package (systems, loaders, etc.)
- `tests/` — integration-style tests
- `docs/` — design and planning documents
- `releases/` — patch notes
- `logs/` — runtime logs (gitignored)