"""
Inventory manager — weight-based carry system.

No stack limit; capacity is enforced by total weight (KG).
Per-player inventories stored in module-level registry, mirroring player_manager pattern.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from core.systems.orchestrator import warning

DEFAULT_MAX_WEIGHT = 35.0  # KG — e.g. ~70 bread loaves (0.5kg) or 2 jerry cans (15kg)

# Lazy import to avoid circular deps — loader is imported inside functions where needed


@dataclass
class InventoryStack:
    """A stack of identical items in an inventory.

    Quantity tracks how many of the same item_id. acquired_at is the timestamp
    of the earliest item in the stack (used for spoilage). When adding more
    of the same item, we keep the earliest timestamp for simplicity.
    """
    item_id: int
    quantity: int
    acquired_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))

    def is_spoiled(self, now: Optional[datetime.datetime] = None) -> bool:
        """Check if this stack is spoiled based on ItemDef perishable + spoil_hours."""
        from core.systems.inventory.loader import get_item_def
        defn = get_item_def(self.item_id)
        if defn is None or not defn.perishable or defn.spoil_hours is None:
            return False
        if now is None:
            now = datetime.datetime.now(datetime.timezone.utc)
        # Ensure both datetimes are timezone-aware for comparison
        acquired = self.acquired_at
        if acquired.tzinfo is None:
            acquired = acquired.replace(tzinfo=datetime.timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=datetime.timezone.utc)
        elapsed_hours = (now - acquired).total_seconds() / 3600.0
        return elapsed_hours >= defn.spoil_hours


class Inventory:
    """Per-player weight-based inventory."""

    def __init__(self, max_weight: float = DEFAULT_MAX_WEIGHT):
        if max_weight <= 0:
            raise ValueError("max_weight must be > 0")
        self.max_weight: float = float(max_weight)
        # item_id -> InventoryStack
        self._stacks: Dict[int, InventoryStack] = {}

    # ---- weight helpers ----

    def total_weight(self) -> float:
        """Calculate total weight of all items (KG)."""
        from core.systems.inventory.loader import get_item_def
        total = 0.0
        for stack in self._stacks.values():
            defn = get_item_def(stack.item_id)
            if defn is None:
                warning(f"Inventory contains unknown item_id {stack.item_id}, counting as 0 weight")
                continue
            total += defn.weight * stack.quantity
        return total

    def remaining_capacity(self) -> float:
        return self.max_weight - self.total_weight()

    def is_overweight(self) -> bool:
        return self.total_weight() > self.max_weight + 1e-9

    # ---- queries ----

    def has(self, item_id: int, quantity: int = 1) -> bool:
        if quantity <= 0:
            raise ValueError("quantity must be > 0")
        stack = self._stacks.get(item_id)
        return stack is not None and stack.quantity >= quantity

    def count(self, item_id: int) -> int:
        stack = self._stacks.get(item_id)
        return stack.quantity if stack else 0

    def can_add(self, item_id: int, quantity: int = 1) -> bool:
        """Check if adding quantity of item_id would stay within weight limit."""
        if quantity <= 0:
            raise ValueError("quantity must be > 0")
        from core.systems.inventory.loader import get_item_def
        defn = get_item_def(item_id)
        if defn is None:
            warning(f"can_add: unknown item_id {item_id}")
            return False
        added_weight = defn.weight * quantity
        return (self.total_weight() + added_weight) <= self.max_weight + 1e-9

    def list_items(self) -> List[InventoryStack]:
        return list(self._stacks.values())

    def is_empty(self) -> bool:
        return len(self._stacks) == 0

    # ---- mutations ----

    def add(self, item_id: int, quantity: int = 1, acquired_at: Optional[datetime.datetime] = None) -> bool:
        """
        Add items. Returns True on success, False if would exceed weight limit.
        Raises ValueError for invalid quantity or unknown item_id silently handled as False + warning.
        """
        if quantity <= 0:
            raise ValueError("quantity must be > 0")
        from core.systems.inventory.loader import get_item_def
        defn = get_item_def(item_id)
        if defn is None:
            warning(f"add: unknown item_id {item_id}, refusing")
            return False
        if not self.can_add(item_id, quantity):
            warning(f"Cannot add {quantity}x '{defn.name}' ({defn.weight * quantity:.2f}kg) — would exceed {self.max_weight:.1f}kg limit (current {self.total_weight():.2f}kg)")
            return False

        now = acquired_at or datetime.datetime.now(datetime.timezone.utc)
        if item_id in self._stacks:
            existing = self._stacks[item_id]
            # Keep earliest timestamp
            earliest = min(existing.acquired_at, now) if existing.acquired_at.tzinfo else now
            # If existing is naive, treat as utc
            if existing.acquired_at.tzinfo is None:
                ea = existing.acquired_at.replace(tzinfo=datetime.timezone.utc)
                n = now if now.tzinfo else now.replace(tzinfo=datetime.timezone.utc)
                earliest = ea if ea < n else n
            existing.quantity += quantity
            # Keep earliest
            if earliest != existing.acquired_at:
                existing.acquired_at = earliest
        else:
            self._stacks[item_id] = InventoryStack(item_id=item_id, quantity=quantity, acquired_at=now)
        return True

    def remove(self, item_id: int, quantity: int = 1) -> bool:
        """Remove items. Returns True on success, False if not enough items."""
        if quantity <= 0:
            raise ValueError("quantity must be > 0")
        stack = self._stacks.get(item_id)
        if stack is None or stack.quantity < quantity:
            return False
        stack.quantity -= quantity
        if stack.quantity == 0:
            del self._stacks[item_id]
        return True

    def clear(self) -> None:
        self._stacks.clear()

    # ---- spoilage ----

    def spoiled_stacks(self, now: Optional[datetime.datetime] = None) -> List[InventoryStack]:
        return [s for s in self._stacks.values() if s.is_spoiled(now)]

    def remove_spoiled(self, now: Optional[datetime.datetime] = None) -> int:
        """Remove all spoiled stacks and return count of item types removed."""
        spoiled = self.spoiled_stacks(now)
        for s in spoiled:
            del self._stacks[s.item_id]
        return len(spoiled)

    # ---- (de)serialization helpers for future save system ----

    def to_dict(self) -> dict:
        return {
            "max_weight": self.max_weight,
            "stacks": [
                {"item_id": s.item_id, "quantity": s.quantity, "acquired_at": s.acquired_at.isoformat()}
                for s in self._stacks.values()
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Inventory":
        inv = cls(max_weight=data.get("max_weight", DEFAULT_MAX_WEIGHT))
        for entry in data.get("stacks", []):
            try:
                dt = datetime.datetime.fromisoformat(entry["acquired_at"])
            except Exception:
                dt = datetime.datetime.now(datetime.timezone.utc)
            inv._stacks[entry["item_id"]] = InventoryStack(
                item_id=entry["item_id"], quantity=entry["quantity"], acquired_at=dt
            )
        return inv


# ---- per-player registry (mirrors player_manager._players) ----

_inventories: Dict[int, Inventory] = {}


def ensure_inventory(player_id: int, max_weight: float = DEFAULT_MAX_WEIGHT) -> Inventory:
    """Get or create inventory for player_id."""
    if not isinstance(player_id, int):
        raise ValueError("player_id must be an int")
    if player_id not in _inventories:
        _inventories[player_id] = Inventory(max_weight=max_weight)
    return _inventories[player_id]


def get_inventory(player_id: int) -> Optional[Inventory]:
    """Return Inventory or None if player has no inventory (and warn)."""
    inv = _inventories.get(player_id)
    if inv is None:
        warning(f"get_inventory: no inventory for player {player_id}")
    return inv


def remove_inventory(player_id: int) -> bool:
    """Remove a player's inventory. Returns True if existed."""
    if player_id in _inventories:
        del _inventories[player_id]
        return True
    return False


def clear_all_inventories() -> None:
    _inventories.clear()


def set_max_weight(player_id: int, new_max: float) -> None:
    inv = ensure_inventory(player_id)
    if new_max <= 0:
        raise ValueError("new_max must be > 0")
    inv.max_weight = float(new_max)
