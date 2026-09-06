"""
Real Estate — MTT Property & Business System

Manages:
 - Catalog of properties (data/properties.xml): houses, apartments, vacant land, farms, businesses
 - Catalog of agents (data/realestate_agents.xml): different fees/ratings per agent
 - Player ownership (buy / rent), garage vehicle storage with parking capacity checks
 - Save/load via save registry (key: "realestate")

Designed to mirror vehicle_shop.py patterns so the future game can do:
    from core.systems.realestate.realestate import (
        get_properties, get_property, get_agents, buy_property, rent_property,
        store_vehicle, retrieve_vehicle, get_catalog
    )

Commands (autodiscovered):
 - realestate.list_properties  (filter by type, for_sale, for_rent, available)
 - realestate.list_agents
 - realestate.info             (property details)
 - realestate.agent_info       (agent details)
 - realestate.buy              (buy with wallet or card — enforces bank limits via card)
 - realestate.rent             (rent weekly price, lease 30 days)
 - realestate.owned            (list owned / rented for player)
 - realestate.sell             (sell owned property, refund 75%)
 - realestate.cancel_rent      (cancel rental)
 - realestate.store_vehicle    (park a owned vehicle at a property if capacity)
 - realestate.retrieve_vehicle (remove from garage)
 - realestate.garage           (list vehicles at one property)
 - realestate.garages          (list all garages for player)
 - realestate.open / realestate.get_catalog / realestate.view (full catalog + balance)

Garage rules:
 - total capacity = stats.parking + stats.garage_spaces (any property can store if >0)
 - 0 capacity -> cannot store (e.g. Budget Studio with 0 spaces)
 - Vehicle must be owned (via ownership.py) and not already stored elsewhere

Future businesses reuse same properties with type="business" / "commercial" and can gain
extra stats like income_per_day once that system is built.
"""

from __future__ import annotations

import time
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
class AgentDef:
    id: str
    name: str
    display: str = ""
    rating: float = 0.0
    fee_percent: float = 0.0
    phone: str = ""
    specialty: str = ""
    agency: str = ""
    description: str = ""
    color: str = "#334155"
    icon: str = "fa-handshake"

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class PropertyDef:
    id: str
    name: str
    type: str                  # house, apartment, vacant_land, business, commercial, farm
    agent_id: str = ""
    location: str = ""
    for_sale: bool = True
    for_rent: bool = False
    price: int = 0
    rent_price: int = 0
    image: str = ""            # placeholder key for UI
    description: str = ""
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def capacity(self) -> int:
        """Total vehicle slots = parking + garage_spaces (stats may have either)."""
        try:
            parking = int(self.stats.get("parking", 0) or 0)
        except Exception:
            parking = 0
        try:
            garage = int(self.stats.get("garage_spaces", 0) or 0)
        except Exception:
            # also check shed_capacity alias for farm
            try:
                garage = int(self.stats.get("shed_capacity", 0) or 0)
            except Exception:
                garage = 0
            # if farm has shed_capacity we already have it, but also add garage_spaces
            # for farm green_acres stats has both, we use garage_spaces primarily
            if "garage_spaces" in self.stats:
                try:
                    garage = int(self.stats.get("garage_spaces", 0) or 0)
                except Exception:
                    pass
        return max(0, parking + garage)

    @property
    def is_vacant(self) -> bool:
        v = self.stats.get("vacant", False)
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes")
        return bool(v)

@dataclass
class OwnedProperty:
    property_id: str
    name: str
    type: str
    agent_id: str
    location: str
    price_paid: int
    fee_paid: int
    total_paid: int
    tenure: str = "owned"              # "owned" or "rented"
    acquired_at: float = field(default_factory=lambda: time.time())
    lease_start: Optional[float] = None
    lease_end: Optional[float] = None  # for rented only (30 days default)
    rent_price: int = 0
    stats: Dict[str, Any] = field(default_factory=dict)
    stored_vehicles: List[str] = field(default_factory=list)  # instance_ids
    description: str = ""
    image: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "OwnedProperty":
        return cls(
            property_id=str(data.get("property_id", "")),
            name=str(data.get("name", "")),
            type=str(data.get("type", "")),
            agent_id=str(data.get("agent_id", "")),
            location=str(data.get("location", "")),
            price_paid=int(data.get("price_paid", 0)),
            fee_paid=int(data.get("fee_paid", 0)),
            total_paid=int(data.get("total_paid", 0)),
            tenure=str(data.get("tenure", "owned")),
            acquired_at=float(data.get("acquired_at", time.time())),
            lease_start=float(data["lease_start"]) if data.get("lease_start") is not None else None,
            lease_end=float(data["lease_end"]) if data.get("lease_end") is not None else None,
            rent_price=int(data.get("rent_price", 0)),
            stats=dict(data.get("stats", {})) if isinstance(data.get("stats"), dict) else {},
            stored_vehicles=list(data.get("stored_vehicles", [])) if isinstance(data.get("stored_vehicles"), list) else [],
            description=str(data.get("description", "")),
            image=str(data.get("image", "")),
        )

    @property
    def capacity(self) -> int:
        try:
            parking = int(self.stats.get("parking", 0) or 0)
        except Exception:
            parking = 0
        try:
            garage = int(self.stats.get("garage_spaces", 0) or 0)
        except Exception:
            garage = 0
            if "shed_capacity" in self.stats:
                try:
                    garage = int(self.stats.get("shed_capacity", 0) or 0)
                except Exception:
                    pass
            if "garage_spaces" in self.stats:
                try:
                    garage = int(self.stats.get("garage_spaces", 0) or 0)
                except Exception:
                    pass
        return max(0, parking + garage)


# ---------------------------------------------------------------------------
# Catalog loader (data/properties.xml + data/realestate_agents.xml)
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PROPERTIES = _PROJECT_ROOT / "data" / "properties.xml"
DEFAULT_AGENTS = _PROJECT_ROOT / "data" / "realestate_agents.xml"

_agents: List[AgentDef] = []
_agents_by_id: Dict[str, AgentDef] = {}

_properties: List[PropertyDef] = []
_properties_by_id: Dict[str, PropertyDef] = {}
_by_type: Dict[str, List[PropertyDef]] = {}
_by_agent: Dict[str, List[PropertyDef]] = {}

_loaded: bool = False
_load_error: Optional[str] = None

def _parse_bool(v: str) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes", "y")

