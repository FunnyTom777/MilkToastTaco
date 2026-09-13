import importlib.metadata as importlib_metadata
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Self-bootstrap: make sure a fresh checkout with only Python installed can
# still run `python main.py` by auto-installing requirements.txt first.
#
# This block must stay stdlib-only (no rich/questionary imports here) because
# those third-party packages are exactly what we may need to install.
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
REQUIREMENTS_FILE = BASE_DIR / "requirements.txt"

# Used only if requirements.txt is missing (e.g. partial download).
_FALLBACK_REQUIREMENTS = [
    "questionary==2.1.1",
    "rich==15.0.0",
    "pygame==2.6.1",
    "pywebview==6.2.1",
    "PyQt6==6.11.0",
    "panda3d==1.10.16",
    "dearpygui==2.3.1",
    "noise==1.2.2",
]


def _parse_requirement_lines(path: Path) -> list[str]:
    """Read requirements.txt and return clean requirement strings."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return list(_FALLBACK_REQUIREMENTS)
    reqs: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # Strip inline comments ("pkg==1.0  # comment").
        if " #" in line:
            line = line.split(" #", 1)[0].strip()
        if line:
            reqs.append(line)
    return reqs if reqs else list(_FALLBACK_REQUIREMENTS)


def _dist_name_and_pinned_version(req: str) -> tuple[str, str | None]:
    """Split 'name[extras]==1.2.3; marker' into ('name', '1.2.3')."""
    # Drop environment markers first.
    req = req.split(";", 1)[0].strip()
    # Drop extras: 'name[extra]==1.0' -> 'name==1.0'.
    req = re.sub(r"\[[^\]]*\]", "", req).strip()
    match = re.split(r"(==|===|>=|<=|~=|!=|>|<)", req, maxsplit=1)
    name = match[0].strip()
    pinned: str | None = None
    if len(match) == 3 and match[1] in ("==", "==="):
        pinned = match[2].strip().split(",")[0].strip().split()[0]
    return name, pinned


def _find_missing_requirements(reqs: list[str]) -> list[str]:
    """Return the subset of requirement strings whose dist is absent/wrong."""
    missing: list[str] = []
    for req in reqs:
        name, pinned = _dist_name_and_pinned_version(req)
        if not name:
            continue
        try:
            installed = importlib_metadata.version(name)
        except importlib_metadata.PackageNotFoundError:
            missing.append(req)
            continue
        except Exception:
            # If metadata lookup itself breaks, assume it needs installing.
            missing.append(req)
            continue
        if pinned and installed.strip() != pinned:
            missing.append(req)
    return missing


def ensure_requirements(auto_install: bool = True) -> bool:
    """Check requirements.txt; pip-install anything missing. Returns True if OK."""
    reqs = _parse_requirement_lines(REQUIREMENTS_FILE)
    missing = _find_missing_requirements(reqs)
    if not missing:
        return True

    print(f"[MTT] Missing {len(missing)} requirement(s):")
    for req in missing:
        print(f"[MTT]   - {req}")

    if not auto_install:
        print("[MTT] Auto-install disabled. Run:")
        print(f"[MTT]   {sys.executable} -m pip install -r {REQUIREMENTS_FILE}")
        return False

    if REQUIREMENTS_FILE.exists():
        cmd = [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)]
    else:
        print(f"[MTT] WARNING: {REQUIREMENTS_FILE} not found, installing fallback list.")
        cmd = [sys.executable, "-m", "pip", "install", *missing]

    print("[MTT] Installing missing requirements (this may take a few minutes)...")
    print(f"[MTT] Running: {' '.join(cmd)}")
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as exc:
        print(f"[MTT] ERROR: pip install failed with exit code {exc.returncode}.")
        print("[MTT] Try running manually:")
        print(f"[MTT]   {sys.executable} -m pip install -r {REQUIREMENTS_FILE}")
        return False
    except FileNotFoundError as exc:
        print(f"[MTT] ERROR: could not launch pip: {exc}")
        return False

    # Verify the install actually fixed everything.
    still_missing = _find_missing_requirements(reqs)
    if still_missing:
        print("[MTT] ERROR: still missing after install:")
        for req in still_missing:
            print(f"[MTT]   - {req}")
        return False
    print("[MTT] All requirements installed. Launching...")
    return True


def _deps_bootstrap() -> None:
    """Run before any third-party import. Honors MTT_SKIP_DEPS / --skip-deps."""
    if os.environ.get("MTT_SKIP_DEPS") == "1" or "--skip-deps" in sys.argv:
        return
    if "--check-deps" in sys.argv:
        reqs = _parse_requirement_lines(REQUIREMENTS_FILE)
        missing = _find_missing_requirements(reqs)
        if missing:
            print("[MTT] Missing requirements:")
            for req in missing:
                print(f"[MTT]   - {req}")
            sys.exit(1)
        print("[MTT] All requirements satisfied.")
        sys.exit(0)
    ok = ensure_requirements(auto_install=True)
    if not ok:
        sys.exit(1)


_deps_bootstrap()

try:
    import questionary
    from questionary import Choice
    from rich.align import Align
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.text import Text
except ImportError:
    # Most likely the bootstrap above was skipped or just installed packages
    # into a location that needs a fresh import. Try once more, then explain.
    print("[MTT] Launcher dependencies not importable, attempting install...")
    if not ensure_requirements(auto_install=True):
        sys.exit(1)
    import questionary
    from questionary import Choice
    from rich.align import Align
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.text import Text

console = Console()

BANNER = r"""
░▒█▀▄▀█░░▀░░█░░█░▄░░░▀▀█▀▀░▄▀▀▄░█▀▀▄░█▀▀░▀█▀░░░▀▀█▀▀░█▀▀▄░█▀▄░▄▀▀▄░░
░▒█▒█▒█░░█▀░█░░█▀▄░░░░▒█░░░█░░█░█▄▄█░▀▀▄░░█░░░░░▒█░░░█▄▄█░█░░░█░░█░░
░▒█░░▒█░▀▀▀░▀▀░▀░▀░░░░▒█░░░░▀▀░░▀░░▀░▀▀▀░░▀░░░░░▒█░░░▀░░▀░▀▀▀░░▀▀░░░
"""


def show_header():
    console.clear()
    console.print(Align.center(Text(BANNER, style="bold cyan")))
    console.print(
        Align.center(
            Panel.fit(
                "[bold yellow]Simulation Engine Control Panel[/bold yellow] [dim]| v2.4.0[/dim]",
                border_style="magenta",
            )
        )
    )
    console.print()


def launch_ascii_renderer():
    show_header()
    console.print(
        Panel(
            "[bold green]Booting ASCII Renderer Engine...[/bold green]",
            border_style="green",
        )
    )

    with console.status(
        "[bold green]Loading environment maps and shader buffers...", spinner="dots"
    ):
        time.sleep(0.6)

    console.print("[bold cyan]>>> Launching ASCII Renderer...[/bold cyan]")
    console.print(
        "[dim]Close the pygame window or press Esc to return to the launcher.[/dim]\n"
    )

    # Prefer subprocess so the pygame main loop + sys.exit() doesn't kill the launcher.
    # Falls back to direct import if subprocess fails (e.g. in embedded test harnesses).
    try:
        result = subprocess.run([sys.executable, "-m", "core.renderer.Ascii1.ascii"])
        if result.returncode == 0:
            console.print("[green]Renderer closed cleanly.[/green]")
        else:
            console.print(
                f"[yellow]Renderer exited with code {result.returncode}.[/yellow]"
            )
    except KeyboardInterrupt:
        console.print("\n[yellow]Renderer interrupted by user.[/yellow]")
    except Exception as exc:
        console.print(
            f"[red]Subprocess launch failed ({exc}), trying direct import...[/red]"
        )
        try:
            from core.renderer.Ascii1.ascii import main as ascii_main

            try:
                ascii_main()
            except SystemExit as se:
                # ascii.py calls sys.exit() on clean quit — treat 0/None as success
                code = se.code if se.code is not None else 0
                if code == 0:
                    console.print("[green]Renderer closed cleanly.[/green]")
                else:
                    console.print(f"[yellow]Renderer exited with code {code}.[/yellow]")
        except SystemExit:
            pass
        except Exception as exc2:
            console.print(f"[red]Failed to launch ASCII renderer: {exc2}[/red]")
            console.print(
                "[dim]Tip: run manually with: python -m core.renderer.Ascii1.ascii[/dim]"
            )

    console.print()
    Prompt.ask("[dim]Press Enter to return to main menu[/dim]", default="")


def launch_dashboard_v2():
    show_header()
    console.print(
        Panel(
            "[bold green]Booting Dashboard V2...[/bold green]",
            border_style="green",
        )
    )

    with console.status(
        "[bold green]Loading XMB themes and system debugger...", spinner="dots"
    ):
        time.sleep(0.6)

    console.print("[bold cyan]>>> Launching Dashboard V2...[/bold cyan]")
    console.print(
        "[dim]Close the Dashboard V2 window or press Esc to return to the launcher.[/dim]\n"
    )

    # Prefer subprocess so the pywebview main loop + sys.exit() doesn't kill the launcher.
    # Falls back to direct import if subprocess fails (e.g. in embedded test harnesses).
    try:
        result = subprocess.run(
            [sys.executable, "-m", "core.renderer.dashboard_v2.dashboard_v2"]
        )
        if result.returncode == 0:
            console.print("[green]Dashboard V2 closed cleanly.[/green]")
        else:
            console.print(
                f"[yellow]Dashboard V2 exited with code {result.returncode}.[/yellow]"
            )
    except KeyboardInterrupt:
        console.print("\n[yellow]Dashboard V2 interrupted by user.[/yellow]")
    except Exception as exc:
        console.print(
            f"[red]Subprocess launch failed ({exc}), trying direct import...[/red]"
        )
        try:
            from core.renderer.dashboard_v2.dashboard_v2 import run as dashboard_v2_run

            try:
                dashboard_v2_run()
            except SystemExit as se:
                # dashboard_v2.py calls sys.exit() on error — treat 0/None as success
                code = se.code if se.code is not None else 0
                if code == 0:
                    console.print("[green]Dashboard V2 closed cleanly.[/green]")
                else:
                    console.print(
                        f"[yellow]Dashboard V2 exited with code {code}.[/yellow]"
                    )
        except SystemExit:
            pass
        except Exception as exc2:
            console.print(f"[red]Failed to launch Dashboard V2: {exc2}[/red]")
            console.print(
                "[dim]Tip: run manually with: python -m core.renderer.dashboard_v2.dashboard_v2[/dim]"
            )

    console.print()
    Prompt.ask("[dim]Press Enter to return to main menu[/dim]", default="")


def launch_dashboard_v5():
    show_header()
    console.print(
        Panel(
            "[bold green]Booting Dashboard V5...[/bold green]",
            border_style="green",
        )
    )

    with console.status(
        "[bold green]Loading command registry and prompt...", spinner="dots"
    ):
        time.sleep(0.6)

    console.print("[bold cyan]>>> Launching Dashboard V5...[/bold cyan]")
    console.print(
        "[dim]Type 'exit' or 'launcher' (or Ctrl+C twice) to return to the launcher.[/dim]\n"
    )

    # Prefer subprocess so the Textual main loop + sys.exit() doesn't kill the launcher.
    # Falls back to direct import if subprocess fails (e.g. in embedded test harnesses).
    try:
        result = subprocess.run(
            [sys.executable, "-m", "core.renderer.dashboard_v5.dashboardv5"]
        )
        if result.returncode == 0:
            console.print("[green]Dashboard V5 closed cleanly.[/green]")
        else:
            console.print(
                f"[yellow]Dashboard V5 exited with code {result.returncode}.[/yellow]"
            )
    except KeyboardInterrupt:
        console.print("\n[yellow]Dashboard V5 interrupted by user.[/yellow]")
    except Exception as exc:
        console.print(
            f"[red]Subprocess launch failed ({exc}), trying direct import...[/red]"
        )
        try:
            from core.renderer.dashboard_v5.dashboardv5 import run as dashboard_v5_run

            try:
                dashboard_v5_run()
            except SystemExit as se:
                # dashboardv5.py calls sys.exit() on error — treat 0/None as success
                code = se.code if se.code is not None else 0
                if code == 0:
                    console.print("[green]Dashboard V5 closed cleanly.[/green]")
                else:
                    console.print(
                        f"[yellow]Dashboard V5 exited with code {code}.[/yellow]"
                    )
        except SystemExit:
            pass
        except Exception as exc2:
            console.print(f"[red]Failed to launch Dashboard V5: {exc2}[/red]")
            console.print(
                "[dim]Tip: run manually with: python -m core.renderer.dashboard_v5.dashboardv5[/dim]"
            )

    console.print()
    Prompt.ask("[dim]Press Enter to return to main menu[/dim]", default="")


def show_tips():
    show_header()

    tips = [
        "[bold cyan]Tip 1:[/bold cyan] Milk Toast Taco is currently ... not very playable... im working on it!",
        "[bold cyan]Tip 2:[/bold cyan] This should be a very helpful tip, but... its not. So just use your imagination.",
        "[bold cyan]Tip 3:[/bold cyan] Despite the name, neither dairy, bread, nor Mexican cuisine affects system performance.",
    ]

    for tip in tips:
        console.print(
            Panel(tip, border_style="blue", title="[bold white]Pro Tip[/bold white]")
        )
        time.sleep(0.3)

    console.print()
    Prompt.ask("[dim]Press Enter to return to main menu[/dim]", default="")


def main():
    while True:
        show_header()

        choice = questionary.select(
            "What would you like to do?",
            choices=[
                Choice("Launch ASCII renderer", value="ascii"),
                Choice("Launch Dashboard V2 (Soft Deprecated)", value="dashboard_v2"),
                Choice("Launch Dashboard V5 (Command Prompt)", value="dashboard_v5"),
                Choice("Tips", value="tips"),
                Choice("Quit", value="quit"),
            ],
            style=questionary.Style(
                [
                    ("qmark", "fg:cyan bold"),
                    ("question", "bold white"),
                    ("answer", "fg:green bold"),
                    ("pointer", "fg:magenta bold"),
                    ("highlighted", "fg:cyan bold"),
                    ("selected", "fg:green bold"),  # <-- Changed 'active' to 'bold'
                ]
            ),
        ).ask()

        if choice == "ascii":
            launch_ascii_renderer()
        elif choice == "dashboard_v2":
            launch_dashboard_v2()
        elif choice == "dashboard_v5":
            launch_dashboard_v5()
        elif choice == "tips":
            show_tips()
        elif choice == "quit" or choice is None:
            console.clear()
            console.print(
                "[bold magenta]Shutting down Milk Toast Taco launcher. Goodbye![/bold magenta]"
            )
            sys.exit()


if __name__ == "__main__":
    main()
