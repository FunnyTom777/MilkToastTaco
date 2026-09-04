"""
MTT Dashboard V2 — Python backend for pywebview.

Mirrors the Dashboard and XMB architecture:
  - dashboard_v2.py  -> Python API exposed via pywebview JS bridge
  - static/dashboard_v2.html -> UI layer (Game System Debugger, XMB-themed)

Lives in its own folder: core/renderer/dashboard_v2/ with its own static/ folder.
Re-uses XMB settings (theme, fullscreen) from xmbsettings.xml so V2 looks
consistent with the XMB. Fullscreen is honoured the same way as other dashboards.

Spawned from XMB via XMBDashboardAPI.launch_dashboard_v2() and runnable
standalone:
    python -m core.renderer.dashboard_v2.dashboard_v2
    python -m core.renderer.dashboard_v2.dashboard_v2 --debug
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Paths --------------------------------------------------------------------
# core/renderer/dashboard_v2/dashboard_v2.py -> parents[3] -> MilkToastTaco/
PROJECT_ROOT = Path(__file__).resolve().parents[3]
STATIC_DIR = Path(__file__).parent / "static"
DASHBOARD_V2_HTML_PATH = STATIC_DIR / "dashboard_v2.html"

# Support both direct file execution and `python -m core.renderer.dashboard_v2.dashboard_v2`
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def get_dashboard_v2_html_path() -> str:
    """Absolute path to static/dashboard_v2.html."""
    return str(DASHBOARD_V2_HTML_PATH.resolve())


# ---------------------------------------------------------------------------
# Dashboard V2 API — exposed to JS via pywebview.api.*
# ---------------------------------------------------------------------------

class DashboardV2API:
    """Python API for the MTT Dashboard V2 frontend (pywebview bridge)."""

    def __init__(self):
        self.game_state = {
            "started": False,
            "mode": "debug",
        }
        # in-memory save editing: mirrors dashboard.py caching
        self._current_save: Optional[str] = None
        self._current_data: Optional[Dict[str, Any]] = None

    # -- settings (reuse XMB settings) -------------------------------------

    def get_xmb_settings(self):
        from core.renderer.main_menu.xmb_settings import load_settings
        return {"status": "success", "settings": load_settings()}

    def set_fullscreen(self, enabled: bool):
        from core.renderer.main_menu.xmb_settings import load_settings, save_settings
        s = load_settings()
        s["fullscreen"] = bool(enabled)
        save_settings(s)
        try:
            import webview
            if webview.windows:
                w = webview.windows[0]
                if hasattr(w, "toggle_fullscreen"):
                    is_fs = getattr(w, "fullscreen", False)
                    if bool(is_fs) != bool(enabled):
                        w.toggle_fullscreen()
                elif hasattr(w, "fullscreen"):
                    w.fullscreen = bool(enabled)
        except Exception:
            pass
        return {"status": "success", "settings": s}

    def set_theme(self, theme: str):
        from core.renderer.main_menu.xmb_settings import load_settings, save_settings, VALID_THEMES
        if theme not in VALID_THEMES:
            return {"status": "error", "message": f"Unknown theme '{theme}'"}
        s = load_settings()
        s["theme"] = theme
        save_settings(s)
        return {"status": "success", "settings": s}

    def get_available_themes(self):
        from core.renderer.main_menu.xmb_settings import THEMES
        return {"status": "success", "themes": THEMES}

    # -- saves / state (delegate to save manager, read-only HUD) -----------

    def list_saves(self):
        try:
            from core.systems.save.manager import list_saves as _list
            saves = _list()
            return {"status": "success", "saves": saves}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_saves(self):
        return self.list_saves()

    def load_save(self, save_name: str):
        try:
            from core.xml_loader import load_xml_file
            from core.systems.save.manager import _resolve_save_dir, _sanitize_filename
            from core.systems.save.xml_codec import element_to_value

            save_dir = _resolve_save_dir()
            fname = f"{_sanitize_filename(save_name)}.xml"
            fpath = save_dir / fname
            root = load_xml_file(str(fpath), strict=False)
            if root is None:
                return {"status": "error", "message": f"Save '{save_name}' not found or corrupt"}

            systems_el = root.find("systems")
            data: Dict[str, Any] = {}
            if systems_el is not None:
                for sys_el in systems_el.findall("system"):
                    key = sys_el.get("key", "")
                    try:
                        data[key] = element_to_value(sys_el)
                    except Exception as e:
                        data[key] = {"_error": str(e)}

            meta = {
                "name": root.get("name", save_name),
                "version": root.get("version"),
                "saved_at": root.get("saved_at"),
            }
            self._current_save = save_name
            self._current_data = {"meta": meta, "systems": data}
            return {"status": "success", "save": save_name, "meta": meta, "systems": data}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_state(self, save_name: Optional[str] = None):
        """Bridge for dashboard_v2.html to pull structured MTT state (HUD)."""
        try:
            from core.renderer.main_menu.xmb_settings import load_settings
            xmb_settings = load_settings()
        except Exception:
            xmb_settings = {"fullscreen": False, "theme": "default"}

        try:
            from core.systems.save.manager import list_saves as _list
            saves = _list()
        except Exception:
            saves = []

        systems: Dict[str, Any] = {}
        meta: Dict[str, Any] = {}
        current = self._current_save

        if save_name is not None:
            res = self.load_save(save_name)
            if res.get("status") == "success":
                systems = res.get("systems", {})
                meta = res.get("meta", {})
                current = save_name
            else:
                return {"status": "error", "message": res.get("message", "load failed"), "saves": saves, "xmb_settings": xmb_settings}
        elif self._current_data and "systems" in self._current_data:
            systems = self._current_data.get("systems", {})
            meta = self._current_data.get("meta", {})
        else:
            try:
                from core.systems.save.registry import get_providers
                for key, (save_fn, _) in get_providers().items():
                    try:
                        systems[key] = save_fn()
                    except Exception as e:
                        systems[key] = {"_error": str(e)}
            except Exception as e:
                systems = {"_error": str(e)}

        hud = self._build_hud_summary(systems)

        return {
            "status": "success",
            "saves": saves,
            "current_save": current,
            "meta": meta,
            "systems": systems,
            "hud": hud,
            "xmb_settings": xmb_settings,
        }

    # -- command registry bridge (decoupled, with dev filtering) ---------------
    # Player dashboard filters to "player"; V2 (debugger) shows all.
    def call_command(self, name: str, args=None):
        try:
            from core.command_registry import execute, ensure_commands_loaded

            ensure_commands_loaded()
            if args is None:
                return execute(name)
            if isinstance(args, dict):
                return execute(name, **args)
            if isinstance(args, (list, tuple)):
                return execute(name, *args)
            return execute(name, args)
        except Exception as e:
            return {"status": "error", "message": str(e), "command": name}

    def call_function(self, function_id, args=None):
        try:
            from core.command_registry import call_function as _cf, ensure_commands_loaded

            ensure_commands_loaded()
            if isinstance(function_id, (list, tuple)) and len(function_id) == 1:
                function_id = function_id[0]
            if args is None:
                return _cf(function_id)
            if isinstance(args, dict):
                return _cf(function_id, **args)
            if isinstance(args, (list, tuple)):
                return _cf(function_id, *args)
            return _cf(function_id, args)
        except Exception as e:
            return {"status": "error", "message": str(e), "command": str(function_id)}

    def list_commands(self, category: str | None = None):
        try:
            from core.command_registry import list_commands as _list, ensure_commands_loaded

            ensure_commands_loaded()
            cmds = _list(category)
            return {"status": "success", "commands": cmds, "category": category}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_commands(self, category: str | None = None):
        return self.list_commands(category)

    def get_game_status(self):
        return {"status": "success", "game_state": self.game_state}

    def _build_hud_summary(self, systems: Dict[str, Any]) -> Dict[str, Any]:
        hud: Dict[str, Any] = {}
        players = systems.get("players") or {}
        hud["player_count"] = len(players) if isinstance(players, dict) else 0
        try:
            if isinstance(players, dict) and players:
                first_key = sorted(players.keys(), key=lambda k: int(k) if str(k).isdigit() else k)[0]
                pos = players[first_key]
                hud["player_pos"] = list(pos) if isinstance(pos, (list, tuple)) else pos
                hud["player_id"] = first_key
            else:
                hud["player_pos"] = [0, 0, 0]
        except Exception:
            hud["player_pos"] = [0, 0, 0]

        inv = systems.get("inventory") or {}
        if isinstance(inv, dict) and inv:
            total_stacks = 0
            total_items = 0
            for pid, idata in inv.items():
                if isinstance(idata, dict):
                    stacks = idata.get("stacks", [])
                    total_stacks += len(stacks) if isinstance(stacks, list) else 0
                    for s in stacks if isinstance(stacks, list) else []:
                        try:
                            total_items += int(s.get("quantity", 0))
                        except Exception:
                            pass
            hud["inventory_stacks"] = total_stacks
            hud["inventory_items"] = total_items
        else:
            hud["inventory_stacks"] = 0
            hud["inventory_items"] = 0

        for k in ("vehicles", "world", "construction", "economy", "weather"):
            if k in systems:
                v = systems[k]
                if isinstance(v, dict):
                    hud[f"{k}_keys"] = list(v.keys())[:6]
                elif isinstance(v, list):
                    hud[f"{k}_count"] = len(v)
        return hud

    def quit_dashboard(self):
        try:
            import webview
            if webview.windows:
                for w in list(webview.windows):
                    try:
                        w.destroy()
                    except Exception:
                        pass
        except Exception:
            pass
        return {"status": "success", "message": "dashboard_v2 quit"}


# -- entrypoint ------------------------------------------------------------

def _parse_args():
    p = argparse.ArgumentParser(description="MTT Dashboard V2 — Game System Debugger (XMB-themed)")
    p.add_argument("--debug", action="store_true", help="Enable pywebview debug")
    return p.parse_args()


def run(debug: bool = True):
    """Start the Dashboard V2 pywebview window."""
    try:
        import webview
    except ImportError:
        print(
            "Error: pywebview is not installed.\n"
            "Install with: pip install -e '.[xmb]'  or  pip install pywebview",
            file=sys.stderr,
        )
        sys.exit(1)

    html_path = get_dashboard_v2_html_path()
    if not Path(html_path).exists():
        print(f"Dashboard V2 HTML not found at {html_path}", file=sys.stderr)
        sys.exit(1)

    api = DashboardV2API()

    try:
        from core.renderer.main_menu.xmb_settings import load_settings
        s = load_settings()
        fullscreen = bool(s.get("fullscreen", False))
    except Exception:
        fullscreen = False

    webview.create_window(
        title="Milk Toast Taco — Dashboard V2",
        url=f"file://{html_path}",
        js_api=api,
        min_size=(1200, 800),
        fullscreen=fullscreen,
    )
    webview.start(debug=debug)


if __name__ == "__main__":
    args = _parse_args()
    run(debug=args.debug)