def _load_catalog(prop_path: Optional[Path] = None, agents_path: Optional[Path] = None) -> None:
    global _agents, _agents_by_id, _properties, _properties_by_id, _by_type, _by_agent, _loaded, _load_error
    if _loaded:
        return
    _agents = []
    _agents_by_id = {}
    _properties = []
    _properties_by_id = {}
    _by_type = {}
    _by_agent = {}
    _load_error = None

    # ---- agents ----
    ap = Path(agents_path) if agents_path else DEFAULT_AGENTS
    if not ap.exists():
        _warn(f"Real estate agents catalog not found: {ap}, using fallback agents")
        _seed_fallback_agents()
    else:
        try:
            tree = ET.parse(str(ap))
            root = tree.getroot()
            for a in root.findall("agent"):
                try:
                    aid = (a.get("id") or "").strip()
                    if not aid:
                        continue
                    name = (a.get("name") or a.get("display") or aid).strip()
                    display = (a.get("display") or name).strip()
                    rating_raw = (a.get("rating") or "0").strip()
                    fee_raw = (a.get("fee_percent") or "0").strip()
                    try:
                        rating = float(rating_raw)
                    except Exception:
                        rating = 0.0
                    try:
                        fee = float(fee_raw)
                    except Exception:
                        fee = 0.0
                    ag = AgentDef(
                        id=aid,
                        name=name,
                        display=display,
                        rating=rating,
                        fee_percent=fee,
                        phone=(a.get("phone") or "").strip(),
                        specialty=(a.get("specialty") or "").strip(),
                        agency=(a.get("agency") or "").strip(),
                        description=(a.get("description") or "").strip(),
                        color=(a.get("color") or "#334155").strip(),
                        icon=(a.get("icon") or "fa-handshake").strip(),
                    )
                    _agents.append(ag)
                    _agents_by_id[aid.lower()] = ag
                except Exception as e:
                    _warn(f"skip bad agent: {e}")
            if not _agents:
                _warn("No agents in realestate_agents.xml, seeding fallback")
                _seed_fallback_agents()
        except Exception as e:
            _load_error = str(e)
            _warn(f"Failed to load agents {ap}: {e}")
            _seed_fallback_agents()

    # ---- properties ----
    pp = Path(prop_path) if prop_path else DEFAULT_PROPERTIES
    if not pp.exists():
        _load_error = f"Properties catalog not found: {pp}"
        _warn(_load_error)
        _seed_fallback_properties()
        _loaded = True
        _build_indices()
        return
    try:
        tree = ET.parse(str(pp))
        root = tree.getroot()
        for p in root.findall("property"):
            try:
                pid = (p.get("id") or "").strip()
                if not pid:
                    # also try child <id>
                    pid = (p.findtext("id") or "").strip()
                    if not pid:
                        continue
                name = (p.get("name") or p.findtext("name") or pid).strip()
                ptype = (p.get("type") or p.findtext("type") or "house").strip().lower()
                agent_id = (p.get("agent_id") or p.findtext("agent_id") or "").strip()
                location = (p.get("location") or p.findtext("location") or "").strip()
                for_sale = _parse_bool(p.get("for_sale") or p.findtext("for_sale") or "true")
                for_rent = _parse_bool(p.get("for_rent") or p.findtext("for_rent") or "false")
                price_raw = (p.get("price") or p.findtext("price") or "0").strip()
                rent_raw = (p.get("rent_price") or p.findtext("rent_price") or "0").strip()
                try:
                    price = int(float(price_raw)) if price_raw else 0
                except Exception:
                    price = 0
                try:
                    rent_price = int(float(rent_raw)) if rent_raw else 0
                except Exception:
                    rent_price = 0
                image = (p.get("image") or p.findtext("image") or "").strip()
                desc = (p.get("description") or p.findtext("description") or "").strip()
                # stats
                stats: Dict[str, Any] = {}
                stats_el = p.find("stats")
                if stats_el is not None:
                    for s in stats_el:
                        tag = (s.tag or "").strip()
                        txt = (s.text or "").strip()
                        if not tag:
                            continue
                        # coerce
                        # keep booleans as bool, try int/float
                        low = txt.lower()
                        if low in ("true", "false"):
                            stats[tag] = low == "true"
                        else:
                            try:
                                if txt == "":
                                    stats[tag] = ""
                                elif "." in txt:
                                    # try float, fallback string
                                    stats[tag] = float(txt)
                                    # if int-like float, keep int?
                                    if stats[tag].is_integer():
                                        stats[tag] = int(stats[tag])
                                else:
                                    stats[tag] = int(txt)
                            except Exception:
                                stats[tag] = txt
                        # also try to keep condition as string
                        if tag == "condition":
                            stats[tag] = txt
                        if tag == "business_type":
                            stats[tag] = txt
                pd = PropertyDef(
                    id=pid,
                    name=name,
                    type=ptype,
                    agent_id=agent_id,
                    location=location,
                    for_sale=for_sale,
                    for_rent=for_rent,
                    price=price,
                    rent_price=rent_price,
                    image=image,
                    description=desc,
                    stats=stats,
                )
                if not pid:
                    continue
                _properties.append(pd)
                _properties_by_id[pid.lower()] = pd
            except Exception as e:
                _warn(f"skip bad property: {e}")
        _build_indices()
        _loaded = True
        if not _properties:
            _warn("No properties in properties.xml, seeding fallback")
            _seed_fallback_properties()
            _build_indices()
    except Exception as e:
        _load_error = str(e)
        _warn(f"Failed to load properties {pp}: {e}")
        _seed_fallback_properties()
        _build_indices()
        _loaded = True

def _build_indices():
    global _by_type, _by_agent
    _by_type = {}
    _by_agent = {}
    for pd in _properties:
        key = pd.type.lower()
        _by_type.setdefault(key, []).append(pd)
        ak = pd.agent_id.lower()
        if ak:
            _by_agent.setdefault(ak, []).append(pd)

def _seed_fallback_agents():
    global _agents, _agents_by_id
    if _agents:
        return
    _agents = [
        AgentDef(id="agent_sunny_estate", name="Sunny Estate Co.", display="Sunny Estate Co.", rating=4.8, fee_percent=2.5, phone="555-0101", specialty="house,apartment", agency="Sunny Group", description="Fallback agent", color="#f59e0b"),
        AgentDef(id="agent_budget_homes", name="Budget Homes Direct", display="Budget Homes", rating=3.6, fee_percent=1.0, phone="555-0104", specialty="house,apartment", agency="Budget Direct", description="Fallback budget agent", color="#6b7280"),
    ]
    _agents_by_id = {a.id.lower(): a for a in _agents}

def _seed_fallback_properties():
    global _properties, _properties_by_id
    if _properties:
        return
    _properties = [
        PropertyDef(id="house_maple_12", name="12 Maple Street", type="house", agent_id="agent_sunny_estate", location="Maple District", for_sale=True, for_rent=False, price=145000, rent_price=0, image="house", description="Fallback house", stats={"beds": 3, "baths": 1, "parking": 1, "garage_spaces": 1, "land_sqm": 620, "vacant": False}),
    ]
    _properties_by_id = {p.id.lower(): p for p in _properties}

