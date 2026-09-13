"""Foolproof project scanner: flake8 + pylint + mypy, critical errors only.

Usage:
    python test_all.py              scan + interactive terminal reader (default)
    python test_all.py --basic      scan only, write scan_reports/*.txt, no reader
    python test_all.py --view       open reader on the latest saved report (no rescan)
    python test_all.py --view <path>  open reader on a specific report file

Reports are saved to: scan_reports/scan_report_YYYYMMDD_HHMMSS.txt
See docs/TEST_ALL_GUIDE.md for details.
"""
import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPORT_DIR = ROOT / "scan_reports"

# Directories to skip (venv is huge/slow and full of false positives)
EXCLUDE_DIRS = (".venv", "venv", "__pycache__", ".git", ".mypy_cache", "scan_reports")
MYPY_EXCLUDE_REGEX = r"(\.venv|venv|__pycache__|\.git|\.mypy_cache|scan_reports)/?"

# --- Flake8: EXACT codes that are almost always real bugs ---
FLAKE8_SELECT = "E999,E902,E911,F821,F822,F823,F831,F632,F633"
FLAKE8_CODE_RE = re.compile(r"\b(E999|E902|E911|E901|F821|F822|F823|F831|F632|F633)\b")

# --- Pylint ---
PYLINT_CODE_RE = re.compile(r"\.py:\d+:\d+:\s*[EF]\d{4}:")
# C-extension / Qt libs (pygame, PyQt6, panda3d) use dynamic members.
# E1101 no-member + E0611 no-name-in-module are ~99% false positives there.
PYLINT_DISABLE_NOISY = "no-member,no-name-in-module,c-extension-no-member"
PYLINT_IMPORT_RE = re.compile(r"E0401|import-error")

# --- Mypy ---
MYPY_NOISE_RES = [
    re.compile(r"\[import-untyped\]"),  # panda3d/direct.gui has no py.typed
    re.compile(r"Need type annotation.*\[var-annotated\]"),
    re.compile(r"\[annotation-unchecked\]"),
    re.compile(r"See https?://mypy\.readthedocs"),
    re.compile(r"Possible overload variants:"),
    re.compile(r"^\s*note:", re.IGNORECASE),
    # Fallback-import pattern used all over core/ (try: from orchestrator...):
    re.compile(r"already defined \(possibly by an import\) \[no-redef\]"),
    re.compile(r"All conditional function variants must have identical signatures\s*\[misc\]"),
    re.compile(r"Redefinition:\s*\[misc\]|\s*Original:"),
    re.compile(r"Name \"\w+\" already defined \(possibly by an import\)"),
    # Dynamic Color palette (Color.WHITE = Color(...) after class def) is valid:
    re.compile(r'"type\[Color\]" has no attribute "(WHITE|BLACK|RED|GREEN|BLUE|SKY)"'),
]
MYPY_IMPORT_RE = re.compile(r"\[(import-not-found|import-error)\]|Unable to import")
# Mypy codes that usually mean a real crash (None deref, wrong arg, bad op).
MYPY_CRITICAL_RE = re.compile(
    r"\[(attr-defined|union-attr|arg-type|call-overload|call-arg|operator|"
    r"truthy-function|truthy-bool|index|return-value|override|has-type|"
    r"callable|abstract|type-var|valid-type)\]"
)

# Optional rich for a nicer reader. Stdlib fallback if missing.
try:
    from rich.console import Console
    from rich.table import Table

    _RICH = True
except Exception:
    _RICH = False


# ------------------------------------------------------------------ helpers
def ensure_report_dir():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    return REPORT_DIR


def migrate_old_reports():
    """Move stray scan_report_*.txt from repo root into scan_reports/ (one-time cleanup)."""
    ensure_report_dir()
    moved = 0
    for p in ROOT.glob("scan_report_*.txt"):
        try:
            p.rename(REPORT_DIR / p.name)
            moved += 1
        except Exception:
            pass
    return moved


