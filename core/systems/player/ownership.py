from core.command_registry import command

try:
    from core.systems.orchestrator import thisdoesnothing
except ImportError:
    try:
        from orchestrator import thisdoesnothing
    except ImportError:
        def thisdoesnothing(*a, **k):  # fallback so autodiscover never fails on import
            pass
# Manages everything the player owns (Add new items, manage existing items, remove items, etc)






@command("ownership.add", "Adds a new item to the players ownership list", category="player")
def add_new_item(player_id):
    # Adds a new item to the players ownership list
    thisdoesnothing()


@command("ownership.remove", "Removes a item from the Players Ownership List.", category="player")
def remove_item(player_id):
    # Removes a item from the players ownership list
    thisdoesnothing()