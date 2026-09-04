from core.systems.orchestrator import warning



current_player_id = 1 # Temporary.


# Internal storage for player positions: {player_id: (x, y, z)}
_players = {1: (0, 0, 0)}

# Backwards-compatible module-level variable for player 1
player_pos1 = _players[1]


def _sync_player_pos1():
    """Keep the legacy player_pos1 variable in sync with _players[1]."""
    global player_pos1
    player_pos1 = _players.get(1, (0, 0, 0))


try:
    from core.command_registry import command as _command
except ImportError:
    def _command(*a, **k):
        def _d(fn):
            return fn
        return _d


@_command("player.add", "Add a new player at pos [x,y,z]", category="dev")
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


@_command("player.move", "Update an existing player's position [x,y,z]", category="player")
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


@_command("player.get", "Get a player's position by ID", category="player")
def get_player_pos(player_id):
    """Return the player's position tuple, or None if not found (and log a warning)."""
    pos = _players.get(player_id)
    if pos is None:
        warning(f"Error: Specified Player ID {player_id} is not available.")
    return pos


@_command("player.remove", "Remove a player by ID", category="dev")
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

# ---- save/load provider (registry mirrors dev-console @command pattern) ----
def _save_players():
    """Return JSON-serializable player state (string keys -> list positions)."""
    return {str(pid): list(pos) for pid, pos in _players.items()}


def _load_players(state):
    """Restore player positions from save state."""
    if not isinstance(state, dict):
        warning(f"_load_players: expected dict, got {type(state).__name__}")
        return
    _players.clear()
    for key, pos in state.items():
        try:
            pid = int(key)
            if not (hasattr(pos, "__len__") and len(pos) == 3):
                warning(f"_load_players: invalid pos for player {pid}: {pos!r}")
                continue
            _players[pid] = tuple(pos)
        except Exception as e:
            warning(f"_load_players: failed to restore player '{key}': {e}")
    _sync_player_pos1()
    # Re-ensure inventories for restored players (best-effort)
    try:
        from core.systems.inventory.manager import ensure_inventory as _ei
        for pid in list(_players.keys()):
            try:
                _ei(pid)
            except Exception:
                pass
    except Exception:
        pass


try:
    from core.systems.save.registry import register_save_provider as _reg
    _reg("players", _save_players, _load_players)
except Exception:
    pass

__all__ = ["add_player", "update_player_pos", "get_player_pos", "remove_player", "player_pos1"]










def get_player_id():
    return current_player_id