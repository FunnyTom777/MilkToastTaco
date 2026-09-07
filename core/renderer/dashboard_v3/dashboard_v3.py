"""
MTT Dashboard V3 — Python backend for pywebview.

Console-style hub: no sidebar, no command palette, big-screen friendly.
Reuses XMB settings (theme, fullscreen) from xmbsettings.xml.

Lives in its own folder: core/renderer/dashboard_v3/ with its own static/
  - static/controller.js   -> reusable gamepad + focus lib (importable by future UIs)
  - static/dashboard_v3.html -> console UI (tabs on top, card grid, modals)

Run:
    python -m core.renderer.dashboard_v3.dashboard_v3
    python -m core.renderer.dashboard_v3.dashboard_v3 --debug
    python dashboard_v3.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
STATIC_DIR = Path(__file__).parent / "static"
DASHBOARD_V3_HTML_PATH = STATIC_DIR / "dashboard_v3.html"
CONTROLLER_JS_PATH = STATIC_DIR / "controller.js"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def get_dashboard_v3_html_path() -> str:
    return str(DASHBOARD_V3_HTML_PATH.resolve())


def get_controller_js_path() -> str:
    return str(CONTROLLER_JS_PATH.resolve())


# ---------------------------------------------------------------------------
# Dashboard V3 API
# ---------------------------------------------------------------------------

class DashboardV3API:
    """Python API for Dashboard V3 (pywebview bridge). Pure UI menus, no commands."""

    def __init__(self):
        self.game_state = {"started": False, "mode": "hub", "version": "V3"}
        self._current_save: Optional[str] = None
        self._current_data: Optional[Dict[str, Any]] = None

    # -- settings -----------------------------------------------------------
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

    # -- saves --------------------------------------------------------------
    def list_saves(self):
        try:
            from core.systems.save.manager import list_saves as _list
            return {"status": "success", "saves": _list()}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_saves(self):
        return self.list_saves()

    def list_saves_detailed(self):
        try:
            from core.systems.save.manager import _resolve_save_dir
            from core.xml_loader import load_xml_file
            save_dir = _resolve_save_dir()
            saves: List[Dict[str, Any]] = []
            for p in sorted(save_dir.glob("*.xml")):
                try:
                    root = load_xml_file(str(p), strict=False)
                    if root is None:
                        saves.append({"name": p.stem, "exists": True, "saved_at": None, "version": None, "error": "corrupt"})
                        continue
                    saves.append({"name": p.stem, "exists": True, "saved_at": root.get("saved_at"), "version": root.get("version"), "save_name_attr": root.get("name", p.stem)})
                except Exception as e:
                    saves.append({"name": p.stem, "exists": True, "saved_at": None, "error": str(e)})
            return {"status": "success", "saves": saves}
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
            meta = {"name": root.get("name", save_name), "version": root.get("version"), "saved_at": root.get("saved_at")}
            self._current_save = save_name
            self._current_data = {"meta": meta, "systems": data}
            return {"status": "success", "save": save_name, "meta": meta, "systems": data}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def load_game(self, save_name: str):
        try:
            from core.systems.save.manager import load_game as _load
            if not save_name or not str(save_name).strip():
                return {"status": "error", "message": "save_name required"}
            ok = _load(str(save_name).strip())
            if not ok:
                return {"status": "error", "message": f"Save '{save_name}' not found or failed to load"}
            self._current_save = str(save_name).strip()
            try:
                self.load_save(self._current_save)
            except Exception:
                pass
            return {"status": "success", "save": self._current_save, "message": f"Loaded {self._current_save}.xml"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def save_game(self, save_name: str):
        try:
            try:
                import core.systems.economy.wallet  # noqa: F401
                import core.systems.player.ownership  # noqa: F401
                import core.systems.shop.vehicle_shop  # noqa: F401
                import core.systems.inventory.manager  # noqa: F401
                import core.systems.player_manager  # noqa: F401
                import core.systems.realestate.realestate  # noqa: F401
            except Exception:
                pass
            from core.systems.save.manager import save_game as _save
            if not save_name or not str(save_name).strip():
                return {"status": "error", "message": "save_name required"}
            path = _save(str(save_name).strip())
            self._current_save = str(save_name).strip()
            try:
                self.load_save(self._current_save)
            except Exception:
                pass
            return {"status": "success", "save": self._current_save, "path": path, "message": f"Saved to {self._current_save}.xml"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_state(self, save_name: Optional[str] = None):
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
        return {"status": "success", "saves": saves, "current_save": current, "meta": meta, "systems": systems, "hud": hud, "xmb_settings": xmb_settings}

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
        # economy
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
        # real estate
        re_raw = systems.get("realestate") or {}
        re_owned = re_raw.get("owned") if isinstance(re_raw, dict) else None
        re_count = 0
        re_owned_count = 0
        re_rented_count = 0
        re_value = 0
        re_fees = 0
        re_garage_cap = 0
        re_garage_used = 0
        re_by_player: Dict[str, int] = {}
        if isinstance(re_owned, dict):
            for pid, lst in re_owned.items():
                if not isinstance(lst, list):
                    continue
                re_by_player[str(pid)] = len(lst)
                re_count += len(lst)
                for op in lst:
                    if not isinstance(op, dict):
                        continue
                    tenure = str(op.get("tenure", "owned"))
                    if tenure == "rented":
                        re_rented_count += 1
                    else:
                        re_owned_count += 1
                    try:
                        re_value += int(float(op.get("price_paid", 0) or 0))
                    except Exception:
                        pass
                    try:
                        re_fees += int(float(op.get("fee_paid", 0) or 0))
                    except Exception:
                        pass
                    stats = op.get("stats") if isinstance(op.get("stats"), dict) else {}
                    try:
                        parking = int(stats.get("parking", 0) or 0)
                    except Exception:
                        parking = 0
                    try:
                        garage = int(stats.get("garage_spaces", 0) or 0)
                    except Exception:
                        garage = 0
                    cap = max(0, parking + garage)
                    re_garage_cap += cap
                    stored = op.get("stored_vehicles") if isinstance(op.get("stored_vehicles"), list) else []
                    re_garage_used += len(stored)
        if re_count == 0:
            try:
                from core.systems.realestate.realestate import get_owned_properties as _re_get  # noqa
                pid_for_re = int(hud.get("wallet_pid", "1"))
                try:
                    from core.systems.realestate import realestate as _re_mod
                    all_owned = getattr(_re_mod, "_owned", {})
                    for pid, lst in all_owned.items():
                        re_by_player[str(pid)] = len(lst)
                        re_count += len(lst)
                        for op in lst:
                            try:
                                tenure = getattr(op, "tenure", "owned")
                                if tenure == "rented":
                                    re_rented_count += 1
                                else:
                                    re_owned_count += 1
                                re_value += int(getattr(op, "price_paid", 0) or 0)
                                re_fees += int(getattr(op, "fee_paid", 0) or 0)
                                try:
                                    cap = int(op.capacity) if hasattr(op, "capacity") and not callable(getattr(op, "capacity", None)) else 0
                                except Exception:
                                    try:
                                        parking = int(op.stats.get("parking", 0) or 0)
                                        garage = int(op.stats.get("garage_spaces", 0) or 0)
                                        cap = parking + garage
                                    except Exception:
                                        cap = 0
                                re_garage_cap += max(0, cap)
                                re_garage_used += len(getattr(op, "stored_vehicles", []) or [])
                            except Exception:
                                continue
                except Exception:
                    live = _re_get(pid_for_re)
                    re_by_player[str(pid_for_re)] = len(live)
                    re_count = len(live)
                    for op in live:
                        tenure = op.get("tenure", "owned")
                        if tenure == "rented":
                            re_rented_count += 1
                        else:
                            re_owned_count += 1
                        re_value += int(op.get("price_paid", 0) or 0)
                        re_fees += int(op.get("fee_paid", 0) or 0)
                        stats = op.get("stats", {})
                        try:
                            re_garage_cap += int(stats.get("parking", 0) or 0) + int(stats.get("garage_spaces", 0) or 0)
                        except Exception:
                            pass
                        re_garage_used += len(op.get("stored_vehicles", []) or [])
            except Exception:
                pass
        hud["realestate_count"] = re_count
        hud["realestate_owned"] = re_owned_count
        hud["realestate_rented"] = re_rented_count
        hud["realestate_value"] = re_value
        hud["realestate_fees"] = re_fees
        hud["realestate_garage_cap"] = re_garage_cap
        hud["realestate_garage_used"] = re_garage_used
        hud["realestate_garage_free"] = max(0, re_garage_cap - re_garage_used)
        hud["realestate_by_player"] = re_by_player
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

    def get_game_status(self):
        return {"status": "success", "game_state": self.game_state}

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
        return {"status": "success", "message": "dashboard_v3 quit"}

    # -- controller-friendly system bridge (UI menus call these, no typed commands) --
    def call_command(self, name: str, args=None):
        """Dispatch any registered @command via controller UI (buttons, not typed)."""
        try:
            from core.renderer.bridge import bridge_call_command as _bcc
            return _bcc(name, args)
        except Exception as e:
            return {"status": "error", "message": str(e), "command": name}

    def call_function(self, function_id, args=None):
        try:
            from core.renderer.bridge import CommandBridgeMixin as _CBM
            return _CBM.call_function(self, function_id, args)
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def list_commands(self, category: str | None = None, refresh: bool = False):
        try:
            from core.renderer.bridge import bridge_list_commands as _blc
            res = _blc(category, refresh=refresh)
            if res.get("status") == "success":
                res["category"] = category
            return res
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_system(self, name: str):
        """Controller UI helper: get one system's data (inventory/players/phone/shop/realestate/bank)."""
        try:
            n = (name or "").strip().lower()
            if n in ("inventory", "inv"):
                return self.get_inventory()
            if n in ("players", "player"):
                return self.get_players_detail()
            if n in ("phone", "contacts"):
                return self.get_phone_contacts()
            if n in ("shop", "vehicleshop", "vehicles"):
                return self.get_shop_catalog()
            if n in ("realestate", "estate", "property"):
                return self.get_realestate_catalog()
            if n in ("bank", "wallet", "economy"):
                return self.get_bank_overview()
            if n in ("police",):
                return self.get_police()
            return {"status": "error", "message": f"Unknown system '{name}'"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_inventory(self, player_id: int = 1):
        try:
            from core.systems.inventory.manager import ensure_inventory
            from core.systems.inventory.loader import get_item_def
            pid = int(player_id)
            inv = ensure_inventory(pid)
            d = inv.to_dict()
            # enrich stacks with item defs for UI
            enriched = []
            for s in d.get("stacks", []):
                defn = get_item_def(int(s.get("item_id", 0)))
                enriched.append({
                    "item_id": s.get("item_id"),
                    "quantity": s.get("quantity"),
                    "acquired_at": s.get("acquired_at"),
                    "def": {
                        "name": getattr(defn, "name", f"Item {s.get('item_id')}") if defn else f"Item {s.get('item_id')}",
                        "value": getattr(defn, "value", 0) if defn else 0,
                        "weight": getattr(defn, "weight", 0) if defn else 0,
                        "category": getattr(defn, "category", "misc") if defn else "misc",
                        "perishable": getattr(defn, "perishable", False) if defn else False,
                        "description": getattr(defn, "description", "") if defn else "",
                    } if defn else None
                })
            return {"status": "success", "player_id": pid, "max_weight": d.get("max_weight"), "total_weight": inv.total_weight(), "remaining": inv.remaining_capacity(), "stacks": enriched}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_players_detail(self):
        try:
            from core.systems.player_manager import _players
            out = []
            for pid, pos in _players.items():
                out.append({"player_id": int(pid), "pos": list(pos)})
            return {"status": "success", "players": out}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_phone_contacts(self):
        try:
            from core.systems.phone.phone import contacts_list
            # contacts_list is dict
            if isinstance(contacts_list, dict):
                arr = [{"name": k, "number": v} if not isinstance(v, dict) else {"name": k, **v} for k, v in contacts_list.items()]
            else:
                arr = []
            return {"status": "success", "contacts": arr, "count": len(arr)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_shop_catalog(self):
        try:
            from core.systems.shop.vehicle_shop import get_catalog, get_categories
            cat = get_catalog()
            # also return owned for HUD
            owned = []
            try:
                from core.command_registry import execute
                r = execute("vehicleshop.owned", player_id=1)
                if isinstance(r, dict) and r.get("status") == "success":
                    owned = r.get("result") or r.get("vehicles") or []
            except Exception:
                pass
            return {"status": "success", "catalog": cat, "owned": owned}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_realestate_catalog(self):
        try:
            from core.systems.realestate.realestate import get_catalog
            c = get_catalog()
            return {"status": "success", "catalog": c}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_bank_overview(self, player_id: int = 1):
        try:
            from core.systems.economy.wallet import get_balance
            from core.systems.economy.bank import get_cards, get_bank_names, BANKS
            pid = int(player_id)
            bal = float(get_balance(pid))
            cards = get_cards(pid)
            banks = {k: dict(v) for k, v in BANKS.items()} if BANKS else {}
            names = get_bank_names()
            return {"status": "success", "player_id": pid, "balance": bal, "cards": cards, "banks": banks, "bank_names": names}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_police(self):
        try:
            from core.command_registry import execute
            r = execute("police.list_patrols")
            if isinstance(r, dict) and r.get("status") == "success":
                return r
            return {"status": "success", "patrols": [], "message": "No active patrols"}
        except Exception as e:
            return {"status": "success", "patrols": [], "note": str(e)}

    # -- optional helpers for UI richness (not commands) -----------------
    def get_catalog_preview(self):
        """Light catalog preview for tiles (vehicleshop/realestate) without exposing commands."""
        out: Dict[str, Any] = {}
        try:
            from core.systems.shop.vehicle_shop import get_catalog as _cat
            out["vehicleshop"] = _cat()  # type: ignore
        except Exception:
            out["vehicleshop"] = None
        try:
            from core.systems.realestate.realestate import list_properties as _lp  # type: ignore
            out["realestate"] = _lp(limit=6)
        except Exception:
            out["realestate"] = None
        return {"status": "success", "catalog": out}


def _parse_args():
    p = argparse.ArgumentParser(description="MTT Dashboard V3 — Console Hub (no commands, pure UI)")
    p.add_argument("--debug", action="store_true", help="Enable pywebview debug")
    return p.parse_args()


def run(debug: bool | None = None):
    try:
        import webview
    except ImportError:
        print("Error: pywebview is not installed.\nInstall with: pip install -e '.[xmb]'  or  pip install pywebview", file=sys.stderr)
        sys.exit(1)
    # Debug opt-in (was previously True by default, forcing DevTools every launch)
    if debug is None:
        import os

        debug = "--debug" in sys.argv or os.environ.get("MTT_DEBUG") == "1"
    else:
        debug = bool(debug)
    html_path = get_dashboard_v3_html_path()
    if not Path(html_path).exists():
        print(f"Dashboard V3 HTML not found at {html_path}", file=sys.stderr)
        sys.exit(1)
    api = DashboardV3API()
    try:
        from core.renderer.main_menu.xmb_settings import load_settings
        s = load_settings()
        fullscreen = bool(s.get("fullscreen", False))
    except Exception:
        fullscreen = False
    webview.create_window(title="Milk Toast Taco — Dashboard V3", url=f"file://{html_path}", js_api=api, min_size=(1200, 800), fullscreen=fullscreen)
    webview.start(debug=debug)


if __name__ == "__main__":
    args = _parse_args()
    run(debug=args.debug)