def run_tool(cmd, timeout=300):
    """Run a tool with ROOT cwd + PYTHONPATH, return stdout text. Never crash."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            env=env,
            timeout=timeout,
        )
        return (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
    except FileNotFoundError:
        return f"<tool not installed: {' '.join(cmd[:3])}>\n"
    except subprocess.TimeoutExpired:
        return f"<tool timed out after {timeout}s: {' '.join(cmd[:3])}>\n"


# ------------------------------------------------------------------ filters (structured)
def filter_flake8_list(output):
    return [ln for ln in output.splitlines() if FLAKE8_CODE_RE.search(ln)]


def filter_pylint_structured(output):
    errors, import_warnings = [], []
    for ln in output.splitlines():
        if not PYLINT_CODE_RE.search(ln):
            continue
        if PYLINT_IMPORT_RE.search(ln):
            import_warnings.append(ln)
        else:
            errors.append(ln)
    return errors, import_warnings


def filter_mypy_structured(output):
    errors, hygiene, import_warnings = [], [], []
    for ln in output.splitlines():
        s = ln.strip()
        if not s or s.startswith("Success:") or s.startswith("Found ") or "checked" in s:
            continue
        if MYPY_IMPORT_RE.search(ln):
            import_warnings.append(ln)
            continue
        if any(rx.search(ln) for rx in MYPY_NOISE_RES):
            continue
        if ": error:" not in ln:
            continue
        if MYPY_CRITICAL_RE.search(ln):
            errors.append(ln)
        else:
            hygiene.append(ln)
    return errors, hygiene, import_warnings


def render_report(stamp, flake, pylint_err, pylint_imp, mypy_err, mypy_hyg, mypy_imp):
    L = []
    L.append("=" * 60)
    L.append("Python Project Scan Report - HIGH PRIORITY ERRORS ONLY")
    L.append(f"Generated: {stamp}")
    L.append("=" * 60 + "\n")
    L.append("FLAKE8 RESULTS (Syntax & Undefined Names):")
    L.append(f"select={FLAKE8_SELECT}")
    L.append("-" * 60)
    L.append("\n".join(flake) if flake else "No critical issues found.")
    L.append("\n\nPYLINT RESULTS (Errors Only):")
    L.append("-" * 60)
    L.append("\n".join(pylint_err) if pylint_err else "No critical issues found.")
    if pylint_imp:
        L.append("\n[WARNING - import path, check PYTHONPATH / package imports]")
        L.append("\n".join(pylint_imp))
    L.append("\n\nMYPY RESULTS (Type Errors, noise filtered):")
    L.append("-" * 60)
    L.append("\n".join(mypy_err) if mypy_err else "No critical issues found.")
    if mypy_hyg:
        L.append("\n[WARNING - annotation hygiene, fix when touching the file]")
        L.append("\n".join(mypy_hyg))
    if mypy_imp:
        L.append("\n[WARNING - import path, check PYTHONPATH / package imports]")
        L.append("\n".join(mypy_imp))
    L.append("")
    return "\n".join(L)


# ------------------------------------------------------------------ scan
def run_scan():
    ensure_report_dir()
    migrate_old_reports()
    stamp = datetime.now()
    report_path = REPORT_DIR / f"scan_report_{stamp.strftime('%Y%m%d_%H%M%S')}.txt"

    flake_out = run_tool(
        [
            sys.executable, "-m", "flake8", ".",
            f"--select={FLAKE8_SELECT}",
            f"--exclude={','.join(EXCLUDE_DIRS)}",
            "--extend-exclude=scan_report_*.txt,scan_reports",
        ]
    )
    pylint_out = run_tool(
        [
            sys.executable, "-m", "pylint", ".",
            "--exit-zero",
            "--disable=all", "--enable=E,F",
            f"--disable={PYLINT_DISABLE_NOISY}",
            f"--ignore={','.join(EXCLUDE_DIRS)}",
            r"--ignore-paths=\.venv,venv,__pycache__,\.git,\.mypy_cache,scan_reports",
        ]
    )
    mypy_out = run_tool(
        [
            sys.executable, "-m", "mypy", ".",
            "--exclude", MYPY_EXCLUDE_REGEX,
            "--ignore-missing-imports",
            "--follow-imports=silent",
            "--show-error-codes",
        ]
    )

    flake = filter_flake8_list(flake_out)
    pylint_err, pylint_imp = filter_pylint_structured(pylint_out)
    mypy_err, mypy_hyg, mypy_imp = filter_mypy_structured(mypy_out)

    report_path.write_text(
        render_report(stamp, flake, pylint_err, pylint_imp, mypy_err, mypy_hyg, mypy_imp),
        encoding="utf-8",
    )
    data = {
        "path": report_path,
        "flake": flake,
        "pylint_err": pylint_err,
        "pylint_imp": pylint_imp,
        "mypy_err": mypy_err,
        "mypy_hyg": mypy_hyg,
        "mypy_imp": mypy_imp,
    }
    return data


def latest_report():
    ensure_report_dir()
    reports = sorted(REPORT_DIR.glob("scan_report_*.txt"))
    return reports[-1] if reports else None


def parse_report_file(path):
    """Rebuild structured buckets from a saved report (for --view without rescan)."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    flake, pylint_err, pylint_imp, mypy_err, mypy_hyg, mypy_imp = [], [], [], [], [], []
    section, bucket = None, "critical"
    for ln in text.splitlines():
        if ln.startswith("FLAKE8 RESULTS"):
            section, bucket = "flake", "critical"
            continue
        if ln.startswith("PYLINT RESULTS"):
            section, bucket = "pylint", "critical"
            continue
        if ln.startswith("MYPY RESULTS"):
            section, bucket = "mypy", "critical"
            continue
        if ln.startswith("[WARNING - import path"):
            bucket = "import"
            continue
        if ln.startswith("[WARNING - annotation hygiene"):
            bucket = "hygiene"
            continue
        if not re.search(r"\.py:\d+", ln):
            continue
        if section == "flake":
            flake.append(ln)
        elif section == "pylint":
            (pylint_imp if bucket == "import" else pylint_err).append(ln)
        elif section == "mypy":
            if bucket == "import":
                mypy_imp.append(ln)
            elif bucket == "hygiene":
                mypy_hyg.append(ln)
            else:
                mypy_err.append(ln)
    return {
        "path": Path(path),
        "flake": flake,
        "pylint_err": pylint_err,
        "pylint_imp": pylint_imp,
        "mypy_err": mypy_err,
        "mypy_hyg": mypy_hyg,
        "mypy_imp": mypy_imp,
    }


