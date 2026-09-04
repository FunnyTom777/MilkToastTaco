"""
MTT Dashboard — Python backend for pywebview.

Mirrors the XMB architecture (xmb.py + static/milk_toast_taco_xmb.html):
  - dashboard.py  -> Python API exposed via pywebview JS bridge
  - static/dashboard.html -> UI layer (HTML/CSS/JS)

Loads save data via the standalone save/load module (core/systems/save/)
and surfaces MTT system state (players, inventory, world, etc.) without
mutating those systems directly — it consumes them.

Also re-uses XMB settings (theme, fullscreen) from xmbsettings.xml so
the Dashboard feels like the same console on the same screen.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Paths --------------------------------------------------------------------
# core/renderer/dashboard/dashboard.py -> parents[3] -> MilkToastTaco/
PROJECT_ROOT = Path(__file__).resolve().parents[3]
STATIC_DIR = Path(__file__).parent / "static"
DASHBOARD_HTML_PATH = STATIC_DIR / "dashboard.html"

# Support both direct file execution and `python -m core.renderer.dashboard.dashboard`
# Ensure project root is on sys.path.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def get_dashboard_html_path() -> str:
    """Absolute path to static/dashboard.html."""
    return str(DASHBOARD_HTML_PATH.resolve())


# ---------------------------------------------------------------------------
# Dashboard API — exposed to JS via pywebview.api.*
# ---------------------------------------------------------------------------

class DashboardAPI:
    """Python API for the MTT Dashboard frontend (pywebview bridge)."""

    def __init__(self, dev_mode: bool = False):
        # dev_mode kept for backwards compat but not used in player dashboard
        # (future dev tools will be separate). Always player-facing.
        self.dev_mode: bool = False
        # in-memory save editing: load once, edit freely, save on demand
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
        # try live-apply to window
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

    # -- dev mode (deprecated, kept for compat) ---------------------------

    def get_dev_mode(self):
        return {"status": "success", "dev_mode": False}

    def set_dev_mode(self, enabled: bool):
        # no-op: dashboard is player-only; future dev tools will be separate
        return {"status": "success", "dev_mode": False}

    # -- saves (standalone save/load module) -------------------------------
    # Proposed issue API: load_save, save_state, list_saves
    # Delegates to core.systems.save.manager which stores .xml under saves/

    def list_saves(self):
        """List available saves (without .xml)."""
        try:
            from core.systems.save.manager import list_saves as _list
            saves = _list()
            return {"status": "success", "saves": saves}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # Alias matching issue naming
    def get_saves(self):
        return self.list_saves()

    def load_save(self, save_name: str):
        """
        Parse XML save and return structured dict.
        Also caches in-memory as _current_data for edit-on-demand.
        """
        try:
            from core.systems.save.manager import list_saves as _list
            from core.xml_loader import load_xml_file
            from core.systems.save.xml_codec import element_to_value

            # Use raw XML parse to return structured data without restoring globals
            # (Dashboard should not clobber live game state — it inspects).
            from core.systems.save.manager import _resolve_save_dir, _sanitize_filename

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

            # also include meta
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

    def save_state(self, save_name: str, data: Optional[Dict[str, Any]] = None):
        """
        Write structured data back to XML.
        If data is None, writes current in-memory _current_data systems.
        If data contains per-system dicts, writes those to a new file via
        xml_codec directly (does not clobber global providers — dashboard's
        own save path for dev editing).

        For the basic scaffold this restores providers temporarily, calls
        save_game, and restores — but the simpler path is to write directly.
        """
        try:
            import datetime
            import xml.etree.ElementTree as ET
            import os
            from core.systems.save.manager import _resolve_save_dir, _sanitize_filename, SAVE_VERSION
            from core.systems.save.xml_codec import value_to_element

            save_dir = _resolve_save_dir()
            file_path = save_dir / f"{_sanitize_filename(save_name)}.xml"

            # Determine systems dict to write
            if data is not None and isinstance(data, dict):
                # Caller may pass {systems: {...}} or flat systems dict
                if "systems" in data and isinstance(data["systems"], dict):
                    systems_data = data["systems"]
                else:
                    systems_data = data
            elif self._current_data and "systems" in self._current_data:
                systems_data = self._current_data["systems"]
            else:
                # fallback: snapshot live providers via save_game helpers
                from core.systems.save.registry import get_providers
                systems_data = {}
                for key, (save_fn, _) in get_providers().items():
                    try:
                        systems_data[key] = save_fn()
                    except Exception:
                        continue

            root = ET.Element("save", {
                "version": str(SAVE_VERSION),
                "name": save_name,
                "saved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            })
            systems_el = ET.SubElement(root, "systems")
            for key, state in systems_data.items():
                el = value_to_element("system", state)
                el.set("key", str(key))
                systems_el.append(el)

            ET.indent(root, space="  ")
            tree = ET.ElementTree(root)
            tmp = file_path.with_suffix(".xml.tmp")
            tree.write(tmp, encoding="utf-8", xml_declaration=True)
            os.replace(tmp, file_path)

            self._current_save = save_name
            if self._current_data is None:
                self._current_data = {}
            # keep in-memory in sync
            self._current_data = {"meta": {"name": save_name, "version": str(SAVE_VERSION)}, "systems": systems_data}

            return {"status": "success", "path": str(file_path), "save": save_name}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # -- get_state bridge (main dashboard data pull) -----------------------

    def get_state(self, save_name: Optional[str] = None):
        """
        Bridge function for dashboard.html to pull structured MTT state.

        If save_name is given, loads that file (cached). Otherwise returns
        the in-memory current_data if set, or live system snapshots.

        Returns dict with keys: saves, current_save, meta, systems, live,
        xmb_settings, dev_mode — safe to JSON-serialize to the frontend.
        """
        try:
            from core.renderer.main_menu.xmb_settings import load_settings
            xmb_settings = load_settings()
        except Exception:
            xmb_settings = {"fullscreen": False, "theme": "default"}

        # saves list
        try:
            from core.systems.save.manager import list_saves as _list
            saves = _list()
        except Exception:
            saves = []

        # Resolve requested save
        systems: Dict[str, Any] = {}
        meta: Dict[str, Any] = {}
        current = self._current_save

        if save_name is not None:
            # load requested
            res = self.load_save(save_name)
            if res.get("status") == "success":
                systems = res.get("systems", {})
                meta = res.get("meta", {})
                current = save_name
            else:
                return {"status": "error", "message": res.get("message", "load failed"), "saves": saves, "xmb_settings": xmb_settings, "dev_mode": False}
        elif self._current_data and "systems" in self._current_data:
            systems = self._current_data.get("systems", {})
            meta = self._current_data.get("meta", {})
        else:
            # live snapshot from providers (no disk IO) — import and call save_fns
            try:
                from core.systems.save.registry import get_providers
                for key, (save_fn, _) in get_providers().items():
                    try:
                        systems[key] = save_fn()
                    except Exception as e:
                        systems[key] = {"_error": str(e)}
            except Exception as e:
                systems = {"_error": str(e)}

        # Build player-friendly HUD summary from systems
        hud = self._build_hud_summary(systems)

        return {
            "status": "success",
            "saves": saves,
            "current_save": current,
            "meta": meta,
            "systems": systems,
            "hud": hud,
            "xmb_settings": xmb_settings,
            "dev_mode": False,
        }

    def _build_hud_summary(self, systems: Dict[str, Any]) -> Dict[str, Any]:
        """Derive player-facing HUD fields from raw systems dict."""
        hud: Dict[str, Any] = {}
        # players
        players = systems.get("players") or {}
        hud["player_count"] = len(players) if isinstance(players, dict) else 0
        # first player pos
        try:
            if isinstance(players, dict) and players:
                # keys are str pids
                first_key = sorted(players.keys(), key=lambda k: int(k) if str(k).isdigit() else k)[0]
                pos = players[first_key]
                hud["player_pos"] = list(pos) if isinstance(pos, (list, tuple)) else pos
                hud["player_id"] = first_key
            else:
                hud["player_pos"] = [0, 0, 0]
        except Exception:
            hud["player_pos"] = [0, 0, 0]

        # inventory
        inv = systems.get("inventory") or {}
        if isinstance(inv, dict) and inv:
            # count stacks across all players
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

        # world / vehicles / construction placeholders
        for k in ("vehicles", "world", "construction", "economy", "weather"):
            if k in systems:
                v = systems[k]
                if isinstance(v, dict):
                    hud[f"{k}_keys"] = list(v.keys())[:6]
                elif isinstance(v, list):
                    hud[f"{k}_count"] = len(v)

        return hud

    def get_raw_state(self):
        """Alias for get_state for backwards compat with early dashboard ideas."""
        return self.get_state()

    # -- command registry bridge (decoupled) ---------------------------------
    # Single entry-point so dashboards/game never hardcode system imports.
    # JS: pywebview.api.call_command("player.move", {player_id: 1, pos: [10,0,5]})
    def call_command(self, name: str, args=None):
        """
        Dispatch any registered command (string id, namespaced like 'player.move').

        Args:
            name: Command name e.g. "player.move", "inventory.add", "bank.apply".
            args: Optional dict of kwargs, or list of positional args.
                  Simplest is dict: {player_id: 1, pos: [10,0,5]}

        Returns:
            {"status": "success", "result": ...} or {"status": "error", "message": ...}
        """
        try:
            from core.command_registry import execute, ensure_commands_loaded

            ensure_commands_loaded()
            if args is None:
                return execute(name)
            if isinstance(args, dict):
                return execute(name, **args)
            if isinstance(args, (list, tuple)):
                return execute(name, *args)
            # single value fallback
            return execute(name, args)
        except Exception as e:
            return {"status": "error", "message": str(e), "command": name}

    # Alias matching user's original proposal
    def call_function(self, function_id, args=None):
        """Alias for call_command (supports original function_id naming)."""
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
        """
        List available commands, optionally filtered by category.

        Args:
            category: "player" | "dev" | None (all). Player dashboard passes "player".

        Returns:
            {"status": "success", "commands": [{name, help, category, params}]}
        """
        try:
            from core.command_registry import list_commands as _list, ensure_commands_loaded

            ensure_commands_loaded()
            cmds = _list(category)
            return {"status": "success", "commands": cmds, "category": category}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_commands(self, category: str | None = None):
        """Alias for list_commands."""
        return self.list_commands(category)

    # -- live edit helpers (dev mode) --------------------------------------

    def update_player_pos(self, player_id: int, pos):
        """
        Legacy helper: now delegates to command registry (kept for backwards compat).
        Prefer: call_command("player.move", {player_id, pos})
        """
        # In-memory edit path preserved for save-editing workflow
        try:
            if self._current_data and "systems" in self._current_data:
                if not (hasattr(pos, "__len__") and len(pos) == 3):
                    return {"status": "error", "message": "pos must be [x,y,z]"}
                players = self._current_data["systems"].setdefault("players", {})
                players[str(player_id)] = [float(pos[0]), float(pos[1]), float(pos[2])]
                return {"status": "success", "players": players}
        except Exception:
            pass
        # Live path via registry
        return self.call_command("player.move", {"player_id": int(player_id), "pos": pos})

    def add_inventory_item(self, player_id: int, item_id: int, quantity: int = 1):
        """
        Legacy helper: now delegates to command registry.
        Prefer: call_command("inventory.add", {player_id, item_id, quantity})
        """
        try:
            if self._current_data and "systems" in self._current_data:
                inv = self._current_data["systems"].setdefault("inventory", {})
                pid = str(player_id)
                if pid not in inv:
                    inv[pid] = {"max_weight": 35.0, "stacks": []}
                stacks = inv[pid].setdefault("stacks", [])
                for s in stacks:
                    if s.get("item_id") == int(item_id):
                        s["quantity"] = int(s.get("quantity", 0)) + int(quantity)
                        return {"status": "success", "inventory": inv[pid]}
                stacks.append({"item_id": int(item_id), "quantity": int(quantity), "acquired_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()})
                return {"status": "success", "inventory": inv[pid]}
        except Exception:
            pass
        return self.call_command("inventory.add", {"player_id": int(player_id), "item_id": int(item_id), "quantity": int(quantity)})

    def delete_save(self, save_name: str):
        try:
            from core.systems.save.manager import delete_save as _del
            ok = _del(save_name)
            if self._current_save == save_name:
                self._current_save = None
                self._current_data = None
            return {"status": "success" if ok else "error", "message": "deleted" if ok else "not found"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def refresh(self, save_name: Optional[str] = None):
        """Force re-read from disk, discarding in-memory edits (if save_name given)."""
        if save_name:
            # clear cache then load
            self._current_data = None
            self._current_save = None
            return self.load_save(save_name)
        # refresh live
        self._current_data = None
        return self.get_state()

    # -- universal output bus (core/output.py) ------------------------------
    def get_output(self, since_id: int = 0, limit: int = 100, level: str | None = None, channel: str | None = None):
        try:
            from core.output import get_output as _get
            return _get(since_id=int(since_id) if isinstance(since_id, int) else 0, limit=int(limit) if isinstance(limit, int) else 100, level=level, channel=channel)
        except Exception as e:
            return {"status": "error", "message": str(e), "messages": []}

    def poll_output(self, since_id: int = 0, limit: int = 100):
        return self.get_output(since_id=since_id, limit=limit)

    def push_output(self, message: str, level: str = "info", channel: str = "general", source: str = "dashboard"):
        try:
            from core.output import emit as _emit
            entry = _emit(str(message), level=level or "info", channel=channel or "general", source=source or "dashboard")
            return {"status": "success", "entry": entry}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def clear_output(self):
        try:
            from core.output import clear as _clear
            return _clear()
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def print_to_user(self, text: str, level: str = "info", channel: str = "general"):
        try:
            from core.output import print_to_user as _ptu
            entry = _ptu(str(text), level=level or "info", channel=channel or "general", source="dashboard")
            return {"status": "success", "entry": entry}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def quit_dashboard(self):
        """Close the dashboard window."""
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
        return {"status": "success", "message": "dashboard quit"}


# -- entrypoint ------------------------------------------------------------

def _parse_args():
    p = argparse.ArgumentParser(description="MTT Dashboard — player-facing")
    p.add_argument("--debug", action="store_true", help="Enable pywebview debug")
    return p.parse_args()


def run(dev_mode: bool = False, debug: bool = True):
    """Start the Dashboard pywebview window."""
    try:
        import webview
    except ImportError:
        print(
            "Error: pywebview is not installed.\n"
            "Install with: pip install -e '.[xmb]'  or  pip install pywebview",
            file=sys.stderr,
        )
        sys.exit(1)

    html_path = get_dashboard_html_path()
    if not Path(html_path).exists():
        print(f"Dashboard HTML not found at {html_path}", file=sys.stderr)
        sys.exit(1)

    api = DashboardAPI(dev_mode=dev_mode)

    try:
        from core.renderer.main_menu.xmb_settings import load_settings
        s = load_settings()
        fullscreen = bool(s.get("fullscreen", False))
    except Exception:
        fullscreen = False

    webview.create_window(
        title="Milk Toast Taco — Dashboard",
        url=f"file://{html_path}",
        js_api=api,
        min_size=(1100, 700),
        fullscreen=fullscreen,
    )
    webview.start(debug=debug)


if __name__ == "__main__":
    args = _parse_args()
    run(debug=args.debug)
