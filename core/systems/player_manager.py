from core.systems.orchestrator import warning

# Internal storage for player positions: {player_id: (x, y, z)}
_players = {1: (0, 0, 0)}

# Backwards-compatible module-level variable for player 1
player_pos1 = _players[1]


def _sync_player_pos1():
    """Keep the legacy player_pos1 variable in sync with _players[1]."""
    global player_pos1
    player_pos1 = _players.get(1, (0, 0, 0))


def add_player(player_id, pos):
    """Add a new player with position `pos` (sequence of 3 numbers).

    Raises ValueError on invalid input or if the player already exists.
    Returns True on success.
    """
    if not isinstance(player_id, int):
        raise ValueError("player_id must be an int")
    if player_id in _players:
        raise ValueError(f"Player {player_id} already exists")
    if not (hasattr(pos, '__len__') and len(pos) == 3):
        raise ValueError("pos must be a sequence of length 3")

    _players[player_id] = tuple(pos)
    _sync_player_pos1()
    # Auto-create inventory for new player (lazy import to avoid cycles)
    try:
        from core.systems.inventory.manager import ensure_inventory
        ensure_inventory(player_id)
    except Exception:
        pass
    return True


def update_player_pos(player_id, pos):
    """Update an existing player's position.

    Raises ValueError if the player does not exist or pos is invalid.
    Returns True on success.
    """
    if player_id not in _players:
        raise ValueError(f"Player {player_id} does not exist")
    if not (hasattr(pos, '__len__') and len(pos) == 3):
        raise ValueError("pos must be a sequence of length 3")

    _players[player_id] = tuple(pos)
    _sync_player_pos1()
    return True


def get_player_pos(player_id):
    """Return the player's position tuple, or None if not found (and log a warning)."""
    pos = _players.get(player_id)
    if pos is None:
        warning(f"Error: Specified Player ID {player_id} is not available.")
    return pos


def remove_player(player_id):
    """Remove a player from the manager.

    Raises ValueError if the player does not exist. Returns True on success.
    """
    if player_id not in _players:
        raise ValueError(f"Player {player_id} does not exist")
    del _players[player_id]
    _sync_player_pos1()
    # Clean up inventory as well
    try:
        from core.systems.inventory.manager import remove_inventory
        remove_inventory(player_id)
    except Exception:
        pass
    return True


# Ensure initial player has an inventory (best-effort, ignore if inventory not yet importable)
try:
    from core.systems.inventory.manager import ensure_inventory as _ensure_inv
    _ensure_inv(1)
except Exception:
    pass

__all__ = ["add_player", "update_player_pos", "get_player_pos", "remove_player", "player_pos1"]