# ------------------------------------------------------------------ terminal reader
def _critical_items(data):
    items = []
    for ln in data["flake"]:
        items.append(("flake8", "critical", ln))
    for ln in data["pylint_err"]:
        items.append(("pylint", "critical", ln))
    for ln in data["mypy_err"]:
        items.append(("mypy", "critical", ln))
    return items


def _warning_items(data):
    items = []
    for ln in data["pylint_imp"]:
        items.append(("pylint", "import-warning", ln))
    for ln in data["mypy_hyg"]:
        items.append(("mypy", "hygiene", ln))
    for ln in data["mypy_imp"]:
        items.append(("mypy", "import-warning", ln))
    return items


def _print_summary(data):
    n_crit = len(data["flake"]) + len(data["pylint_err"]) + len(data["mypy_err"])
    n_warn = len(data["pylint_imp"]) + len(data["mypy_hyg"]) + len(data["mypy_imp"])
    if _RICH:
        c = Console()
        t = Table(title=f"Scan results - {data['path'].name}")
        t.add_column("Tool")
        t.add_column("Critical", justify="right")
        t.add_column("Warnings", justify="right")
        t.add_row("flake8", str(len(data["flake"])), "0")
        t.add_row("pylint", str(len(data["pylint_err"])), str(len(data["pylint_imp"])))
        t.add_row("mypy", str(len(data["mypy_err"])),
                  str(len(data["mypy_hyg"]) + len(data["mypy_imp"])))
        t.add_row("TOTAL", str(n_crit), str(n_warn), end_section=True)
        c.print(t)
        if n_crit == 0:
            c.print("[green]No critical issues found. Nice.[/green]")
    else:
        print(f"Report: {data['path']}")
        print(f"  flake8: {len(data['flake'])} critical")
        print(f"  pylint: {len(data['pylint_err'])} critical, {len(data['pylint_imp'])} import-warnings")
        print(f"  mypy:   {len(data['mypy_err'])} critical, "
              f"{len(data['mypy_hyg'])} hygiene, {len(data['mypy_imp'])} import-warnings")
        print(f"  TOTAL:  {n_crit} critical, {n_warn} warnings")
    # Auto-outline: top files by critical count
    counts = {}
    for _, _, ln in _critical_items(data):
        m = re.match(r"(.+?\.py)", ln)
        if m:
            f = m.group(1)
            counts[f] = counts.get(f, 0) + 1
    if counts:
        print("Crucial hotspots (most criticals first):")
        for f, n in sorted(counts.items(), key=lambda kv: -kv[1])[:10]:
            print(f"  {n:3d}x  {f}")
    return n_crit, n_warn


