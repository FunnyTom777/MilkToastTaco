# test_all.py — Project Scanner Guide

`test_all.py` runs three static-analysis tools over the repo and keeps only
high-priority errors (syntax errors, undefined names, real pylint errors, and
likely-crash mypy types). Style noise (`F401` unused imports, `F841` unused
locals, pygame `no-member` false positives, missing-stub notes, …) is filtered
out or demoted to a warning bucket.

## Quick start

| Command | What it does |
|---|---|
| `python test_all.py` | Scan, save a report, then open the interactive reader (default) |
| `python test_all.py --basic` | Scan and save a report only — no reader (CI / quick check) |
| `python test_all.py --view` | Open the reader on the latest saved report (no rescan) |
| `python test_all.py --view scan_reports/scan_report_20260913_093455.txt` | Open the reader on a specific report |

Reports live in `scan_reports/scan_report_YYYYMMDD_HHMMSS.txt`.
Old `scan_report_*.txt` files left in the repo root are auto-moved into
`scan_reports/` on the next scan.

## The interactive reader

After a scan you get a summary table plus an auto-outline of crucial hotspots
(files with the most critical hits, worst first). Then a menu:

- `1` — Critical errors only (syntax, undefined names, pylint errors,
  crash-prone mypy: `attr-defined`, `union-attr`, `arg-type`, `call-overload`,
  `operator`, `truthy-function`, …)
- `2` — Criticals + import-path warnings (`E0401` / `import-not-found` —
  usually a `PYTHONPATH` / package-layout symptom, not a per-line bug)
- `3` — Everything, including annotation-hygiene warnings (`[assignment]`
  missing annotations, `[no-redef]` fallback shadowing — fix when you touch
  the file)
- `4` — Filter by file text (e.g. `bank.py`)
- `5` — Filter by tool (`flake8` / `pylint` / `mypy`)
- `q` — Quit

Long output pages 40 lines at a time (`Enter` for more, `q` to stop).
Piped / non-TTY output (CI) skips the menu and just prints the criticals.
If `rich` is installed you get a formatted table; otherwise plain text.

## What counts as "critical"

- **flake8** (`--select=E999,E902,E911,F821,F822,F823,F831,F632,F633`):
  syntax errors and undefined names / duplicate args only.
- **pylint** (`--enable=E,F`, minus `no-member,no-name-in-module,
  c-extension-no-member`): real errors. The disabled checks are ~99% false
  positives on `pygame`, `PyQt6`, and `panda3d` (dynamic C-extension members).
- **mypy** (`--ignore-missing-imports --follow-imports=silent
  --show-error-codes`): crash-prone codes stay critical; `[assignment]`,
  `[no-redef]`, `[misc]` go to hygiene warnings; stub notes, `var-annotated`,
  `annotation-unchecked`, and fallback-import `no-redef` noise is dropped.

## Requirements

Tools are invoked as `python -m flake8 / pylint / mypy`, so install whichever
you want into the active environment. A missing tool degrades to a
`<tool not installed: …>` line instead of crashing the scan.
`rich` is optional and only affects reader formatting.
