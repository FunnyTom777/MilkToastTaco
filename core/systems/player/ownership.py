"""
Ownership system — manages everything the player owns.

Owns vehicles (via Vehicle Shop), and generic items. Vehicles are stored
as distinct instances (each purchase creates an OwnedVehicle with its own
instance_id + license plate). Generic ownership (legacy) kept for compat.

Save provider key: "ownership"
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from core.command_registry import command

try:
    from core.systems.orchestrator import warning as _warn
except ImportError:
    def _warn(msg): print(f"WARNING: {msg}")

try:
    from core.output import print_to_user as _ptu, warning as _out_warn, success as _success
except ImportError:
    def _ptu(*a, **k): print(*a)
    def _out_warn(*a, **k): print(*a)
    def _success(*a, **k): print(*a)


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

@dataclass
class OwnedVehicle:
    """A single owned vehicle instance (FS22-style)."""
    instance_id: str           # unique per purchase, e.g. "ov_abc123"
    vehicle_id: str            # catalog id, e.g. "car_sedan_classic"
    category: str              # e.g. "cars"
    name: str                  # display name snapshot at purchase time
    price_paid: int
    acquired_at: float = field(default_factory=lambda: time.time())
    license_plate: Optional[str] = None
    # optional snapshot of stats at purchase (not mutated after)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "OwnedVehicle":
        return cls(
            instance_id=str(data.get("instance_id", "")),
            vehicle_id=str(data.get("vehicle_id", "")),
            category=str(data.get("category", "")),
            name=str(data.get("name", "")),
            price_paid=int(data.get("price_paid", 0)),
            acquired_at=float(data.get("acquired_at", time.time())),
            license_plate=data.get("license_plate"),
            stats=dict(data.get("stats", {})) if isinstance(data.get("stats"), dict) else {},
        )


# player_id -> list[OwnedVehicle]
_owned_vehicles: Dict[int, List[OwnedVehicle]] = {}

# legacy generic ownership (player_id -> list[any])
_generic_owned: Dict[int, List[Any]] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_list(player_id: int) -> List[OwnedVehicle]:
    pid = int(player_id)
    if pid not in _owned_vehicles:
        _owned_vehicles[pid] = []
    return _owned_vehicles[pid]

def _gen_instance_id() -> str:
    return "ov_" + uuid.uuid4().hex[:8]

def _gen_plate():
    try:
        from core.systems.vehicles.data.license_plates import generate_new_licenseplate, register_new_licenseplate
        plate = generate_new_licenseplate()
        try:
            register_new_licenseplate(plate)
        except Exception:
            pass
        return plate
    except Exception:
        # fallback random
        import random, string
        chars = string.ascii_uppercase + string.digits
        return ''.join(random.choice(chars) for _ in range(3)) + '-' + ''.join(random.choice(chars) for _ in range(4))


# ---------------------------------------------------------------------------
# Public API (importable by shop + game)
# ---------------------------------------------------------------------------

def add_owned_vehicle(player_id: int, vehicle_def: Any, price_paid: Optional[int] = None, stats: Optional[dict] = None) -> OwnedVehicle:
    """
    Add a vehicle to ownership. vehicle_def can be a VehicleDef dataclass or dict with id/name/category/price.
    Returns the created OwnedVehicle.
    """
    pid = int(player_id)
    # Normalize def
    if hasattr(vehicle_def, "id"):
        vid = getattr(vehicle_def, "id")
        name = getattr(vehicle_def, "name", vid)
        cat = getattr(vehicle_def, "category", "")
        price = getattr(vehicle_def, "price", 0)
        stats_src = getattr(vehicle_def, "stats", {}) or {}
    elif isinstance(vehicle_def, dict):
        vid = vehicle_def.get("id") or vehicle_def.get("vehicle_id") or ""
        name = vehicle_def.get("name", vid)
        cat = vehicle_def.get("category", "")
        price = vehicle_def.get("price", 0)
        stats_src = vehicle_def.get("stats", {}) or {}
    else:
        raise ValueError("vehicle_def must be VehicleDef or dict")

    if not vid:
        raise ValueError("vehicle_def missing id")

    final_price = int(price_paid) if price_paid is not None else int(price)
    snapshot_stats = dict(stats) if isinstance(stats, dict) else dict(stats_src) if isinstance(stats_src, dict) else {}

    ov = OwnedVehicle(
        instance_id=_gen_instance_id(),
        vehicle_id=str(vid),
        category=str(cat),
        name=str(name),
        price_paid=final_price,
        license_plate=_gen_plate(),
        stats=snapshot_stats,
    )
    _ensure_list(pid).append(ov)
    try:
        _success(f"Added owned vehicle {ov.name} ({ov.instance_id}) for player {pid}", source="ownership")
    except Exception:
        pass
    return ov

def remove_owned_vehicle(player_id: int, instance_id: str) -> bool:
    """Remove an owned vehicle by instance_id. Returns True if removed."""
    pid = int(player_id)
    lst = _owned_vehicles.get(pid, [])
    for i, ov in enumerate(lst):
        if ov.instance_id == instance_id:
            del lst[i]
            return True
    return False

def remove_owned_vehicle_by_vehicle_id(player_id: int, vehicle_id: str) -> bool:
    """Remove first owned vehicle matching catalog vehicle_id (convenience for sell)."""
    pid = int(player_id)
    lst = _owned_vehicles.get(pid, [])
    for i, ov in enumerate(lst):
        if ov.vehicle_id == vehicle_id:
            del lst[i]
            return True
    return False

def get_owned_vehicles(player_id: int) -> List[Dict[str, Any]]:
    """Return owned vehicles for player as list of dicts (JSON-safe)."""
    pid = int(player_id)
    return [ov.to_dict() for ov in _owned_vehicles.get(pid, [])]

def list_owned_vehicles(player_id: int) -> List[OwnedVehicle]:
    """Return OwnedVehicle objects."""
    pid = int(player_id)
    return list(_owned_vehicles.get(pid, []))

def clear_owned_vehicles(player_id: Optional[int] = None) -> int:
    """Clear owned vehicles for one player or all. Returns count removed."""
    if player_id is None:
        n = sum(len(v) for v in _owned_vehicles.values())
        _owned_vehicles.clear()
        return n
    pid = int(player_id)
    n = len(_owned_vehicles.get(pid, []))
    _owned_vehicles.pop(pid, None)
    return n

def owns_vehicle(player_id: int, vehicle_id: str) -> bool:
    pid = int(player_id)
    return any(ov.vehicle_id == vehicle_id for ov in _owned_vehicles.get(pid, []))

def count_owned(player_id: int) -> int:
    return len(_owned_vehicles.get(int(player_id), []))

# Legacy generic helpers (kept for existing ownership.add/remove calls)
def _add_generic(player_id: int, item: Any):
    pid = int(player_id)
    if pid not in _generic_owned:
        _generic_owned[pid] = []
    _generic_owned[pid].append(item)

def _remove_generic(player_id: int, item: Any) -> bool:
    pid = int(player_id)
    lst = _generic_owned.get(pid, [])
    if item in lst:
        lst.remove(item)
        return True
    return False

# ---------------------------------------------------------------------------
# Commands (dashboard / game accessible)
# ---------------------------------------------------------------------------

@command("ownership.add", "Adds a new item to the players ownership list", category="player")
def add_new_item(player_id: int, item: str = "", vehicle_id: str = "") -> dict:
    """Legacy generic add; also supports adding a vehicle by vehicle_id via shop catalog lookup."""
    pid = int(player_id)
    # If vehicle_id supplied, treat as vehicle purchase via ownership directly (bypasses shop economy)
    if vehicle_id:
        # try to resolve via shop catalog if available
        try:
            from core.systems.shop.vehicle_shop import get_vehicle as _get_v, _to_owned_dict
            v = _get_v(vehicle_id)
            if v is None:
                return {"status": "error", "message": f"Unknown vehicle '{vehicle_id}'"}
            ov = add_owned_vehicle(pid, v)
            return {"status": "success", "instance_id": ov.instance_id, "vehicle": ov.to_dict(), "message": f"Added {ov.name} to ownership"}
        except ImportError:
            _add_generic(pid, vehicle_id)
            return {"status": "success", "message": f"Added {vehicle_id} (generic)"}
    if item:
        _add_generic(pid, item)
        return {"status": "success", "message": f"Added '{item}' to ownership", "owned": list(_generic_owned.get(pid, []))}
    _add_generic(pid, f"item_{len(_generic_owned.get(pid, []))+1}")
    return {"status": "success", "message": "Added generic item", "owned": list(_generic_owned.get(pid, []))}

@command("ownership.remove", "Removes an item from the Players Ownership List.", category="player")
def remove_item(player_id: int, instance_id: str = "", item: str = "") -> dict:
    pid = int(player_id)
    if instance_id:
        ok = remove_owned_vehicle(pid, instance_id)
        if ok:
            return {"status": "success", "message": f"Removed {instance_id}"}
        # also try generic
        if _remove_generic(pid, instance_id):
            return {"status": "success", "message": f"Removed generic {instance_id}"}
        return {"status": "error", "message": f"Not found: {instance_id}"}
    if item:
        if remove_owned_vehicle_by_vehicle_id(pid, item):
            return {"status": "success", "message": f"Removed vehicle {item}"}
        if _remove_generic(pid, item):
            return {"status": "success", "message": f"Removed generic {item}"}
        return {"status": "error", "message": f"Not found: {item}"}
    return {"status": "error", "message": "Provide instance_id or item"}

@command("ownership.list", "List owned vehicles for a player", category="player")
def ownership_list(player_id: int) -> dict:
    pid = int(player_id)
    vehicles = get_owned_vehicles(pid)
    generic = list(_generic_owned.get(pid, []))
    return {"status": "success", "player_id": pid, "vehicles": vehicles, "generic": generic, "count": len(vehicles)}

@command("ownership.clear", "Clear owned vehicles for a player (dev)", category="dev")
def ownership_clear(player_id: int) -> dict:
    n = clear_owned_vehicles(int(player_id))
    return {"status": "success", "cleared": n}

# ---------------------------------------------------------------------------
# Save / Load
# ---------------------------------------------------------------------------

def _save_ownership():
    return {
        "vehicles": {str(pid): [ov.to_dict() for ov in lst] for pid, lst in _owned_vehicles.items()},
        "generic": {str(pid): list(items) for pid, items in _generic_owned.items()},
    }

def _load_ownership(state: Any):
    if not isinstance(state, dict):
        _warn(f"_load_ownership: expected dict, got {type(state).__name__}")
        return
    _owned_vehicles.clear()
    _generic_owned.clear()
    veh = state.get("vehicles", {})
    gen = state.get("generic", {})
    if isinstance(veh, dict):
        for k, lst in veh.items():
            try:
                pid = int(k)
                if not isinstance(lst, list):
                    continue
                _owned_vehicles[pid] = [OwnedVehicle.from_dict(d) for d in lst if isinstance(d, dict)]
            except Exception as e:
                _warn(f"_load_ownership vehicles for '{k}': {e}")
    # backwards compat: old saves stored vehicles as list under "vehicles" incorrectly?
    # if vehicles key directly was the player map (legacy), handle
    if not _owned_vehicles and isinstance(state, dict) and any(isinstance(v, list) for v in state.values()):
        # check if state itself looks like { "1": [ov_dict, ...] }
        looks_like_old = all(k.isdigit() if isinstance(k, str) else isinstance(k, int) for k in state.keys()) and all(isinstance(v, list) for v in state.values())
        if looks_like_old:
            for k, lst in state.items():
                try:
                    pid = int(k)
                    _owned_vehicles[pid] = [OwnedVehicle.from_dict(d) for d in lst if isinstance(d, dict)]
                except Exception as e:
                    _warn(f"_load_ownership legacy for '{k}': {e}")
    if isinstance(gen, dict):
        for k, lst in gen.items():
            try:
                pid = int(k)
                _generic_owned[pid] = list(lst) if isinstance(lst, list) else []
            except Exception as e:
                _warn(f"_load_ownership generic for '{k}': {e}")

try:
    from core.systems.save.registry import register_save_provider as _reg
    _reg("ownership", _save_ownership, _load_ownership)
except Exception:
    pass

__all__ = [
    "OwnedVehicle",
    "add_owned_vehicle",
    "remove_owned_vehicle",
    "remove_owned_vehicle_by_vehicle_id",
    "get_owned_vehicles",
    "list_owned_vehicles",
    "clear_owned_vehicles",
    "owns_vehicle",
    "count_owned",
]
