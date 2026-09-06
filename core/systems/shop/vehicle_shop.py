"""
Vehicle Shop — FS22-style shop system.

Owns catalog (data/vehicles.xml), categories, and buy/sell logic.
Separated from dashboard so the future game can `from core.systems.shop.vehicle_shop import ...`.

Integrates:
 - ownership.py  -> `add_owned_vehicle` / `remove_owned_vehicle`
 - economy/wallet.py -> balance checks / deduct / refund on sell
 - vehicles/data/license_plates.py -> plate generation (via ownership)
 - output.py -> player feedback (also returned as command dicts)

Commands (autodiscovered):
 - vehicleshop.list_categories
 - vehicleshop.list_vehicles
 - vehicleshop.info
 - vehicleshop.buy
 - vehicleshop.sell
 - vehicleshop.owned
 - vehicleshop.get_catalog
 - vehicleshop.open  (returns catalog for UI)

Future game can also call pure python:
    from core.systems.shop.vehicle_shop import get_categories, get_vehicles, buy_vehicle, get_catalog
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.command_registry import command

try:
    from core.systems.orchestrator import warning as _warn
except ImportError:
    def _warn(m): print(m)

try:
    from core.output import print_to_user as _ptu, success as _success, warning as _out_warn, error as _err
except ImportError:
    def _ptu(msg, **k): print(msg)
    def _success(msg, **k): print(msg)
    def _out_warn(msg, **k): print(msg)
    def _err(msg, **k): print(msg)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class CategoryDef:
    id: str
    name: str
    icon: str = "fa-car"
    color: str = "#3b82f6"
    description: str = ""
    image: str = ""  # optional URL / path; if empty UI uses icon

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class VehicleDef:
    id: str
    name: str
    category: str
    price: int
    image: str = ""  # placeholder key: car/truck/tractor/etc -> UI maps to icon
    description: str = ""
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

# ---------------------------------------------------------------------------
# Catalog loader (data/vehicles.xml)
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CATALOG = _PROJECT_ROOT / "data" / "vehicles.xml"

_categories: List[CategoryDef] = []
_vehicles: List[VehicleDef] = []
_by_id: Dict[str, VehicleDef] = {}
_by_category: Dict[str, List[VehicleDef]] = {}
_loaded: bool = False
_load_error: Optional[str] = None

def _load_catalog(path: Optional[Path] = None) -> None:
    global _categories, _vehicles, _by_id, _by_category, _loaded, _load_error
    if _loaded:
        return
    _categories = []
    _vehicles = []
    _by_id = {}
    _by_category = {}
    _load_error = None
    p = Path(path) if path else DEFAULT_CATALOG
    if not p.exists():
        _load_error = f"Catalog not found: {p}"
        _warn(_load_error)
        _loaded = True
        _seed_fallback()
        return
    try:
        tree = ET.parse(str(p))
        root = tree.getroot()
        # categories
        cats_el = root.find("categories")
        if cats_el is not None:
            for c in cats_el.findall("category"):
                try:
                    cid = (c.get("id") or "").strip()
                    if not cid:
                        continue
                    _categories.append(CategoryDef(
                        id=cid,
                        name=c.get("name", cid) or cid,
                        icon=c.get("icon", "fa-car") or "fa-car",
                        color=c.get("color", "#3b82f6") or "#3b82f6",
                        description=c.get("description", "") or "",
                        image=c.get("image", "") or "",
                    ))
                except Exception as e:
                    _warn(f"skip bad category: {e}")
        # vehicles
        for v in root.findall("vehicle"):
            try:
                vid = (v.findtext("id") or "").strip()
                name = (v.findtext("name") or vid).strip()
                cat = (v.findtext("category") or "").strip()
                price_raw = (v.findtext("price") or "0").strip()
                price = int(float(price_raw)) if price_raw else 0
                image = (v.findtext("image") or "").strip()
                desc = (v.findtext("description") or "").strip()
                stats: Dict[str, Any] = {}
                stats_el = v.find("stats")
                if stats_el is not None:
                    for s in stats_el:
                        tag = (s.tag or "").strip()
                        txt = (s.text or "").strip()
                        if not tag:
                            continue
                        # coerce numeric
                        try:
                            if "." in txt:
                                stats[tag] = float(txt)
                            else:
                                stats[tag] = int(txt)
                        except Exception:
                            stats[tag] = txt
                vd = VehicleDef(id=vid, name=name, category=cat, price=price, image=image, description=desc, stats=stats)
                if not vid:
                    continue
                _vehicles.append(vd)
                _by_id[vid.lower()] = vd
            except Exception as e:
                _warn(f"skip bad vehicle: {e}")
        # index by category
        for vd in _vehicles:
            key = vd.category.lower()
            if key not in _by_category:
                _by_category[key] = []
            _by_category[key].append(vd)
        _loaded = True
        if not _categories:
            _warn("No categories in vehicles.xml, seeding fallback")
            _seed_fallback()
        if not _vehicles:
            _warn("No vehicles in vehicles.xml")
    except Exception as e:
        _load_error = str(e)
        _warn(f"Failed to load catalog {p}: {e}")
        _loaded = True
        _seed_fallback()

def _seed_fallback():
    """Minimal fallback if XML missing/corrupt so commands still work."""
    global _categories, _vehicles, _by_id, _by_category
    if _categories:
        return
    _categories = [
        CategoryDef(id="cars", name="Cars", icon="fa-car", color="#3b82f6"),
        CategoryDef(id="trucks", name="Trucks", icon="fa-truck", color="#f97316"),
    ]
    _vehicles = [
        VehicleDef(id="car_sedan_classic", name="Sedan Classic", category="cars", price=12500, image="car", description="Fallback sedan", stats={"power": 145, "top_speed": 185}),
    ]
    _by_id = {v.id.lower(): v for v in _vehicles}
    _by_category = {"cars": list(_vehicles)}

def _ensure_loaded():
    if not _loaded:
        _load_catalog()

# ---------------------------------------------------------------------------
# Public catalog API
# ---------------------------------------------------------------------------

def get_categories() -> List[Dict[str, Any]]:
    _ensure_loaded()
    return [c.to_dict() for c in _categories]

def get_category(category_id: str) -> Optional[Dict[str, Any]]:
    _ensure_loaded()
    if not category_id:
        return None
    key = category_id.strip().lower()
    for c in _categories:
        if c.id.lower() == key:
            return c.to_dict()
    return None

def get_vehicles(category: Optional[str] = None) -> List[Dict[str, Any]]:
    _ensure_loaded()
    if category is None or not str(category).strip():
        return [v.to_dict() for v in _vehicles]
    key = str(category).strip().lower()
    return [v.to_dict() for v in _by_category.get(key, [])]

def get_vehicle(vehicle_id: str) -> Optional[VehicleDef]:
    _ensure_loaded()
    if not vehicle_id:
        return None
    return _by_id.get(vehicle_id.strip().lower())

def get_vehicle_dict(vehicle_id: str) -> Optional[dict]:
    v = get_vehicle(vehicle_id)
    return v.to_dict() if v else None

def get_catalog() -> dict:
    _ensure_loaded()
    # build counts per category
    counts = {c.id: len(_by_category.get(c.id.lower(), [])) for c in _categories}
    return {
        "categories": [c.to_dict() for c in _categories],
        "vehicles": [v.to_dict() for v in _vehicles],
        "counts": counts,
        "load_error": _load_error,
    }

def search_vehicles(query: str) -> List[Dict[str, Any]]:
    _ensure_loaded()
    q = (query or "").strip().lower()
    if not q:
        return []
    out = []
    for v in _vehicles:
        if q in v.id.lower() or q in v.name.lower() or q in v.category.lower():
            out.append(v.to_dict())
    return out

def _to_owned_dict(vehicle_def: VehicleDef) -> dict:
    return vehicle_def.to_dict()

# ---------------------------------------------------------------------------
# Buy / Sell (ownership + wallet)
# ---------------------------------------------------------------------------

def buy_vehicle(player_id: int, vehicle_id: str, card_id: Optional[str] = None, payment_method: Optional[str] = None) -> dict:
    """
    Buy a vehicle for player. Checks wallet or card, deducts, adds to ownership.
    If card_id is given, uses bank.pay_with_card (enforces per-transaction limits).
    Otherwise uses wallet (legacy).
    Returns {status, message, instance_id, vehicle, balance}
    """
    _ensure_loaded()
    pid = int(player_id)
    vid = str(vehicle_id).strip()
    # allow card_id to be passed as payment_method alias
    if not card_id and payment_method:
        card_id = str(payment_method).strip() or None
    # also allow vehicle_id to contain card via legacy positional confusion handled in command wrapper
    if not vid:
        return {"status": "error", "message": "vehicle_id required"}
    v = get_vehicle(vid)
    if v is None:
        matches = search_vehicles(vid)
        if len(matches) == 1:
            v = get_vehicle(matches[0]["id"])
        if v is None:
            return {"status": "error", "message": f"Unknown vehicle '{vehicle_id}'. Use vehicleshop.list_vehicles to browse."}
    # payment: card path (enforces limits)
    new_bal = None
    payment_info: Dict[str, Any] = {}
    if card_id:
        try:
            from core.systems.economy.bank import pay_with_card
            pay_res = pay_with_card(pid, str(card_id), float(v.price), description=f"Vehicle {v.name}")
            if pay_res.get("status") != "success":
                # Transaction Failed — propagate exactly
                return {"status": "error", "message": pay_res.get("message", "Transaction Failed"), "price": v.price, "card": pay_res.get("card")}
            payment_info = {"card": pay_res.get("card"), "type": pay_res.get("type")}
            # for debit, also fetch new wallet balance
            if pay_res.get("type") == "debit":
                try:
                    from core.systems.economy.wallet import get_balance
                    new_bal = get_balance(pid)
                except Exception:
                    new_bal = None
            else:
                # credit: show debt/available
                payment_info["debt"] = pay_res.get("debt")
                payment_info["available"] = pay_res.get("available")
                try:
                    from core.systems.economy.wallet import get_balance
                    new_bal = get_balance(pid)
                except Exception:
                    new_bal = None
        except Exception as e:
            return {"status": "error", "message": f"Card payment failed: {e}"}
    else:
        # legacy wallet path
        try:
            from core.systems.economy.wallet import get_balance, deduct_funds
            bal = get_balance(pid)
            if bal + 1e-9 < v.price:
                return {"status": "error", "message": f"Insufficient funds: need ${v.price}, have ${bal:.0f}", "balance": bal, "price": v.price}
            ok = deduct_funds(pid, float(v.price))
            if not ok:
                return {"status": "error", "message": f"Insufficient funds: need ${v.price}, have ${bal:.0f}", "balance": bal}
            new_bal = get_balance(pid)
        except ImportError:
            new_bal = None

    # add to ownership
    try:
        from core.systems.player.ownership import add_owned_vehicle
        ov = add_owned_vehicle(pid, v, price_paid=v.price, stats=dict(v.stats))
        # success message varies by payment type
        if payment_info:
            _success(f"Player {pid} bought {v.name} for ${v.price} via {payment_info.get('type')} {payment_info.get('card',{}).get('bank','')} (instance {ov.instance_id})", source="vehicleshop")
        else:
            _success(f"Player {pid} bought {v.name} for ${v.price} (instance {ov.instance_id})", source="vehicleshop")
        out: Dict[str, Any] = {"status": "success", "message": f"Bought {v.name} for ${v.price}", "instance_id": ov.instance_id, "vehicle": ov.to_dict(), "balance": new_bal, "catalog_price": v.price}
        if payment_info:
            out["payment"] = payment_info
        return out
    except Exception as e:
        # refund on failure
        try:
            if card_id:
                # refund via pay_debt or add_funds?
                from core.systems.economy.bank import pay_debt
                # for credit, reduce debt; for debit, refund wallet
                from core.systems.economy.bank import find_card
                c = find_card(pid, str(card_id))
                if c and c.type == "credit":
                    c.debt = max(0.0, float(c.debt) - float(v.price))
                else:
                    from core.systems.economy.wallet import add_funds
                    add_funds(pid, float(v.price))
            else:
                from core.systems.economy.wallet import add_funds
                add_funds(pid, float(v.price))
        except Exception:
            pass
        _err(f"buy_vehicle failed: {e}", source="vehicleshop")
        return {"status": "error", "message": f"Purchase failed: {e}"}

def sell_vehicle(player_id: int, instance_id: str, refund_ratio: float = 0.7) -> dict:
    """
    Sell an owned vehicle instance. Refunds refund_ratio * price_paid.
    """
    pid = int(player_id)
    iid = str(instance_id).strip()
    if not iid:
        return {"status": "error", "message": "instance_id required (from vehicleshop.owned)"}
    if not (0 < refund_ratio <= 1):
        refund_ratio = 0.7
    # find owned
    try:
        from core.systems.player.ownership import list_owned_vehicles, remove_owned_vehicle
        owned = list_owned_vehicles(pid)
        target = None
        for ov in owned:
            if ov.instance_id == iid:
                target = ov
                break
        if target is None:
            # also try vehicle_id as fallback (sell first match)
            for ov in owned:
                if ov.vehicle_id.lower() == iid.lower():
                    target = ov
                    iid = ov.instance_id
                    break
        if target is None:
            return {"status": "error", "message": f"Not owned: '{instance_id}'. Use vehicleshop.owned to list."}
        ok = remove_owned_vehicle(pid, iid)
        if not ok:
            return {"status": "error", "message": f"Failed to remove {iid}"}
        refund = int(round(target.price_paid * refund_ratio))
        try:
            from core.systems.economy.wallet import add_funds, get_balance
            new_bal = add_funds(pid, float(refund))
            _success(f"Player {pid} sold {target.name} ({iid}) for ${refund}", source="vehicleshop")
            return {"status": "success", "message": f"Sold {target.name} for ${refund}", "refund": refund, "balance": new_bal, "instance_id": iid}
        except ImportError:
            _success(f"Player {pid} sold {target.name} ({iid})", source="vehicleshop")
            return {"status": "success", "message": f"Sold {target.name}", "refund": refund, "instance_id": iid}
    except Exception as e:
        _err(f"sell_vehicle failed: {e}", source="vehicleshop")
        return {"status": "error", "message": str(e)}

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@command("vehicleshop.list_categories", "List shop categories (FS22 grid)", category="player")
def vehicleshop_list_categories() -> dict:
    cats = get_categories()
    counts = {c["id"]: len(get_vehicles(c["id"])) for c in cats}
    return {"status": "success", "categories": cats, "counts": counts}

@command("vehicleshop.list_vehicles", "List vehicles (optionally filter by category)", category="player")
def vehicleshop_list_vehicles(category: str = "") -> dict:
    # category optional: "" -> all
    if category and str(category).strip():
        cat = str(category).strip()
        # validate category exists
        vlist = get_vehicles(cat)
        # if empty but category not known, try as search
        if not vlist:
            known = {c.id.lower() for c in _categories} if _loaded else set()
            if cat.lower() not in known:
                # maybe they passed vehicle search?
                vlist = search_vehicles(cat)
                if vlist:
                    return {"status": "success", "category": cat, "vehicles": vlist, "searched": True}
                return {"status": "error", "message": f"Unknown category '{category}'. Use vehicleshop.list_categories"}
        return {"status": "success", "category": cat, "vehicles": vlist, "count": len(vlist)}
    all_v = get_vehicles(None)
    return {"status": "success", "vehicles": all_v, "count": len(all_v)}

@command("vehicleshop.info", "Get vehicle details by id", category="player")
def vehicleshop_info(vehicle_id: str) -> dict:
    if not vehicle_id or not str(vehicle_id).strip():
        return {"status": "error", "message": "vehicle_id required"}
    v = get_vehicle(str(vehicle_id))
    if v is None:
        sugg = search_vehicles(str(vehicle_id))
        hint = f" Did you mean: {', '.join(x['id'] for x in sugg[:3])}?" if sugg else ""
        return {"status": "error", "message": f"Unknown vehicle '{vehicle_id}'.{hint}"}
    return {"status": "success", "vehicle": v.to_dict()}

@command("vehicleshop.buy", "Buy a vehicle by id (supports card_id for bank limits — use Payment Menu)", category="player")
def vehicleshop_buy(player_id: int = 1, vehicle_id: str = "", id: str = "", name: str = "", card_id: str = "", card: str = "", payment_method: str = "") -> dict:
    """
    Buy a vehicle. Preferred: vehicleshop.buy player_id=1 vehicle_id="car_sedan_classic" card_id="card_1_westbank_debit_xxx"
    Also accepts: vehicleshop.buy "car_sedan_classic"  (player defaults to 1)
    Legacy aliases: id=, name=  • card= / payment_method= are aliases for card_id.
    If card_id is given, payment enforces per-transaction debit/credit limits via bank.pay.
    """
    # collect card alias
    chosen_card = (card_id or card or payment_method or "").strip() or None
    # flexible positional handling: if player_id is actually a string vehicle id and vehicle_id empty
    pid = 1
    vid = ""
    if isinstance(player_id, str) and not vehicle_id and not id and not name:
        vid = player_id
        pid = 1
    elif isinstance(player_id, str) and vehicle_id == "" and (id or name):
        vid = id or name or vehicle_id
        try:
            pid = int(player_id)
        except Exception:
            pid = 1
            vid = str(player_id)
    else:
        try:
            pid = int(player_id)
        except Exception:
            pid = 1
            vid = str(player_id)
        vid = (vehicle_id or id or name or vid or "").strip()
        if not vid and isinstance(player_id, str):
            vid = str(player_id).strip()
    if not vid:
        return {"status": "error", "message": "vehicle_id required. Example: /vehicleshop.buy car_sedan_classic  or  /vehicleshop.buy player_id=1 vehicle_id=car_sedan_classic card_id=card_..."}
    return buy_vehicle(pid, vid, card_id=chosen_card)

@command("vehicleshop.sell", "Sell an owned vehicle by instance_id (refund 70%)", category="player")
def vehicleshop_sell(player_id: int = 1, instance_id: str = "", id: str = "") -> dict:
    pid = 1
    iid = ""
    if isinstance(player_id, str) and not instance_id:
        iid = player_id
        pid = 1
    else:
        try:
            pid = int(player_id)
        except Exception:
            pid = 1
            iid = str(player_id)
        iid = (instance_id or id or iid or "").strip()
    if not iid:
        return {"status": "error", "message": "instance_id required. Use vehicleshop.owned to list. Example: /vehicleshop.sell ov_abc123"}
    return sell_vehicle(pid, iid)

@command("vehicleshop.owned", "List owned vehicles for a player (ownership.py)", category="player")
def vehicleshop_owned(player_id: int = 1) -> dict:
    pid = int(player_id)
    try:
        from core.systems.player.ownership import get_owned_vehicles as _gov
        vehicles = _gov(pid)
        # enrich with catalog current stats? keep as is
        try:
            from core.systems.economy.wallet import get_balance
            bal = get_balance(pid)
        except Exception:
            bal = None
        return {"status": "success", "player_id": pid, "vehicles": vehicles, "count": len(vehicles), "balance": bal}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@command("vehicleshop.get_catalog", "Get full shop catalog (categories + vehicles)", category="player")
def vehicleshop_get_catalog() -> dict:
    cat = get_catalog()
    return {"status": "success", "catalog": cat}

@command("vehicleshop.open", "Open vehicle shop (returns catalog for UI)", category="player")
def vehicleshop_open() -> dict:
    cat = get_catalog()
    # also include balance for player 1 as convenience
    try:
        from core.systems.economy.wallet import get_balance
        bal = get_balance(1)
    except Exception:
        bal = None
    try:
        from core.systems.player.ownership import get_owned_vehicles
        owned = get_owned_vehicles(1)
    except Exception:
        owned = []
    return {"status": "success", "catalog": cat, "balance": bal, "owned_count": len(owned), "message": "Shop opened"}

# alias without dot for direct /vehicleshop (but command registry requires dot — so we provide both)
# Dashboard JS will intercept /vehicleshop as builtin and then call vehicleshop.open via bridge.
# For completeness, also register slash variant via explicit lower check is not needed; we just ensure
# the command list includes vehicleshop.open so help shows.

# Ensure catalog loads on import so dashboard can query immediately
try:
    _ensure_loaded()
except Exception:
    pass

__all__ = [
    "CategoryDef", "VehicleDef",
    "get_categories", "get_vehicles", "get_vehicle", "get_vehicle_dict", "get_catalog", "search_vehicles",
    "buy_vehicle", "sell_vehicle",
]
