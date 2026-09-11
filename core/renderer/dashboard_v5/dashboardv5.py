import os
import subprocess
import sys

import questionary
from rich import print


def open_commands():
    from pathlib import Path

    prompt_path = Path(__file__).resolve().parent / "systems" / "command_prompt.py"
    if not prompt_path.is_file():
        print(f"[red]Command prompt not found at {prompt_path}[/red]")
        return
    try:
        # cwd=project root so `core.*` imports resolve even if V5 was
        # launched from another directory. Stdio is inherited so the
        # interactive prompt works; a nonzero exit is reported instead
        # of silently returning to nothing.
        result = subprocess.run(
            [sys.executable, str(prompt_path)],
            cwd=str(Path(__file__).resolve().parents[3]),
        )
        if result.returncode != 0:
            print(
                f"[yellow]Command prompt exited with code {result.returncode}. "
                "Try running it directly: "
                "python core/renderer/dashboard_v5/systems/command_prompt.py[/yellow]"
            )
    except Exception as e:
        print(f"[red]Could not launch command prompt: {e}[/red]")


logo = """[green]
░▒█▀▄▀█░░▀░░█░░█░▄░░░▀▀█▀▀░▄▀▀▄░█▀▀▄░█▀▀░▀█▀░░░▀▀█▀▀░█▀▀▄░█▀▄░▄▀▀▄░░
░▒█▒█▒█░░█▀░█░░█▀▄░░░░▒█░░░█░░█░█▄▄█░▀▀▄░░█░░░░░▒█░░░█▄▄█░█░░░█░░█░░
░▒█░░▒█░▀▀▀░▀▀░▀░▀░░░░▒█░░░░▀▀░░▀░░▀░▀▀▀░░▀░░░░░▒█░░░▀░░▀░▀▀▀░░▀▀░░░
"""


def main() -> None:
    os.system("cls" if os.name == "nt" else "clear")
    print(logo)
    print("[green bold]Welcome to Milk Toast Taco! (Dashboard V5 - Version 0.1)")

    while True:
        option = questionary.select(
            "What do you want to do?",
            choices=[
                "Play Career Mode",
                "Play Sandbox Mode",
                "Play Military Mode",
                "Settings",
                "Other",
                "Quit",
            ],
        ).ask()

        if option == "Play Career Mode":
            pass
        elif option == "Play Sandbox Mode":
            pass
        elif option == "Play Military Mode":
            pass
        elif option == "Settings":
            pass
        elif option == "Other":
            open_commands()
            # loop back to the menu instead of exiting
        elif option == "Quit" or option is None:
            print("[dim]Bye![/dim]")
            break
        else:
            print("[red]Invalid Option!")


if __name__ == "__main__":
    main()
