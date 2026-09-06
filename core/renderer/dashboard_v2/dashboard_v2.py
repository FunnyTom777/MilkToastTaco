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

    def list_saves_detailed(self):
        """Return saves with meta (name, saved_at, version) for save-menu grid."""
        try:
            from core.systems.save.manager import _resolve_save_dir, _sanitize_filename
            from core.xml_loader import load_xml_file
            save_dir = _resolve_save_dir()
            saves = []
            for p in sorted(save_dir.glob("*.xml")):
                try:
                    root = load_xml_file(str(p), strict=False)
                    if root is None:
                        saves.append({"name": p.stem, "exists": True, "saved_at": None, "version": None, "error": "corrupt"})
                        continue
                    saves.append({
                        "name": p.stem,
                        "exists": True,
                        "saved_at": root.get("saved_at"),
                        "version": root.get("version"),
                        "save_name_attr": root.get("name", p.stem),
                    })
                except Exception as e:
                    saves.append({"name": p.stem, "exists": True, "saved_at": None, "error": str(e)})
            return {"status": "success", "saves": saves}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def save_game(self, save_name: str):
        """Save current state to a slot/file. Exposed to JS save-menu."""
        try:
            # Ensure all providers are registered before saving (so empty saves don't happen on fresh boot)
            try:
                import core.systems.economy.wallet  # noqa: F401
                import core.systems.player.ownership  # noqa: F401
                import core.systems.shop.vehicle_shop  # noqa: F401
                import core.systems.inventory.manager  # noqa: F401
                import core.systems.player_manager  # noqa: F401
            except Exception:
                pass
            from core.systems.save.manager import save_game as _save
            if not save_name or not str(save_name).strip():
                return {"status": "error", "message": "save_name required"}
            path = _save(str(save_name).strip())
            self._current_save = str(save_name).strip()
            # also update _current_data cache by re-reading?
            try:
                self.load_save(self._current_save)
            except Exception:
                pass
            return {"status": "success", "save": self._current_save, "path": path, "message": f"Saved to {self._current_save}.xml"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_save_slot_info(self, slot: int):
        """Helper for JS: get info for slot 1..20 (maps to save name slot<slot>)."""
        try:
            slot = int(slot)
            if not 1 <= slot <= 20:
                return {"status": "error", "message": "slot must be 1..20"}
            name = f"slot{slot}"
            return self.load_save(name)
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def load_game(self, save_name: str):
        """Restore live game state from a save (for slot Load)."""
        try:
            from core.systems.save.manager import load_game as _load
            if not save_name or not str(save_name).strip():
                return {"status": "error", "message": "save_name required"}
            ok = _load(str(save_name).strip())
            if not ok:
                return {"status": "error", "message": f"Save '{save_name}' not found or failed to load"}
            self._current_save = str(save_name).strip()
            # refresh cache
            try:
                self.load_save(self._current_save)
            except Exception:
                pass
            return {"status": "success", "save": self._current_save, "message": f"Loaded {self._current_save}.xml"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

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

        # -- command registry bridge (autodiscovering, shared via bridge mixin) --
    # Inherits autodiscover behaviour from core.renderer.bridge.CommandBridgeMixin
    # so new @command files appear automatically in V2 (shows all) and
    # future dashboards/game share the same bridge.
    def call_command(self, name: str, args=None):
        from core.renderer.bridge import bridge_call_command as _bcc

        return _bcc(name, args)

    def call_function(self, function_id, args=None):
        from core.renderer.bridge import CommandBridgeMixin as _CBM

        # Delegate via mixin to keep alias semantics (list-wrapped ids, etc.)
        return _CBM.call_function(self, function_id, args)

    def list_commands(self, category: str | None = None, refresh: bool = False):
        from core.renderer.bridge import bridge_list_commands as _blc

        res = _blc(category, refresh=refresh)
        # Normalise to {status, commands, category} shape expected by JS
        if res.get("status") == "success":
            res["category"] = category
        return res

    def get_commands(self, category: str | None = None, refresh: bool = False):
        return self.list_commands(category, refresh=refresh)

    def refresh_commands(self):
        """Force filesystem rescan — JS can call refresh_commands() after adding new @command files."""
        return self.list_commands(refresh=True)

    def get_game_status(self):
        return {"status": "success", "game_state": self.game_state}

    # Expose command for output demo (so /output can be typed even without args)
    # Actual output emission is via get_output/poll_output; no extra command needed.

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

        for k in ("vehicles", "world", "construction", "weather"):
            if k in systems:
                v = systems[k]
                if isinstance(v, dict):
                    hud[f"{k}_keys"] = list(v.keys())[:6]
                elif isinstance(v, list):
                    hud[f"{k}_count"] = len(v)

        # --- Economy HUD (mirrors Dashboard) ----------------------------------
        raw_wallet = systems.get("wallet") or systems.get("economy") or {}
        if isinstance(raw_wallet, dict) and raw_wallet:
            wallet_all: Dict[str, float] = {}
            for kk, vv in raw_wallet.items():
                try:
                    wallet_all[str(kk)] = float(vv)  # type: ignore
                except Exception:
                    continue
            if wallet_all:
                pid_key = str(hud.get("player_id", "1"))
                if pid_key not in wallet_all:
                    try:
                        pid_key = sorted(wallet_all.keys(), key=lambda x: int(x) if str(x).isdigit() else x)[0]
                    except Exception:
                        pid_key = next(iter(wallet_all))
                hud["wallet_balance"] = wallet_all.get(pid_key, 0.0)
                hud["wallet_pid"] = pid_key
                hud["wallet_all"] = wallet_all
                hud["wallet_total"] = sum(wallet_all.values())
            else:
                hud["wallet_balance"] = 0.0
                hud["wallet_all"] = {}
        else:
            try:
                from core.systems.economy.wallet import get_balance
                pid_key = str(hud.get("player_id", "1"))
                try:
                    hud["wallet_balance"] = float(get_balance(int(pid_key)))
                except Exception:
                    hud["wallet_balance"] = float(get_balance(1))
                hud["wallet_pid"] = pid_key
            except Exception:
                hud["wallet_balance"] = 0.0
                hud["wallet_pid"] = "1"
            hud["wallet_all"] = {hud["wallet_pid"]: hud["wallet_balance"]}

        owned = systems.get("ownership") or {}
        owned_count = 0
        owned_value = 0
        owned_by_player: Dict[str, int] = {}
        if isinstance(owned, dict) and "vehicles" in owned and isinstance(owned["vehicles"], dict):
            for pid, lst in owned["vehicles"].items():
                if isinstance(lst, list):
                    owned_by_player[str(pid)] = len(lst)
                    owned_count += len(lst)
                    for ov in lst:
                        try:
                            owned_value += int(float(ov.get("price_paid", 0))) if isinstance(ov, dict) else 0
                        except Exception:
                            pass
        hud["owned_count"] = owned_count
        hud["owned_value"] = owned_value
        hud["owned_by_player"] = owned_by_player

        try:
            import core.systems.orchestrator as _orch
            hud["bank_member"] = getattr(_orch, "current_bank_member", None)
            hud["bank_names"] = list(getattr(_orch, "bank_names", []))
        except Exception:
            hud["bank_member"] = None
            hud["bank_names"] = []
        try:
            from core.systems.economy.bank import get_cards as _get_cards, get_bank_names as _gbn, BANKS as _BANKS
            pid_for_cards = int(hud.get("wallet_pid", "1"))
            hud["bank_cards"] = _get_cards(pid_for_cards)
            hud["bank_configs"] = {k: dict(v) for k, v in _BANKS.items()} if _BANKS else {}
            if not hud["bank_names"]:
                hud["bank_names"] = _gbn()
        except Exception:
            hud["bank_cards"] = []
            hud["bank_configs"] = {}

        return hud

    # -- universal output bus (core/output.py) -----------------------------
    def get_output(self, since_id: int = 0, limit: int = 100, level: str | None = None, channel: str | None = None):
        """Poll output bus for dashboard chat. Wraps core.output.get_output()."""
        try:
            from core.output import get_output as _get
            return _get(since_id=int(since_id) if isinstance(since_id, int) else 0, limit=int(limit) if isinstance(limit, int) else 100, level=level, channel=channel)
        except Exception as e:
            return {"status": "error", "message": str(e), "messages": []}

    def poll_output(self, since_id: int = 0, limit: int = 100):
        """Alias for get_output — JS polls poll_output(since_id)."""
        return self.get_output(since_id=since_id, limit=limit)

    def push_output(self, message: str, level: str = "info", channel: str = "general", source: str = "dashboard_v2"):
        """Push a message into the output bus from JS/frontend."""
        try:
            from core.output import emit as _emit
            entry = _emit(str(message), level=level or "info", channel=channel or "general", source=source or "dashboard_v2")
            return {"status": "success", "entry": entry}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def clear_output(self):
        try:
            from core.output import clear as _clear
            return _clear()
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # also expose print_to_user as a pywebview-callable for JS-initiated toasts
    def print_to_user(self, text: str, level: str = "info", channel: str = "general"):
        try:
            from core.output import print_to_user as _ptu
            entry = _ptu(str(text), level=level or "info", channel=channel or "general", source="dashboard_v2")
            return {"status": "success", "entry": entry}
        except Exception as e:
            return {"status": "error", "message": str(e)}

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