def _ensure_loaded():
    if not _loaded:
        _load_catalog()

def reload_catalog(prop_path: Optional[str] = None, agents_path: Optional[str] = None) -> dict:
    """Force reload (for tests / admin)."""
    global _loaded
    _loaded = False
    _load_catalog(Path(prop_path) if prop_path else None, Path(agents_path) if agents_path else None)
    return {"agents": len(_agents), "properties": len(_properties), "error": _load_error}


# ---------------------------------------------------------------------------
# Public catalog API
# ---------------------------------------------------------------------------

def get_agents() -> List[Dict[str, Any]]:
    _ensure_loaded()
    return [a.to_dict() for a in _agents]

def get_agent(agent_id: str) -> Optional[AgentDef]:
    _ensure_loaded()
    if not agent_id:
        return None
    return _agents_by_id.get(str(agent_id).strip().lower())

def get_agent_dict(agent_id: str) -> Optional[dict]:
    a = get_agent(agent_id)
    return a.to_dict() if a else None

def get_properties(
    type_filter: Optional[str] = None,
    for_sale: Optional[bool] = None,
    for_rent: Optional[bool] = None,
    available_only: bool = False,
) -> List[Dict[str, Any]]:
    _ensure_loaded()
    lst = list(_properties)
    if type_filter and str(type_filter).strip():
        key = str(type_filter).strip().lower()
        lst = [p for p in lst if p.type.lower() == key]
    if for_sale is not None:
        lst = [p for p in lst if p.for_sale == bool(for_sale)]
    if for_rent is not None:
        lst = [p for p in lst if p.for_rent == bool(for_rent)]
    if available_only:
        lst = [p for p in lst if is_available(p.id)]
    return [p.to_dict() for p in lst]

def get_property(property_id: str) -> Optional[PropertyDef]:
    _ensure_loaded()
    if not property_id:
        return None
    return _properties_by_id.get(str(property_id).strip().lower())

def get_property_dict(property_id: str) -> Optional[dict]:
    p = get_property(property_id)
    return p.to_dict() if p else None

def get_catalog() -> dict:
    _ensure_loaded()
    counts_by_type: Dict[str, int] = {}
    for pd in _properties:
        counts_by_type[pd.type] = counts_by_type.get(pd.type, 0) + 1
    counts_by_agent: Dict[str, int] = {}
    for pd in _properties:
        counts_by_agent[pd.agent_id] = counts_by_agent.get(pd.agent_id, 0) + 1
    return {
        "agents": [a.to_dict() for a in _agents],
        "properties": [p.to_dict() for p in _properties],
        "counts_by_type": counts_by_type,
        "counts_by_agent": counts_by_agent,
        "total_agents": len(_agents),
        "total_properties": len(_properties),
        "load_error": _load_error,
    }

def search_properties(query: str) -> List[Dict[str, Any]]:
    _ensure_loaded()
    q = (query or "").strip().lower()
    if not q:
        return []
    out = []
    for p in _properties:
        hay = f"{p.id} {p.name} {p.type} {p.location} {p.description}".lower()
        if q in hay:
            out.append(p.to_dict())
    return out

def search_agents(query: str) -> List[Dict[str, Any]]:
    _ensure_loaded()
    q = (query or "").strip().lower()
    if not q:
        return []
    out = []
    for a in _agents:
        hay = f"{a.id} {a.name} {a.display} {a.agency} {a.specialty}".lower()
        if q in hay:
            out.append(a.to_dict())
    return out


# ---------------------------------------------------------------------------
# Ownership + Garage
# ---------------------------------------------------------------------------

# player_id -> list[OwnedProperty]
_owned: Dict[int, List[OwnedProperty]] = {}

def _ensure_owned_list(player_id: int) -> List[OwnedProperty]:
    pid = int(player_id)
    if pid not in _owned:
        _owned[pid] = []
    return _owned[pid]

def _find_owned(player_id: int, property_id: str) -> Optional[OwnedProperty]:
    pid = int(player_id)
    lst = _owned.get(pid, [])
    low = str(property_id).strip().lower()
    for op in lst:
        if op.property_id.lower() == low:
            return op
    return None

def _find_owner_global(property_id: str) -> Optional[int]:
    """Return player_id who currently owns (bought) or rents this property globally, or None if available."""
    low = str(property_id).strip().lower()
    for pid, lst in _owned.items():
        for op in lst:
            if op.property_id.lower() == low:
                # if rent expired, treat as available? expire leases
                if op.tenure == "rented" and op.lease_end is not None and op.lease_end < time.time():
                    # expired — treat as free (caller should cleanup but for availability check it's free)
                    continue
                return pid
    return None

def is_available(property_id: str) -> bool:
    """True if property not currently owned/rented by anyone."""
    return _find_owner_global(property_id) is None

def is_owned_by(player_id: int, property_id: str) -> bool:
    return _find_owned(player_id, property_id) is not None

def get_owned_properties(player_id: int) -> List[Dict[str, Any]]:
    pid = int(player_id)
    return [op.to_dict() for op in _owned.get(pid, [])]

def list_owned_properties(player_id: int) -> List[OwnedProperty]:
    return list(_owned.get(int(player_id), []))

def clear_owned(player_id: Optional[int] = None) -> int:
    if player_id is None:
        n = sum(len(v) for v in _owned.values())
        _owned.clear()
        return n
    pid = int(player_id)
    n = len(_owned.get(pid, []))
    _owned.pop(pid, None)
    return n

def _agent_fee(agent_id: str, amount: int) -> int:
    ag = get_agent(agent_id)
    if not ag:
        return 0
    try:
        return int(round(float(amount) * float(ag.fee_percent) / 100.0))
    except Exception:
        return 0

def _cleanup_expired_rentals():
    """Remove expired rentals (lease_end < now). Called lazily."""
    now = time.time()
    for pid, lst in list(_owned.items()):
        keep = []
        for op in lst:
            if op.tenure == "rented" and op.lease_end is not None and op.lease_end < now:
                # expire: also need to handle stored vehicles? move them out? For now clear stored_vehicles and drop ownership
                # vehicles stay in ownership but are no longer parked — they become un-stored.
                # We don't delete vehicle, just property. Stored vehicles become "homeless" but still owned.
                continue
            keep.append(op)
        _owned[pid] = keep

# ---- buy / rent / sell ----

