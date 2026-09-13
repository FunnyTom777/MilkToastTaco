try:
    from core.systems.state import get_player_stat
except ImportError:
    from state import get_player_stat


from orchestrator import offense_severity


def player_wanted_check(player_id):
    """
    Returns the players current wanted level.
    """
    return get_player_stat(player_id, "wanted_level")


def update_player_wanted_level(offense_name):
    severity = offense_severity(offense_name)
