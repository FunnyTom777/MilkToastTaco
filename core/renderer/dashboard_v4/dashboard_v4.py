"""
MTT Dashboard V4 — Native Desktop Dashboard Hub (PyQt6).

Communicates with MTT systems exclusively through the Command Bridge
(core.renderer.bridge.CommandBridgeMixin / core.command_registry).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.renderer.bridge import CommandBridgeMixin


class DashboardV4API(CommandBridgeMixin):
    """Bridge API for Dashboard V4. Decoupled from game systems."""

    def __init__(self):
        self.game_state = {
            "started": False,
            "version": "V4",
            "frontend": "PyQt6",
        }

    # -- settings (synced with xmbsettings.xml) -----------------------------
    def get_xmb_settings(self) -> Dict[str, Any]:
        try:
            from core.renderer.main_menu.xmb_settings import load_settings
            return {"status": "success", "settings": load_settings()}
        except Exception as e:
            return {"status": "error", "message": str(e), "settings": {"theme": "default", "fullscreen": False}}

    def set_fullscreen(self, enabled: bool) -> Dict[str, Any]:
        try:
            from core.renderer.main_menu.xmb_settings import load_settings, save_settings
            s = load_settings()
            s["fullscreen"] = bool(enabled)
            save_settings(s)
            return {"status": "success", "settings": s}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def set_theme(self, theme: str) -> Dict[str, Any]:
        try:
            from core.renderer.main_menu.xmb_settings import load_settings, save_settings, VALID_THEMES
            if theme not in VALID_THEMES:
                return {"status": "error", "message": f"Unknown theme '{theme}'"}
            s = load_settings()
            s["theme"] = theme
            save_settings(s)
            return {"status": "success", "settings": s}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # -- save manager bridge ------------------------------------------------
    def list_saves(self) -> Dict[str, Any]:
        try:
            from core.systems.save.manager import list_saves as _list
            return {"status": "success", "saves": _list()}
        except Exception as e:
            return {"status": "error", "message": str(e), "saves": []}

    def load_game(self, save_name: str) -> Dict[str, Any]:
        try:
            from core.systems.save.manager import load_game as _load
            if not save_name or not str(save_name).strip():
                return {"status": "error", "message": "save_name required"}
            ok = _load(str(save_name).strip())
            if not ok:
                return {"status": "error", "message": f"Save '{save_name}' failed to load"}
            return {"status": "success", "save": save_name, "message": f"Loaded {save_name}.xml"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def save_game(self, save_name: str) -> Dict[str, Any]:
        try:
            from core.systems.save.manager import save_game as _save
            if not save_name or not str(save_name).strip():
                return {"status": "error", "message": "save_name required"}
            path = _save(str(save_name).strip())
            return {"status": "success", "save": save_name, "path": path, "message": f"Saved {save_name}.xml"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_game_status(self) -> Dict[str, Any]:
        return {"status": "success", "game_state": self.game_state}


def run(
    debug: bool = False,
    width: int = 1280,
    height: int = 840,
    fullscreen: Optional[bool] = None,
    theme: Optional[str] = None,
    player_id: int = 1,
):
    """Initialize and run the PyQt6 Dashboard V4 Application."""
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        print(
            "Error: PyQt6 is not installed.\n"
            "Install it with: pip install PyQt6",
            file=sys.stderr
        )
        sys.exit(1)

    from core.renderer.dashboard_v4.ui.main_window import DashboardV4MainWindow

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    api = DashboardV4API()

    # Load settings for defaults
    settings = api.get_xmb_settings().get("settings", {})
    resolved_theme = theme or settings.get("theme", "default")
    resolved_fullscreen = fullscreen if fullscreen is not None else bool(settings.get("fullscreen", False))

    window = DashboardV4MainWindow(
        bridge=api,
        player_id=player_id,
        initial_theme=resolved_theme
    )
    window.resize(width, height)

    if resolved_fullscreen:
        window.showFullScreen()
    else:
        window.show()

    return app.exec()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="MTT Dashboard V4 (PyQt6)")
    p.add_argument("--debug", action="store_true", help="Enable debug mode")
    p.add_argument("--width", type=int, default=1280, help="Window width")
    p.add_argument("--height", type=int, default=840, help="Window height")
    p.add_argument("--fullscreen", action="store_true", help="Fullscreen mode")
    p.add_argument("--theme", type=str, default=None, help="Theme override")
    p.add_argument("--player-id", type=int, default=1, help="Active player ID")
    args = p.parse_args()

    run(
        debug=args.debug,
        width=args.width,
        height=args.height,
        fullscreen=True if args.fullscreen else None,
        theme=args.theme,
        player_id=args.player_id,
    )
