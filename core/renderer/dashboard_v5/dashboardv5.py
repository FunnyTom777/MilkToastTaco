import os
import subprocess

import questionary
from rich import print


def open_commands():
    subprocess.run(["python", "systems/command_prompt.py"])


logo = """[green]
░▒█▀▄▀█░░▀░░█░░█░▄░░░▀▀█▀▀░▄▀▀▄░█▀▀▄░█▀▀░▀█▀░░░▀▀█▀▀░█▀▀▄░█▀▄░▄▀▀▄░░
░▒█▒█▒█░░█▀░█░░█▀▄░░░░▒█░░░█░░█░█▄▄█░▀▀▄░░█░░░░░▒█░░░█▄▄█░█░░░█░░█░░
░▒█░░▒█░▀▀▀░▀▀░▀░▀░░░░▒█░░░░▀▀░░▀░░▀░▀▀▀░░▀░░░░░▒█░░░▀░░▀░▀▀▀░░▀▀░░░
"""

os.system("cls" if os.name == "nt" else "clear")
print(logo)
print("[green bold]Welcome to Milk Toast Taco! (Dashboard V5 - Version 0.1)")

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
elif option == "Quit":
    exit()
else:
    print("[red]Invalid Option!")
