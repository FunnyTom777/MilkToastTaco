import os
import sys

import questionary
from rich import print

logo = """
░▒█▀▄▀█░░▀░░█░░█░▄░░░▀▀█▀▀░▄▀▀▄░█▀▀▄░█▀▀░▀█▀░░░▀▀█▀▀░█▀▀▄░█▀▄░▄▀▀▄
░▒█▒█▒█░░█▀░█░░█▀▄░░░░▒█░░░█░░█░█▄▄█░▀▀▄░░█░░░░░▒█░░░█▄▄█░█░░░█░░█
░▒█░░▒█░▀▀▀░▀▀░▀░▀░░░░▒█░░░░▀▀░░▀░░▀░▀▀▀░░▀░░░░░▒█░░░▀░░▀░▀▀▀░░▀▀░
"""


os.system("cls" if os.name == "nt" else "clear")

print(f"[green]{logo}")
print("Welcome to Milk Toast Taco!")


option = questionary.select(
    "What would you like to do?",
    choices=["Play (ASCII renderer)", "Play (Dashboard V2)", "Exit"],
).ask()


if option == "Play (ASCII renderer)":
    pass
else:
    sys.exit()  # Exit the program
