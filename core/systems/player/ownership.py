try:
    from core.command_registry import command as _command
except ImportError:
    def _command(*a, **k):
        def _d(fn):
            return fn
        return _d



from orchestrator import thisdoesnothing
# Manages everything the player owns (Add new items, manage existing items, remove items, etc)






@_command("ownership.add", "Adds a new item to the players ownership list", category="dev")
def add_new_item(player_id):
    # Adds a new item to the players ownership list
    thisdoesnothing()


@_command("ownership.remove", "renoves a item to the players ownership list", category="dev")
def remove_item(player_id):
    # Removes a item from the players ownership list
    thisdoesnothing()