def buy_property(player_id: int, property_id: str, card_id: Optional[str] = None, payment_method: Optional[str] = None) -> dict:
    _ensure_loaded()
    _cleanup_expired_rentals()
    pid = int(player_id)
    vid = str(property_id).strip()
    if not vid:
        return {"status": "error", "message": "property_id required"}
    # flexible card alias
    chosen_card = (card_id or payment_method or "").strip() or None
    if not vid:
        return {"status": "error", "message": "property_id required"}
    pdef = get_property(vid)
    if pdef is None:
        # try fuzzy search
        matches = search_properties(vid)
        if len(matches) == 1:
            pdef = get_property(matches[0]["id"])
        if pdef is None:
            sugg = ", ".join(m["id"] for m in search_properties(vid)[:3])
            hint = f" Did you mean: {sugg}?" if sugg else ""
            return {"status": "error", "message": f"Unknown property '{property_id}'.{hint}"}
    if not pdef.for_sale:
        return {"status": "error", "message": f"Property '{pdef.name}' is not for sale (try renting if for_rent)"}
    if not is_available(pdef.id):
        owner = _find_owner_global(pdef.id)
        return {"status": "error", "message": f"Property '{pdef.name}' is already owned by player {owner}"}
    if pdef.price <= 0:
        return {"status": "error", "message": f"Property '{pdef.name}' has no buy price configured"}
    fee = _agent_fee(pdef.agent_id, pdef.price)
    total = int(pdef.price) + int(fee)

    # payment
    new_bal = None
    payment_info: Dict[str, Any] = {}
    if chosen_card:
        try:
            from core.systems.economy.bank import pay_with_card
            pay_res = pay_with_card(pid, str(chosen_card), float(total), description=f"Property {pdef.name}")
            if pay_res.get("status") != "success":
                return {"status": "error", "message": pay_res.get("message", "Transaction Failed"), "price": pdef.price, "fee": fee, "total": total, "card": pay_res.get("card")}
            payment_info = {"card": pay_res.get("card"), "type": pay_res.get("type")}
            if pay_res.get("type") == "debit":
                try:
                    from core.systems.economy.wallet import get_balance
                    new_bal = get_balance(pid)
                except Exception:
                    new_bal = None
            else:
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
        try:
            from core.systems.economy.wallet import get_balance, deduct_funds
            bal = get_balance(pid)
            if bal + 1e-9 < total:
                return {"status": "error", "message": f"Insufficient funds: need ${total:,} (${pdef.price:,}+${fee:,} fee), have ${bal:,.0f}", "balance": bal, "price": pdef.price, "fee": fee, "total": total}
            ok = deduct_funds(pid, float(total))
            if not ok:
                return {"status": "error", "message": f"Insufficient funds: need ${total:,} (${pdef.price:,}+${fee:,} fee)", "balance": bal}
            new_bal = get_balance(pid)
        except ImportError:
            new_bal = None

    # create owned
    op = OwnedProperty(
        property_id=pdef.id,
        name=pdef.name,
        type=pdef.type,
        agent_id=pdef.agent_id,
        location=pdef.location,
        price_paid=int(pdef.price),
        fee_paid=int(fee),
        total_paid=int(total),
        tenure="owned",
        acquired_at=time.time(),
        lease_start=None,
        lease_end=None,
        rent_price=int(pdef.rent_price),
        stats=dict(pdef.stats),
        stored_vehicles=[],
        description=pdef.description,
        image=pdef.image,
    )
    _ensure_owned_list(pid).append(op)
    try:
        _success(f"Player {pid} bought {pdef.name} ({pdef.id}) for ${pdef.price:,} + ${fee:,} fee via {payment_info.get('type','wallet')}", source="realestate")
    except Exception:
        pass
    out: Dict[str, Any] = {"status": "success", "message": f"Bought {pdef.name} for ${pdef.price:,} + ${fee:,} fee = ${total:,}", "property": op.to_dict(), "balance": new_bal, "price": pdef.price, "fee": fee, "total": total}
    if payment_info:
        out["payment"] = payment_info
    return out

def rent_property(player_id: int, property_id: str, card_id: Optional[str] = None, payment_method: Optional[str] = None, lease_days: int = 30) -> dict:
    _ensure_loaded()
    _cleanup_expired_rentals()
    pid = int(player_id)
    vid = str(property_id).strip()
    if not vid:
        return {"status": "error", "message": "property_id required"}
    chosen_card = (card_id or payment_method or "").strip() or None
    pdef = get_property(vid)
    if pdef is None:
        matches = search_properties(vid)
        if len(matches) == 1:
            pdef = get_property(matches[0]["id"])
        if pdef is None:
            return {"status": "error", "message": f"Unknown property '{property_id}'"}
    if not pdef.for_rent:
        return {"status": "error", "message": f"Property '{pdef.name}' is not for rent"}
    if not is_available(pdef.id):
        owner = _find_owner_global(pdef.id)
        return {"status": "error", "message": f"Property '{pdef.name}' is already owned/rented by player {owner}"}
    if pdef.rent_price <= 0:
        return {"status": "error", "message": f"Property '{pdef.name}' has no rent price configured"}
    fee = _agent_fee(pdef.agent_id, pdef.rent_price)
    total = int(pdef.rent_price) + int(fee)
    # payment
    new_bal = None
    payment_info: Dict[str, Any] = {}
    if chosen_card:
        try:
            from core.systems.economy.bank import pay_with_card
            pay_res = pay_with_card(pid, str(chosen_card), float(total), description=f"Rent {pdef.name} ({lease_days}d)")
            if pay_res.get("status") != "success":
                return {"status": "error", "message": pay_res.get("message", "Transaction Failed"), "rent_price": pdef.rent_price, "fee": fee, "total": total, "card": pay_res.get("card")}
            payment_info = {"card": pay_res.get("card"), "type": pay_res.get("type")}
            try:
                from core.systems.economy.wallet import get_balance
                new_bal = get_balance(pid)
            except Exception:
                new_bal = None
            if pay_res.get("type") == "credit":
                payment_info["debt"] = pay_res.get("debt")
                payment_info["available"] = pay_res.get("available")
        except Exception as e:
            return {"status": "error", "message": f"Card payment failed: {e}"}
    else:
        try:
            from core.systems.economy.wallet import get_balance, deduct_funds
            bal = get_balance(pid)
            if bal + 1e-9 < total:
                return {"status": "error", "message": f"Insufficient funds: need ${total:,} (${pdef.rent_price:,}+${fee:,} fee), have ${bal:,.0f}", "balance": bal, "rent_price": pdef.rent_price, "fee": fee, "total": total}
            ok = deduct_funds(pid, float(total))
            if not ok:
                return {"status": "error", "message": f"Insufficient funds: need ${total:,}", "balance": bal}
            new_bal = get_balance(pid)
        except ImportError:
            new_bal = None
    lease_start = time.time()
    lease_end = lease_start + int(lease_days) * 24 * 3600
    op = OwnedProperty(
        property_id=pdef.id,
        name=pdef.name,
        type=pdef.type,
        agent_id=pdef.agent_id,
        location=pdef.location,
        price_paid=int(pdef.rent_price),
        fee_paid=int(fee),
        total_paid=int(total),
        tenure="rented",
        acquired_at=lease_start,
        lease_start=lease_start,
        lease_end=lease_end,
        rent_price=int(pdef.rent_price),
        stats=dict(pdef.stats),
        stored_vehicles=[],
        description=pdef.description,
        image=pdef.image,
    )
    _ensure_owned_list(pid).append(op)
    try:
        _success(f"Player {pid} rented {pdef.name} for {lease_days} days — ${pdef.rent_price:,}+${fee:,} fee", source="realestate")
    except Exception:
        pass
    out: Dict[str, Any] = {"status": "success", "message": f"Rented {pdef.name} for {lease_days} days (${pdef.rent_price:,}+${fee:,} fee = ${total:,})", "property": op.to_dict(), "balance": new_bal, "rent_price": pdef.rent_price, "fee": fee, "total": total, "lease_days": lease_days, "lease_end": lease_end}
    if payment_info:
        out["payment"] = payment_info
    return out

