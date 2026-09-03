"""
Inventory system public exports.

Weight-based carry system: no stack limit, capacity enforced by total KG.
See data/items.xml for item definitions.
"""

from core.systems.inventory.loader import ItemDef, load_item_defs, get_item_def, get_all_item_defs, clear_cache
from core.systems.inventory.manager import Inventory, InventoryStack, get_inventory, ensure_inventory, remove_inventory, clear_all_inventories, set_max_weight

__all__ = [
    "ItemDef",
    "load_item_defs",
    "get_item_def",
    "get_all_item_defs",
    "clear_cache",
    "Inventory",
    "InventoryStack",
    "get_inventory",
    "ensure_inventory",
    "remove_inventory",
    "clear_all_inventories",
    "set_max_weight",
]
