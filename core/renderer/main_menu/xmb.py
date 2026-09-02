"""
XMB Dashboard API for Milk Toast Taco.

This module provides the Python API that the XMB HTML dashboard can call
via JavaScript using pywebview.api.* methods.
"""

from functools import wraps
from collections import defaultdict
from typing import Dict, List, Any


# Global registry to store menu options
_menu_registry: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
    "title": "",
    "icon": "",
    "items": []
})


def menu_option(category_id: str, category_title: str = "", category_icon: str = "", 
                item_name: str = "", description: str = ""):
    """Decorator to register a menu option for a category.
    
    Args:
        category_id: Unique identifier for the category (e.g., "overview", "settings")
        category_title: Display title for the category (e.g., "Overview", "Settings")
        category_icon: Font Awesome icon class (e.g., "fa-cog", "fa-book")
        item_name: Display name for the menu item
        description: Description text for the menu item
    """
    def decorator(func):
        # Register category metadata if not already registered
        if not _menu_registry[category_id]["title"]:
            _menu_registry[category_id]["title"] = category_title
            _menu_registry[category_id]["icon"] = category_icon
        
        # Add item to the category
        _menu_registry[category_id]["items"].append({
            "name": item_name,
            "desc": description,
            "_callback": func.__name__
        })
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


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

    @menu_option("overview", "Overview", "fa-book", "Start Game", 
                 "Initialize and start a new game session.")
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

    @menu_option("industries", "Industries", "fa-briefcase", "Load Player", 
                 "Load or create a player profile.")
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

    @menu_option("options", "Settings", "fa-cog", "Exit Game", 
                 "Return to desktop.")
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

    def get_menu_structure(self) -> List[Dict[str, Any]]:
        """Get the dynamically-built menu structure for the XMB interface.
        
        Returns:
            list: Menu structure organized by category, matching xmbData format
        """
        result = []
        
        # Convert the registry to the xmbData format
        for category_id, category_data in _menu_registry.items():
            category_entry = {
                "id": category_id,
                "title": category_data["title"],
                "icon": category_data["icon"],
                "items": category_data["items"]
            }
            result.append(category_entry)
        
        return result
