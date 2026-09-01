from orchestrator import warning


# player 1:
player_pos1 = 0, 0, 0



def get_player_pos(player_id):
    if player_id == 1:
        return player_pos1
    else:
        return warning(f"Error: Specified Player ID is not avalible.")