def sell_property(player_id: int, property_id: str, refund_ratio: float = 0.75) -> dict:
    _ensure_loaded()
    pid = int(player_id)
    vid = str(property_id).strip()
    if not vid:
        return {"status": "error", "message": "property_id required (from realestate.owned)"}
    if not (0 < refund_ratio <= 1):
        refund_ratio = 0.75
    op = _find_owned(pid, vid)
    if op is None:
        # try case insensitive search already handled; fallback list
        return {"status": "error", "message": f"Not owned: '{property_id}'. Use realestate.owned to list."}
    if op.tenure == "rented":
        return {"status": "error", "message": f"Property '{op.name}' is rented, not owned — use realestate.cancel_rent to end rental (no refund)"}
    # remove
    lst = _owned.get(pid, [])
    # also clear stored vehicles? they become un-stored but stay owned
    stored_count = len(op.stored_vehicles)
    # detach vehicles: they remain in ownership but are no longer parked
    for iid in list(op.stored_vehicles):
        op.stored_vehicles.remove(iid)
    # remove owned entry
    for i, o in enumerate(lst):
        if o.property_id.lower() == vid.lower():
            del lst[i]
            break
    refund = int(round(op.price_paid * refund_ratio))
    try:
        from core.systems.economy.wallet import add_funds, get_balance
        new_bal = add_funds(pid, float(refund))
        _success(f"Player {pid} sold {op.name} ({op.property_id}) for ${refund:,} (stored vehicles freed: {stored_count})", source="realestate")
        return {"status": "success", "message": f"Sold {op.name} for ${refund:,} (refund {refund_ratio*100:.0f}%, vehicles freed: {stored_count})", "refund": refund, "balance": new_bal, "property_id": op.property_id, "vehicles_freed": stored_count}
    except ImportError:
        _success(f"Player {pid} sold {op.name} ({op.property_id})", source="realestate")
        return {"status": "success", "message": f"Sold {op.name}", "refund": refund, "property_id": op.property_id}

def cancel_rent(player_id: int, property_id: str) -> dict:
    pid = int(player_id)
    vid = str(property_id).strip()
    if not vid:
        return {"status": "error", "message": "property_id required"}
    op = _find_owned(pid, vid)
    if op is None:
        return {"status": "error", "message": f"Not rented: '{property_id}'"}
    if op.tenure != "rented":
        return {"status": "error", "message": f"Property '{op.name}' is owned, not rented — use realestate.sell"}
    # free stored vehicles
    stored_count = len(op.stored_vehicles)
    lst = _owned.get(pid, [])
    for i, o in enumerate(lst):
        if o.property_id.lower() == vid.lower():
            del lst[i]
            break
    _success(f"Player {pid} cancelled rent on {op.name} (vehicles freed: {stored_count})", source="realestate")
    return {"status": "success", "message": f"Cancelled rent on {op.name} (vehicles freed: {stored_count})", "property_id": op.property_id, "vehicles_freed": stored_count}

# ---- garage management ----

def _find_property_garage_conflict(instance_id: str) -> Optional[tuple[int, str]]:
    """Find which player/property currently stores instance_id, if any."""
    iid = str(instance_id).strip()
    for pid, lst in _owned.items():
        for op in lst:
            if iid in op.stored_vehicles:
                return (pid, op.property_id)
    return None

def store_vehicle(player_id: int, property_id: str, instance_id: str) -> dict:
    _ensure_loaded()
    _cleanup_expired_rentals()
    pid = int(player_id)
    prop_id = str(property_id).strip()
    iid = str(instance_id).strip()
    if not prop_id or not iid:
        return {"status": "error", "message": "property_id and instance_id required (instance_id from vehicleshop.owned or ownership.list)"}
    op = _find_owned(pid, prop_id)
    if op is None:
        return {"status": "error", "message": f"Player {pid} does not own/rent property '{prop_id}'. Use realestate.owned to list."}
    if iid in op.stored_vehicles:
        return {"status": "error", "message": f"Vehicle {iid} already stored at '{op.name}'"}
    # check global conflict before capacity — more specific error
    conflict = _find_property_garage_conflict(iid)
    if conflict is not None:
        cpid, cprop = conflict
        return {"status": "error", "message": f"Vehicle {iid} already stored at property '{cprop}' (player {cpid}) — retrieve it first"}
    cap = op.capacity
    if cap <= 0:
        return {"status": "error", "message": f"Property '{op.name}' has no parking/garage spaces (parking={op.stats.get('parking',0)}, garage={op.stats.get('garage_spaces',0)}) — cannot store vehicles"}
    if len(op.stored_vehicles) >= cap:
        return {"status": "error", "message": f"Garage full at '{op.name}': {len(op.stored_vehicles)}/{cap} spaces used"}
    # verify vehicle ownership via ownership system
    try:
        from core.systems.player.ownership import list_owned_vehicles as _list_ov
        owned_vs = _list_ov(pid)
        owned_ids = {ov.instance_id for ov in owned_vs}
        # also allow vehicle_id shorthand? no, garage must store instance_id
        if iid not in owned_ids:
            # try vehicle_id fallback suggestions
            from core.systems.player.ownership import get_owned_vehicles as _gov
            vs = _gov(pid)
            sugg = ", ".join(v["instance_id"] for v in vs[:3]) if vs else ""
            hint = f" Owned: {sugg}" if sugg else ""
            return {"status": "error", "message": f"Player {pid} does not own vehicle '{iid}'.{hint}"}
    except ImportError:
        # if ownership not available, skip check
        pass
    op.stored_vehicles.append(iid)
    _success(f"Stored {iid} at {op.name} ({len(op.stored_vehicles)}/{cap})", source="realestate")
    return {"status": "success", "message": f"Stored {iid} at '{op.name}' ({len(op.stored_vehicles)}/{cap})", "property_id": op.property_id, "capacity": cap, "used": len(op.stored_vehicles), "stored": list(op.stored_vehicles)}

