"""
XMB Dashboard API for Milk Toast Taco.

This module provides the Python API that the XMB HTML dashboard can call
via JavaScript using pywebview.api.* methods.
"""


class XMBDashboardAPI:
    """Python API exposed to the XMB dashboard JavaScript frontend.
    
    Methods in this class are callable from JavaScript via pywebview.api.method_name()
    """

    def __init__(self):
        """Initialize the XMB Dashboard API."""
        self.game_state = {
            "started": False,
            "current_player": None,
            "game_data": {},
        }

    def start_game(self):
        """Start a new game session.
        
        Returns:
            dict: Status message with game initialization info
        """
        self.game_state["started"] = True
        return {
            "status": "success",
            "message": "Game started",
            "game_state": self.game_state,
        }

    def load_player(self, player_name):
        """Load or create a player.
        
        Args:
            player_name (str): Name of the player to load
            
        Returns:
            dict: Player data or error message
        """
        self.game_state["current_player"] = player_name
        return {
            "status": "success",
            "message": f"Player '{player_name}' loaded",
            "player_name": player_name,
        }

    def get_game_status(self):
        """Get current game status.
        
        Returns:
            dict: Current game state
        """
        return {
            "status": "success",
            "game_state": self.game_state,
        }

    def quit_game(self):
        """Quit the game gracefully.
        
        Returns:
            dict: Confirmation message
        """
        self.game_state["started"] = False
        return {
            "status": "success",
            "message": "Game quit",
        }
