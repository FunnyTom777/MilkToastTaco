import sys
import time

import questionary
from questionary import Choice
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
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
        time.sleep(2)

    console.print(
        "[bold cyan]>>> ASCII Renderer actively running.[/bold cyan] (Press Enter to stop)\n"
    )
    Prompt.ask("[dim]Press Enter to return to main menu[/dim]", default="")


def launch_dashboard_v2():
    show_header()

    table = Table(
        title="[bold yellow]System Metrics & Telemetry[/bold yellow]",
        border_style="cyan",
    )
    table.add_column("Module", style="bold white")
    table.add_column("Status", justify="center")
    table.add_column("Load", justify="right")

    table.add_row("Core Sim Loop", "[green]ONLINE[/green]", "12%")
    table.add_row("Entity Manager", "[green]ONLINE[/green]", "44%")
    table.add_row("Spatial Indexer", "[yellow]OPTIMIZING[/yellow]", "78%")
    table.add_row("Memory Pool", "[green]STABLE[/green]", "1.2 GB")

    console.print(Align.center(table))
    console.print("\n[dim]Dashboard updating live...[/dim]\n")
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
                Choice("Launch Dashboard V2", value="dashboard"),
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
        elif choice == "dashboard":
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