def retrieve_vehicle(player_id: int, property_id: str = "", instance_id: str = "") -> dict:
    """
    Retrieve a vehicle from a property garage.
    If property_id is given, removes from that property only. Otherwise searches all player garages.
    """
    pid = int(player_id)
    iid = str(instance_id).strip()
    prop_id = str(property_id).strip() if property_id else ""
    # flexible positional: if property_id looks like instance_id and instance_id empty
    if not iid and prop_id:
        # called as retrieve(player_id, instance_id) via second arg
        iid = prop_id
        prop_id = ""
    if not iid:
        return {"status": "error", "message": "instance_id required"}
    # if property specified, only there
    if prop_id:
        op = _find_owned(pid, prop_id)
        if op is None:
            return {"status": "error", "message": f"Player {pid} does not own property '{prop_id}'"}
        if iid not in op.stored_vehicles:
            return {"status": "error", "message": f"Vehicle {iid} not stored at '{op.name}' (stored: {op.stored_vehicles})"}
        op.stored_vehicles.remove(iid)
        _success(f"Retrieved {iid} from {op.name} ({len(op.stored_vehicles)}/{op.capacity})", source="realestate")
        return {"status": "success", "message": f"Retrieved {iid} from '{op.name}'", "property_id": op.property_id, "stored": list(op.stored_vehicles)}
    # no property given: search all
    for op in _owned.get(pid, []):
        if iid in op.stored_vehicles:
            op.stored_vehicles.remove(iid)
            _success(f"Retrieved {iid} from {op.name}", source="realestate")
            return {"status": "success", "message": f"Retrieved {iid} from '{op.name}'", "property_id": op.property_id, "stored": list(op.stored_vehicles)}
    return {"status": "error", "message": f"Vehicle {iid} not found in any of your garages. Use realestate.garages to list."}

def garage_list(player_id: int, property_id: str) -> dict:
    pid = int(player_id)
    prop_id = str(property_id).strip()
    if not prop_id:
        return {"status": "error", "message": "property_id required"}
    op = _find_owned(pid, prop_id)
    if op is None:
        return {"status": "error", "message": f"Player {pid} does not own/rent '{prop_id}'"}
    # enrich stored vehicles with names if possible
    stored_details: List[Dict[str, Any]] = []
    try:
        from core.systems.player.ownership import list_owned_vehicles as _list_ov
        owned_map = {ov.instance_id: ov for ov in _list_ov(pid)}
        for iid in op.stored_vehicles:
            ov = owned_map.get(iid)
            if ov:
                stored_details.append({"instance_id": iid, "name": ov.name, "vehicle_id": ov.vehicle_id, "license_plate": ov.license_plate, "stats": ov.stats})
            else:
                stored_details.append({"instance_id": iid, "name": "Unknown (not in ownership)", "vehicle_id": "", "license_plate": None})
    except Exception:
        stored_details = [{"instance_id": iid} for iid in op.stored_vehicles]
    return {"status": "success", "property_id": op.property_id, "name": op.name, "capacity": op.capacity, "used": len(op.stored_vehicles), "stored": list(op.stored_vehicles), "stored_details": stored_details, "stats": op.stats}

def garages_all(player_id: int) -> dict:
    pid = int(player_id)
    lst = _owned.get(pid, [])
    garages = []
    total_cap = 0
    total_used = 0
    for op in lst:
        cap = op.capacity
        used = len(op.stored_vehicles)
        total_cap += cap
        total_used += used
        garages.append({
            "property_id": op.property_id,
            "name": op.name,
            "type": op.type,
            "capacity": cap,
            "used": used,
            "available": max(0, cap - used),
            "stored": list(op.stored_vehicles),
            "location": op.location,
            "tenure": op.tenure,
            "stats": dict(op.stats),
        })
    return {"status": "success", "player_id": pid, "garages": garages, "total_capacity": total_cap, "total_used": total_used, "total_available": max(0, total_cap - total_used), "property_count": len(garages)}


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@command("realestate.list_properties", "List properties (filters: type, for_sale, for_rent, available_only)", category="player")
def realestate_list_properties(type: str = "", category: str = "", for_sale: str = "", for_rent: str = "", available_only: bool = False, search: str = "") -> dict:
    # type alias via category param as well
    t = (type or category or "").strip() or None
    # for_sale/for_rent as string bools: "" means no filter
    fs = None
    if isinstance(for_sale, str) and str(for_sale).strip() != "":
        fs = _parse_bool(str(for_sale))
    elif isinstance(for_sale, bool):
        fs = bool(for_sale)
    fr = None
    if isinstance(for_rent, str) and str(for_rent).strip() != "":
        fr = _parse_bool(str(for_rent))
    elif isinstance(for_rent, bool):
        fr = bool(for_rent)
    if search and str(search).strip():
        res = search_properties(str(search))
        # also include availability flag
        for r in res:
            r["available"] = is_available(r["id"])
        return {"status": "success", "properties": res, "count": len(res), "searched": True, "query": str(search)}
    props = get_properties(type_filter=t, for_sale=fs, for_rent=fr, available_only=bool(available_only))
    # add availability + agent info
    for p in props:
        p["available"] = is_available(p["id"])
        ag = get_agent(p.get("agent_id",""))
        p["agent"] = ag.to_dict() if ag else None
        # capacity convenience
        try:
            parking = int(p.get("stats",{}).get("parking",0) or 0)
        except Exception:
            parking = 0
        try:
            garage = int(p.get("stats",{}).get("garage_spaces",0) or 0)
        except Exception:
            garage = 0
        p["capacity"] = parking + garage
    # counts
    _ensure_loaded()
    return {"status": "success", "properties": props, "count": len(props), "filters": {"type": t, "for_sale": fs, "for_rent": fr, "available_only": bool(available_only)}}

@command("realestate.list_agents", "List real estate agents with ratings and fees", category="player")
def realestate_list_agents(search: str = "") -> dict:
    if search and str(search).strip():
        res = search_agents(str(search))
        return {"status": "success", "agents": res, "count": len(res), "searched": True}
    agents = get_agents()
    # include listings count per agent
    for a in agents:
        ak = a["id"].lower()
        # count properties for this agent
        try:
            a["listings"] = len(_by_agent.get(ak, []))
        except Exception:
            a["listings"] = 0
    return {"status": "success", "agents": agents, "count": len(agents)}

