import subprocess
import sys
import time

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
