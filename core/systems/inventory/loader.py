"""
Inventory loader — parses data/items.xml into ItemDef registry.

Uses core.xml_loader for safe parsing; logs via orchestrator.warning.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from core.xml_loader import load_xml_file, get_child_elements, get_element_text
from core.systems.orchestrator import warning


@dataclass(frozen=True)
class ItemDef:
    """Definition of a single item type from items.xml."""
    item_id: int
    name: str
    value: int
    weight: float
    category: str
    perishable: bool
    spoil_hours: Optional[int]  # None if not perishable or not specified
    description: str
    tags: List[str]


# Module-level cache: item_id -> ItemDef
_ITEM_DEFS: Dict[int, ItemDef] = {}
_LOADED_PATH: Optional[str] = None


def _parse_bool(text: str) -> bool:
    return text.strip().lower() in ("true", "1", "yes")


def _load_defs_from_root(root) -> Dict[int, ItemDef]:
    defs: Dict[int, ItemDef] = {}
    for item_el in get_child_elements(root, "item"):
        name = get_element_text(item_el, "item_name", default="").strip()
        id_text = get_element_text(item_el, "item_id", default="").strip()
        value_text = get_element_text(item_el, "value", default="0").strip()
        weight_text = get_element_text(item_el, "weight", default="0").strip()
        category = get_element_text(item_el, "category", default="misc").strip()
        perishable_text = get_element_text(item_el, "perishable", default="false").strip()
        spoil_text = get_element_text(item_el, "spoil_time_hours", default="").strip()
        description = get_element_text(item_el, "item_description", default="").strip()

        # Tags
        tags: List[str] = []
        tags_el = item_el.find("tags")
        if tags_el is not None:
            for tag_el in get_child_elements(tags_el, "tag"):
                if tag_el.text and tag_el.text.strip():
                    tags.append(tag_el.text.strip())

        # Validate required fields
        if not name or not id_text:
            warning(f"Skipping item with missing name or id: name='{name}' id='{id_text}'")
            continue

        try:
            item_id = int(id_text)
        except ValueError:
            warning(f"Skipping item '{name}': invalid item_id '{id_text}'")
            continue

        try:
            value = int(value_text) if value_text else 0
        except ValueError:
            warning(f"Item {item_id} ('{name}'): invalid value '{value_text}', defaulting to 0")
            value = 0

        try:
            weight = float(weight_text) if weight_text else 0.0
        except ValueError:
            warning(f"Item {item_id} ('{name}'): invalid weight '{weight_text}', defaulting to 0")
            weight = 0.0

        perishable = _parse_bool(perishable_text)
        spoil_hours: Optional[int] = None
        if perishable and spoil_text:
            try:
                spoil_hours = int(spoil_text)
            except ValueError:
                warning(f"Item {item_id} ('{name}'): invalid spoil_time_hours '{spoil_text}'")
                spoil_hours = None

        if item_id in defs:
            warning(f"Duplicate item_id {item_id} ('{name}'), overwriting previous entry")

        defs[item_id] = ItemDef(
            item_id=item_id,
            name=name,
            value=value,
            weight=weight,
            category=category,
            perishable=perishable,
            spoil_hours=spoil_hours,
            description=description,
            tags=tags,
        )

    return defs


def load_item_defs(path: str = "data/items.xml", strict: bool = False, use_cache: bool = True) -> Dict[int, ItemDef]:
    """
    Load item definitions from XML file.

    Args:
        path: Path to items.xml (relative to project root or absolute).
        strict: If True, raise on load failure instead of returning empty dict.
        use_cache: If True, return cached result when path matches previous load.

    Returns:
        Dict mapping item_id -> ItemDef. Empty dict on failure (unless strict).
    """
    global _ITEM_DEFS, _LOADED_PATH

    # Resolve path relative to project root (one level above core/systems/inventory)
    if not os.path.isabs(path):
        # Try relative to cwd first, then relative to project root
        candidate = Path(path)
        if not candidate.is_file():
            # Project root is 3 levels up from this file: core/systems/inventory/loader.py -> MilkToastTaco/
            project_root = Path(__file__).resolve().parents[3]
            candidate = project_root / path
            path = str(candidate)

    if use_cache and _ITEM_DEFS and _LOADED_PATH == path:
        return dict(_ITEM_DEFS)

    root = load_xml_file(path, strict=strict)

    if root is None:
        if strict:
            # load_xml_file with strict=True would have raised; this is fallback
            from core.xml_loader import XMLLoadError
            raise XMLLoadError(f"Failed to load item definitions from {path}")
        warning(f"Could not load item definitions from {path}, returning empty registry")
        return {}

    defs = _load_defs_from_root(root)

    # Only cache successful loads
    _ITEM_DEFS = defs
    _LOADED_PATH = path

    return dict(_ITEM_DEFS)


def get_item_def(item_id: int) -> Optional[ItemDef]:
    """Get a single ItemDef by id, loading defaults if cache empty."""
    if not _ITEM_DEFS:
        load_item_defs()
    return _ITEM_DEFS.get(item_id)


def get_all_item_defs() -> Dict[int, ItemDef]:
    """Get all cached ItemDefs, loading defaults if empty."""
    if not _ITEM_DEFS:
        load_item_defs()
    return dict(_ITEM_DEFS)


def clear_cache() -> None:
    """Clear the module cache (useful for tests)."""
    global _ITEM_DEFS, _LOADED_PATH
    _ITEM_DEFS = {}
    _LOADED_PATH = None
