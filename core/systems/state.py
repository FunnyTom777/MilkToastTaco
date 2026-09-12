# Manages current game state.
from orchestrator import warning

# Store all players in a dictionary
players = {
    1: {"money": 0, "wanted_level": 0},
    2: {"money": 0, "wanted_level": 0},
    3: {"money": 0, "wanted_level": 0},
    4: {"money": 0, "wanted_level": 0},
    5: {"money": 0, "wanted_level": 0},
    6: {"money": 0, "wanted_level": 0},
    7: {"money": 0, "wanted_level": 0},
}


def update_player_money(player_id, value):
    """
    Updates the specified players (player_id) money value.
    """
    if player_id in players:
        players[player_id]["money"] = value
    else:
        warning(
            "Provided Player ID is not recognized. Please try again. Action aborted."
        )


def update_player_wanted_level(player_id, value):
    """
    Updates the specified players (player_id) wanted level.
    Can be anywhere from 0 to 10.
    """
    if player_id in players:
        players[player_id]["wanted_level"] = value
    else:
        warning(
            "Provided Player ID is not recognized. Please try again. Action aborted."
        )


def get_player_stat(player_id, stat):
    """
    Returns the specified stat for a player.
    """
    if player_id not in players:
        warning(
            "Provided Player ID is not recognized. Please try again. Action aborted."
        )
        return None

    if stat not in players[player_id]:
        warning(f"Stat '{stat}' does not exist for this player.")
        return None

    return players[player_id][stat]