def _show_lines(lines, page_size=40):
    for i in range(0, len(lines), page_size):
        chunk = lines[i:i + page_size]
        for ln in chunk:
            print(ln)
        if i + page_size < len(lines):
            try:
                ans = input(f"-- {i + len(chunk)}/{len(lines)} -- Enter for more, q to stop: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if ans == "q":
                return


def launch_reader(data):
    _print_summary(data)
    if not sys.stdin.isatty():
        # Non-interactive shell (CI): dump criticals and exit
        for _, _, ln in _critical_items(data):
            print(ln)
        return
    crit = _critical_items(data)
    warn = _warning_items(data)
    while True:
        print("\n--- Reader ---")
        print(f"[1] Critical only ({len(crit)})  [2] Critical + import warnings "
              f"({len(crit) + len(data['pylint_imp']) + len(data['mypy_imp'])})  "
              f"[3] Everything ({len(crit) + len(warn)})")
        print("[4] Filter by file text  [5] Filter by tool  [q] Quit")
        try:
            choice = input("Choose: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if choice in ("q", "quit", "exit"):
            return
        if choice == "1":
            lines = [ln for _, _, ln in crit] or ["No critical issues found."]
            _show_lines(lines)
        elif choice == "2":
            lines = [ln for _, _, ln in crit]
            lines.append("-- import-path warnings --")
            lines += [ln for t, k, ln in warn if k == "import-warning"]
            _show_lines(lines or ["Nothing to show."])
        elif choice == "3":
            lines = [ln for _, _, ln in crit]
            lines.append("-- warnings (hygiene + import-path) --")
            lines += [ln for _, _, ln in warn]
            _show_lines(lines or ["Nothing to show."])
        elif choice == "4":
            try:
                needle = input("File text (e.g. bank.py): ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                continue
            all_lines = [ln for _, _, ln in crit + warn]
            hits = [ln for ln in all_lines if needle.lower() in ln.lower()]
            _show_lines(hits or [f"No matches for {needle!r}."])
        elif choice == "5":
            try:
                tool = input("Tool (flake8/pylint/mypy): ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                continue
            hits = [ln for t, _, ln in crit + warn if t == tool]
            _show_lines(hits or [f"No matches for tool {tool!r}."])
        else:
            print("Unknown choice. Pick 1-5 or q.")


# ------------------------------------------------------------------ CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description="Scan the project (flake8+pylint+mypy) and read results.")
    ap.add_argument("--basic", action="store_true",
                    help="just write scan_reports/*.txt, no interactive reader")
    ap.add_argument("--view", nargs="?", const="latest", default=None,
                    help="open reader on latest (or given) report without rescanning")
    args = ap.parse_args(argv)

    if args.view is not None:
        target = latest_report() if args.view == "latest" else Path(args.view)
        if target is None or not Path(target).exists():
            print(f"No report found at {args.view!r}. Run `python test_all.py --basic` first.")
            return 1
        launch_reader(parse_report_file(target))
        return 0

    data = run_scan()
    n_crit = len(data["flake"]) + len(data["pylint_err"]) + len(data["mypy_err"])
    n_warn = len(data["pylint_imp"]) + len(data["mypy_hyg"]) + len(data["mypy_imp"])
    print(f"Scan complete! Report saved to: {data['path']}")
    print(f"  critical: {n_crit} | warnings: {n_warn} "
          f"(flake8={len(data['flake'])}, pylint={len(data['pylint_err'])}+{len(data['pylint_imp'])}w, "
          f"mypy={len(data['mypy_err'])}+{len(data['mypy_hyg'])}h+{len(data['mypy_imp'])}w)")

    if args.basic:
        return 0
    launch_reader(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
