"""
XMB Dashboard API for Milk Toast Taco.

This module provides the Python API that the XMB HTML dashboard can call
via JavaScript using pywebview.api.* methods.
"""

from functools import wraps
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any


# Path to the XMB HTML dashboard located in static/ next to this module
# After refactor moved from project-root /static/ to core/renderer/main_menu/static/
STATIC_DIR = Path(__file__).parent / "static"
XMB_HTML_PATH = STATIC_DIR / "milk_toast_taco_xmb.html"


def get_xmb_html_path() -> str:
    """Get absolute path to the XMB HTML dashboard.

    Returns:
        str: Absolute path to milk_toast_taco_xmb.html
    """
    return str(XMB_HTML_PATH.resolve())


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
        category_id: Unique identifier for the category (e.g., "game_modes", "options")
        category_title: Display title for the category (e.g., "Game Modes", "Options")
        category_icon: Font Awesome icon class (e.g., "fa-gamepad", "fa-cog")
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
            "mode": None,
            "current_player": None,
            "game_data": {},
        }

    # --- Game Modes -------------------------------------------------

    @menu_option("game_modes", "Game Modes", "fa-gamepad", "Play Career Mode",
                 "Start a new or continue an existing Career Mode save. Build a reputation, "
                 "own property, and grow across industries over time.")
    def play_career_mode(self):
        """Start Career Mode.
        
        Returns:
            dict: Status message with game initialization info
        """
        self.game_state["started"] = True
        self.game_state["mode"] = "career"
        return {
            "status": "success",
            "message": "Career Mode started",
            "game_state": self.game_state,
        }

    @menu_option("game_modes", "Game Modes", "fa-gamepad", "Play Sandbox Mode",
                 "Jump into a free-play world with no objectives. Spawn vehicles, tune the "
                 "economy, and build without restriction.")
    def play_sandbox_mode(self):
        """Start Sandbox Mode.
        
        Returns:
            dict: Status message with game initialization info
        """
        self.game_state["started"] = True
        self.game_state["mode"] = "sandbox"
        return {
            "status": "success",
            "message": "Sandbox Mode started",
            "game_state": self.game_state,
        }

    @menu_option("game_modes", "Game Modes", "fa-gamepad", "View Military Campaigns",
                 "Browse historical and modern combat campaigns, from WWI dogfights to "
                 "network-centric modern warfare, and launch a mission.")
    def view_military_campaigns(self):
        """Open the Military Campaigns browser.
        
        Returns:
            dict: Status message confirming the campaign list was opened
        """
        return {
            "status": "success",
            "message": "Military campaign list opened",
        }

    # --- Options ------------------------------------------------------

    @menu_option("options", "Options", "fa-cog", "Mod Browser",
                 "Browse, enable, and configure installed mods. All mod data is YAML/CSV "
                 "driven, no compilation required.")
    def open_mod_browser(self):
        """Open the Mod Browser.
        
        Returns:
            dict: Status message confirming the mod browser was opened
        """
        return {
            "status": "success",
            "message": "Mod Browser opened",
        }

    @menu_option("options", "Options", "fa-cog", "Game Options",
                 "Adjust display, audio, controls, and multiplayer settings.")
    def open_game_options(self):
        """Open Game Options.
        
        Returns:
            dict: Status message confirming game options were opened
        """
        return {
            "status": "success",
            "message": "Game Options opened",
        }

    # --- XMB Options ----------------------------------------------------

    @menu_option("xmb_options", "XMB Options", "fa-sliders", "Display Settings",
                 "Configure fullscreen and display preferences for the XMB.")
    def open_xmb_display_settings(self):
        """Open XMB display settings (fullscreen etc)."""
        return {"status": "success", "message": "XMB display settings opened"}

    @menu_option("xmb_options", "XMB Options", "fa-sliders", "Theme Settings",
                 "Change the XMB visual theme — colors, waves, and accents.")
    def open_xmb_theme_settings(self):
        """Open XMB theme settings."""
        return {"status": "success", "message": "XMB theme settings opened"}

    # --- Misc -----------------------------------------------------------

    @menu_option("misc", "Misc", "fa-ellipsis-h", "Launch MTT Dashboard",
                 "Open the Milk Toast Taco developer dashboard (terminal/web).")
    def launch_dashboard(self):
        """Launch dashboard placeholder."""
        return {
            "status": "info",
            "message": "Dashboard launch not implemented yet",
        }

    @menu_option("misc", "Misc", "fa-ellipsis-h", "Quit",
                 "Save progress and return to desktop.")
    def quit_game(self):
        """Quit the game gracefully - actually closes pywebview window."""
        self.game_state["started"] = False
        try:
            import webview
            # Destroy all windows - closes the app
            if webview.windows:
                for w in list(webview.windows):
                    try:
                        w.destroy()
                    except Exception:
                        pass
            else:
                # Fallback: try to destroy via API
                pass
        except Exception:
            pass
        return {
            "status": "success",
            "message": "Game quit",
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

    # --- XMB Settings (fullscreen + theme) --------------------------------

    def get_xmb_settings(self):
        """Get current XMB settings (fullscreen, theme)."""
        from core.renderer.main_menu.xmb_settings import load_settings
        settings = load_settings()
        return {"status": "success", "settings": settings}

    def set_fullscreen(self, enabled: bool):
        """Set fullscreen preference and apply to window if possible."""
        from core.renderer.main_menu.xmb_settings import load_settings, save_settings
        settings = load_settings()
        settings["fullscreen"] = bool(enabled)
        save_settings(settings)
        # Try to apply live to window
        try:
            import webview
            if webview.windows:
                w = webview.windows[0]
                # pywebview: toggle_fullscreen vs fullscreen property
                if hasattr(w, "toggle_fullscreen"):
                    # Only toggle if needed
                    is_fs = getattr(w, "fullscreen", False)
                    if bool(is_fs) != bool(enabled):
                        w.toggle_fullscreen()
                elif hasattr(w, "fullscreen"):
                    w.fullscreen = bool(enabled)
                elif hasattr(w, "maximize"):
                    if enabled:
                        w.maximize()
        except Exception:
            pass
        return {"status": "success", "settings": settings}

    def set_theme(self, theme: str):
        """Set XMB theme."""
        from core.renderer.main_menu.xmb_settings import load_settings, save_settings, VALID_THEMES
        if theme not in VALID_THEMES:
            return {"status": "error", "message": f"Unknown theme '{theme}'"}
        settings = load_settings()
        settings["theme"] = theme
        save_settings(settings)
        return {"status": "success", "settings": settings}

    def get_available_themes(self):
        """Return available themes."""
        from core.renderer.main_menu.xmb_settings import THEMES
        return {"status": "success", "themes": THEMES}

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