import os

from rich import print

os.system("cls" if os.name == "nt" else "clear")

# data
current_version = "v0.1.0"
new_update_avalible = True


print("[bold white]Welcome to Milk Toast Taco!")
print(f"[green]{current_version}")
print(" ")


def install_new_update():
    pass


def new_update():
    if new_update_avalible == True:
        print("[bold yellow]New update available!")
        print(f"[green]Update {current_version} is now available.")
        input1 = input("Would you like to install it now? [y/n]")
        if input1 == "y":
            os.system("cls" if os.name == "nt" else "clear")
            print("[bold green]Installing...")
            install_new_update()

        elif input1 == "n":
            pass
        else:
            print("[bold red]Invalid input.")
            new_update()


new_update()