@command("realestate.info", "Get property details by id", category="player")
def realestate_info(property_id: str) -> dict:
    if not property_id or not str(property_id).strip():
        return {"status": "error", "message": "property_id required"}
    p = get_property(str(property_id))
    if p is None:
        sugg = search_properties(str(property_id))
        hint = f" Did you mean: {', '.join(x['id'] for x in sugg[:3])}?" if sugg else ""
        return {"status": "error", "message": f"Unknown property '{property_id}'.{hint}"}
    d = p.to_dict()
    d["available"] = is_available(p.id)
    ag = get_agent(p.agent_id)
    d["agent"] = ag.to_dict() if ag else None
    d["capacity"] = p.capacity
    owner = _find_owner_global(p.id)
    d["owned_by"] = owner
    return {"status": "success", "property": d}

@command("realestate.agent_info", "Get agent details by id", category="player")
def realestate_agent_info(agent_id: str) -> dict:
    if not agent_id or not str(agent_id).strip():
        return {"status": "error", "message": "agent_id required"}
    a = get_agent(str(agent_id))
    if a is None:
        sugg = search_agents(str(agent_id))
        hint = f" Did you mean: {', '.join(x['id'] for x in sugg[:3])}?" if sugg else ""
        return {"status": "error", "message": f"Unknown agent '{agent_id}'.{hint}"}
    d = a.to_dict()
    # add listings
    _ensure_loaded()
    d["listings"] = [p.to_dict() for p in _by_agent.get(a.id.lower(), [])]
    d["listings_count"] = len(d["listings"])
    return {"status": "success", "agent": d}

@command("realestate.buy", "Buy a property by id (supports card_id for bank limits)", category="player")
def realestate_buy(player_id: int = 1, property_id: str = "", id: str = "", card_id: str = "", card: str = "", payment_method: str = "") -> dict:
    chosen_card = (card_id or card or payment_method or "").strip() or None
    # flexible positional: if player_id is string and property_id empty
    pid = 1
    vid = ""
    if isinstance(player_id, str) and not property_id and not id:
        vid = player_id
        pid = 1
    elif isinstance(player_id, str) and property_id == "" and id:
        vid = id
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
        vid = (property_id or id or vid or "").strip()
        if not vid and isinstance(player_id, str):
            vid = str(player_id).strip()
    if not vid:
        return {"status": "error", "message": "property_id required. Example: /realestate.buy house_maple_12  or  /realestate.buy player_id=1 property_id=house_maple_12 card_id=card_..."}
    return buy_property(pid, vid, card_id=chosen_card)

@command("realestate.rent", "Rent a property by id (weekly price, 30-day lease, supports card_id)", category="player")
def realestate_rent(player_id: int = 1, property_id: str = "", id: str = "", card_id: str = "", card: str = "", payment_method: str = "", lease_days: int = 30) -> dict:
    chosen_card = (card_id or card or payment_method or "").strip() or None
    try:
        ld = int(lease_days)
    except Exception:
        ld = 30
    if ld <= 0 or ld > 365:
        ld = 30
    pid = 1
    vid = ""
    if isinstance(player_id, str) and not property_id and not id:
        vid = player_id
        pid = 1
    else:
        try:
            pid = int(player_id)
        except Exception:
            pid = 1
            vid = str(player_id)
        vid = (property_id or id or vid or "").strip()
        if not vid and isinstance(player_id, str):
            vid = str(player_id).strip()
    if not vid:
        return {"status": "error", "message": "property_id required. Example: /realestate.rent apt_city_tower_7b"}
    return rent_property(pid, vid, card_id=chosen_card, lease_days=ld)

@command("realestate.owned", "List owned/rented properties for a player", category="player")
def realestate_owned(player_id: int = 1) -> dict:
    try:
        pid = int(player_id)
    except Exception:
        # string player_id maybe property filter? treat as 1
        if isinstance(player_id, str) and player_id.strip().isdigit():
            pid = int(player_id)
        else:
            pid = 1
    _cleanup_expired_rentals()
    props = get_owned_properties(pid)
    # enrich with agent and balances
    try:
        from core.systems.economy.wallet import get_balance
        bal = get_balance(pid)
    except Exception:
        bal = None
    # also compute totals
    total_value = sum(p.get("price_paid", 0) for p in props if p.get("tenure") == "owned")
    total_fees = sum(p.get("fee_paid", 0) for p in props)
    gar = garages_all(pid)
    return {"status": "success", "player_id": pid, "properties": props, "count": len(props), "total_value": total_value, "total_fees": total_fees, "balance": bal, "garages": gar}

# alias for owned
@command("realestate.my_properties", "Alias for realestate.owned", category="player")
def realestate_my_properties(player_id: int = 1) -> dict:
    return realestate_owned(player_id)

@command("realestate.sell", "Sell an owned property (refund 75%)", category="player")
def realestate_sell(player_id: int = 1, property_id: str = "", id: str = "") -> dict:
    pid = 1
    vid = ""
    if isinstance(player_id, str) and not property_id:
        vid = player_id
        pid = 1
    else:
        try:
            pid = int(player_id)
        except Exception:
            pid = 1
            vid = str(player_id)
        vid = (property_id or id or vid or "").strip()
    if not vid:
        return {"status": "error", "message": "property_id required. Use realestate.owned to list. Example: /realestate.sell house_maple_12"}
    return sell_property(pid, vid)

@command("realestate.cancel_rent", "Cancel a rental (no refund, frees garage)", category="player")
def realestate_cancel_rent(player_id: int = 1, property_id: str = "", id: str = "") -> dict:
    pid = 1
    vid = ""
    if isinstance(player_id, str) and not property_id:
        vid = player_id
        pid = 1
    else:
        try:
            pid = int(player_id)
        except Exception:
            pid = 1
            vid = str(player_id)
        vid = (property_id or id or vid or "").strip()
    if not vid:
        return {"status": "error", "message": "property_id required. Use realestate.owned to list."}
    return cancel_rent(pid, vid)

@command("realestate.store_vehicle", "Store an owned vehicle at a property garage (checks parking capacity)", category="player")
def realestate_store_vehicle(player_id: int = 1, property_id: str = "", instance_id: str = "", vehicle_id: str = "") -> dict:
    # support both instance_id and vehicle_id alias + flexible positional
    pid = 1
    prop = ""
    iid = ""
    # detect calling patterns: store_vehicle(pid, prop, iid) or store_vehicle(prop, iid)
    if isinstance(player_id, str) and not property_id and not instance_id:
        # single arg -> treat as instance_id with default prop?
        return {"status": "error", "message": "property_id and instance_id required. Example: /realestate.store_vehicle house_maple_12 ov_abc123"}
    try:
        pid = int(player_id)
        prop = str(property_id).strip()
        iid = str(instance_id or vehicle_id).strip()
        if not prop and isinstance(property_id, str) and property_id:
            prop = property_id
        if not iid and vehicle_id:
            iid = vehicle_id
    except Exception:
        # player_id was property_id string?
        pid = 1
        prop = str(player_id).strip()
        iid = str(property_id).strip() or str(instance_id).strip()
    if not prop or not iid:
        return {"status": "error", "message": "property_id and instance_id required. Example: /realestate.store_vehicle house_maple_12 ov_abc123"}
    return store_vehicle(pid, prop, iid)

