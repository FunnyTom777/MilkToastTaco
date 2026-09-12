# Manages current game state.
# Central home for per-player money + wanted_level. Plain dict + functions only.
from __future__ import annotations

try:
    from core.systems.orchestrator import warning
except ImportError:
    def warning(m): print(m)

DEFAULT_MONEY = 0
DEFAULT_WANTED = 0

# Store all players in a dictionary
players = {
    1: {"money": DEFAULT_MONEY, "wanted_level": DEFAULT_WANTED},
    2: {"money": DEFAULT_MONEY, "wanted_level": DEFAULT_WANTED},
    3: {"money": DEFAULT_MONEY, "wanted_level": DEFAULT_WANTED},
    4: {"money": DEFAULT_MONEY, "wanted_level": DEFAULT_WANTED},
    5: {"money": DEFAULT_MONEY, "wanted_level": DEFAULT_WANTED},
    6: {"money": DEFAULT_MONEY, "wanted_level": DEFAULT_WANTED},
    7: {"money": DEFAULT_MONEY, "wanted_level": DEFAULT_WANTED},
}


def _ensure(player_id):
    """Make sure a player entry exists, return it."""
    pid = int(player_id)
    if pid not in players:
        players[pid] = {"money": float(DEFAULT_MONEY), "wanted_level": DEFAULT_WANTED}
    return players[pid]


def update_player_money(player_id, value):
    """Set the player's money value. Returns the new balance."""
    data = _ensure(player_id)
    data["money"] = float(value)
    return float(data["money"])


def update_player_wanted_level(player_id, value):
    """Set wanted level (0-10). Returns the new level."""
    data = _ensure(player_id)
    data["wanted_level"] = int(value)
    return int(data["wanted_level"])


def get_player_stat(player_id, stat):
    """Return one stat for a player, or None if missing."""
    try:
        pid = int(player_id)
    except (TypeError, ValueError):
        warning("Provided Player ID is not recognized. Please try again. Action aborted.")
        return None
    if pid not in players:
        warning("Provided Player ID is not recognized. Please try again. Action aborted.")
        return None
    if stat not in players[pid]:
        warning(f"Stat '{stat}' does not exist for this player.")
        return None
    return players[pid][stat]


# --- Money API (wallet delegates here) ---

def get_balance(player_id) -> float:
    return float(_ensure(player_id)["money"])


def set_balance(player_id, amount: float) -> float:
    if amount < 0:
        raise ValueError("amount must be >= 0")
    return update_player_money(player_id, float(amount))


def add_funds(player_id, amount: float) -> float:
    if amount <= 0:
        raise ValueError("amount must be > 0")
    data = _ensure(player_id)
    data["money"] = float(data["money"] + amount)
    return float(data["money"])


def deduct_funds(player_id, amount: float) -> bool:
    """Deduct if enough funds. Returns True on success, False if insufficient."""
    if amount <= 0:
        raise ValueError("amount must be > 0")
    data = _ensure(player_id)
    if float(data["money"]) + 1e-9 < amount:
        return False
    data["money"] = float(data["money"] - amount)
    return True


def can_afford(player_id, amount: float) -> bool:
    return get_balance(player_id) + 1e-9 >= amount


# --- Save / Load (saves everything state manages) ---

def _save_state():
    return {
        str(pid): {"money": float(d.get("money", 0)), "wanted_level": int(d.get("wanted_level", 0))}
        for pid, d in players.items()
    }


def _load_state(state):
    if not isinstance(state, dict):
        warning(f"_load_state: expected dict, got {type(state).__name__}")
        return
    players.clear()
    for k, v in state.items():
        try:
            pid = int(k)
            if isinstance(v, dict):
                players[pid] = {
                    "money": float(v.get("money", DEFAULT_MONEY)),
                    "wanted_level": int(v.get("wanted_level", DEFAULT_WANTED)),
                }
            else:
                # tolerate legacy plain-number entry: treat as money
                players[pid] = {"money": float(v), "wanted_level": DEFAULT_WANTED}
        except Exception as e:
            warning(f"_load_state for '{k}': {e}")


def _save_money_slice():
    # compat for HUD / old saves that expect wallet/economy keys
    return {str(pid): float(d.get("money", 0)) for pid, d in players.items()}


def _load_money_slice(state):
    if not isinstance(state, dict):
        warning(f"_load_money_slice: expected dict, got {type(state).__name__}")
        return
    for k, v in state.items():
        try:
            pid = int(k)
            data = _ensure(pid)
            if isinstance(v, dict) and "money" in v:
                data["money"] = float(v["money"])
            else:
                data["money"] = float(v)
        except Exception as e:
            warning(f"_load_money_slice for '{k}': {e}")


try:
    from core.systems.save.registry import register_save_provider as _reg
    _reg("state", _save_state, _load_state)
    _reg("wallet", _save_money_slice, _load_money_slice)
    _reg("economy", _save_money_slice, _load_money_slice)  # alias for HUD
except Exception:
    pass