@command("realestate.retrieve_vehicle", "Retrieve a vehicle from a garage (property_id optional — searches all if omitted)", category="player")
def realestate_retrieve_vehicle(player_id: int = 1, property_id: str = "", instance_id: str = "", vehicle_id: str = "") -> dict:
    # alias handling
    iid = (instance_id or vehicle_id or "").strip()
    prop = str(property_id).strip() if property_id else ""
    try:
        pid = int(player_id)
    except Exception:
        # player_id is actually property or instance
        if isinstance(player_id, str):
            # assume player_id=1 and first arg is either property or instance
            pid = 1
            if not prop and not iid:
                # player_id holds the instance or property
                # if property_id param actually holds instance?
                # Heuristic: if second param (property_id) looks like instance_id (ov_*)
                prop = str(player_id).strip()
                iid = str(property_id).strip() or iid
                if prop.startswith("ov_"):
                    iid = prop
                    prop = ""
            else:
                prop = str(player_id).strip()
        else:
            pid = 1
    if not iid:
        # try if property_id holds instance and no iid
        if prop and prop.startswith("ov_"):
            iid = prop
            prop = ""
    if not iid:
        return {"status": "error", "message": "instance_id required. Example: /realestate.retrieve_vehicle ov_abc123  or  /realestate.retrieve_vehicle house_maple_12 ov_abc123"}
    return retrieve_vehicle(pid, prop, iid)

@command("realestate.garage", "List vehicles stored at one property", category="player")
def realestate_garage(player_id: int = 1, property_id: str = "", id: str = "") -> dict:
    try:
        pid = int(player_id)
        prop = (property_id or id or "").strip()
        if not prop and isinstance(player_id, str):
            prop = str(player_id).strip()
            pid = 1
    except Exception:
        pid = 1
        prop = str(player_id).strip()
    if not prop:
        return {"status": "error", "message": "property_id required. Use realestate.owned to list properties"}
    return garage_list(pid, prop)

@command("realestate.garages", "List all garages / parking for a player", category="player")
def realestate_garages(player_id: int = 1) -> dict:
    try:
        pid = int(player_id)
    except Exception:
        if isinstance(player_id, str) and str(player_id).strip().isdigit():
            pid = int(str(player_id).strip())
        else:
            # treat as property filter? just return for player 1
            pid = 1
    _cleanup_expired_rentals()
    return garages_all(pid)

@command("realestate.get_catalog", "Get full real estate catalog (agents + properties)", category="player")
def realestate_get_catalog() -> dict:
    cat = get_catalog()
    return {"status": "success", "catalog": cat}

@command("realestate.open", "Open real estate browser (returns catalog for UI)", category="player")
def realestate_open(player_id: int = 1) -> dict:
    _ensure_loaded()
    _cleanup_expired_rentals()
    cat = get_catalog()
    # enrich properties with availability for UI
    for p in cat["properties"]:
        p["available"] = is_available(p["id"])
        try:
            parking = int(p.get("stats",{}).get("parking",0) or 0)
        except Exception:
            parking = 0
        try:
            garage = int(p.get("stats",{}).get("garage_spaces",0) or 0)
        except Exception:
            garage = 0
        p["capacity"] = parking + garage
    try:
        pid = int(player_id)
    except Exception:
        pid = 1
    try:
        from core.systems.economy.wallet import get_balance
        bal = get_balance(pid)
    except Exception:
        bal = None
    try:
        owned = get_owned_properties(pid)
    except Exception:
        owned = []
    gar = garages_all(pid)
    return {"status": "success", "catalog": cat, "balance": bal, "owned": owned, "owned_count": len(owned), "garages": gar, "message": "Real Estate opened"}

# shorter alias
@command("realestate.view", "View/ browse all properties (alias for realestate.open)", category="player")
def realestate_view(player_id: int = 1) -> dict:
    return realestate_open(player_id)

@command("realestate.reload", "Reload properties/agents XML (dev)", category="dev")
def realestate_reload() -> dict:
    res = reload_catalog()
    return {"status": "success", "message": f"Reloaded {res['properties']} properties, {res['agents']} agents", "result": res}

# Ensure catalog loads on import so dashboards can query immediately
try:
    _ensure_loaded()
except Exception:
    pass

# ---------------------------------------------------------------------------
# Save / Load
# ---------------------------------------------------------------------------

def _save_realestate():
    # also snapshot catalog ids for debug? just owned mapping
    return {
        "owned": {str(pid): [op.to_dict() for op in lst] for pid, lst in _owned.items()},
        "catalog_version": 1,
    }

def _load_realestate(state: Any):
    if not isinstance(state, dict):
        _warn(f"_load_realestate: expected dict, got {type(state).__name__}")
        return
    _owned.clear()
    owned_map = state.get("owned", {})
    # backwards compat: if state itself looks like { "1": [op_dict,...] } without wrapper
    if not owned_map and any(isinstance(v, list) for v in state.values()) and all(isinstance(k, str) and k.isdigit() for k in state.keys()):
        owned_map = state
    if isinstance(owned_map, dict):
        for k, lst in owned_map.items():
            try:
                pid = int(k)
                if not isinstance(lst, list):
                    continue
                _owned[pid] = [OwnedProperty.from_dict(d) for d in lst if isinstance(d, dict)]
            except Exception as e:
                _warn(f"_load_realestate for '{k}': {e}")
    # also handle legacy flat owned under key "properties"
    if not _owned and isinstance(state.get("properties"), dict):
        for k, lst in state.get("properties", {}).items():
            try:
                pid = int(k)
                if isinstance(lst, list):
                    _owned[pid] = [OwnedProperty.from_dict(d) for d in lst if isinstance(d, dict)]
            except Exception:
                pass

try:
    from core.systems.save.registry import register_save_provider as _reg
    _reg("realestate", _save_realestate, _load_realestate)
except Exception:
    pass

__all__ = [
    "AgentDef", "PropertyDef", "OwnedProperty",
    "get_agents", "get_agent", "get_agent_dict",
    "get_properties", "get_property", "get_property_dict", "get_catalog", "search_properties", "search_agents",
    "is_available", "is_owned_by", "get_owned_properties", "list_owned_properties", "clear_owned",
    "buy_property", "rent_property", "sell_property", "cancel_rent",
    "store_vehicle", "retrieve_vehicle", "garage_list", "garages_all",
    "reload_catalog",
]
