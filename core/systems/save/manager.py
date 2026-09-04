"""
Save/Load manager for MTT.

Central orchestration for writing and reading save files. Doesn't know
about individual systems — it just calls whatever's registered in
core.systems.save.registry, so wiring a new system up for saves is a
one-line register_save_provider() call in that system's own module.

Save files are XML — consistent with the rest of MTT's data files (see
core/xml_loader.py and data/items.xml) — stored under saves/ at the
project root (gitignored — saves are local player state, not source).

Reading reuses core.xml_loader.load_xml_file() directly, so save files
get the same graceful-fallback / strict-mode / XMLLoadError behavior as
every other XML file in the project. Writing/serialization of the actual
system state uses xml_codec.py.
"""

from __future__ import annotations

import datetime
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional

from core.systems.save.registry import get_providers
from core.systems.save.xml_codec import value_to_element, element_to_value
from core.xml_loader import load_xml_file
from core.systems.orchestrator import warning

SAVE_VERSION = 1

# Project root: core/systems/save/manager.py -> parents[3] -> MilkToastTaco/
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SAVE_DIR = _PROJECT_ROOT / "saves"


def _resolve_save_dir(directory: Optional[str] = None) -> Path:
    save_dir = Path(directory) if directory else DEFAULT_SAVE_DIR
    save_dir.mkdir(parents=True, exist_ok=True)
    return save_dir


def _sanitize_filename(name: str) -> str:
    """Keep save filenames boring and filesystem-safe (alnum, dash, underscore)."""
    cleaned = "".join(c for c in name if c.isalnum() or c in ("-", "_"))
    return cleaned or "save"


def save_game(save_name: str, directory: Optional[str] = None) -> str:
    """
    Save current game state to an XML file.

    Iterates every registered save provider, collects its state, and writes
    one save file containing all of it.

    Args:
        save_name: Name for this save (used as filename, sanitized).
        directory: Optional override for the save directory (mainly for tests).

    Returns:
        The path to the written save file.
    """
    save_dir = _resolve_save_dir(directory)
    file_path = save_dir / f"{_sanitize_filename(save_name)}.xml"

    root = ET.Element("save", {
        "version": str(SAVE_VERSION),
        "name": save_name,
        "saved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })
    systems_el = ET.SubElement(root, "systems")

    for key, (save_fn, _load_fn) in get_providers().items():
        try:
            state = save_fn()
        except Exception as e:
            warning(f"Failed to save system '{key}': {e}")
            continue

        system_el = value_to_element("system", state)
        system_el.set("key", key)
        systems_el.append(system_el)

    ET.indent(root, space="  ")  # pretty-print (Python 3.9+; project requires 3.11+)
    tree = ET.ElementTree(root)

    # Write to a temp file first and replace, so a crash mid-write can't
    # corrupt an existing save.
    tmp_path = file_path.with_suffix(".xml.tmp")
    tree.write(tmp_path, encoding="utf-8", xml_declaration=True)
    os.replace(tmp_path, file_path)

    return str(file_path)


def load_game(save_name: str, directory: Optional[str] = None, strict: bool = False) -> bool:
    """
    Load game state from a save file, restoring every registered system.

    Args:
        save_name: Name of the save to load (without .xml extension).
        directory: Optional override for the save directory.
        strict: If True, raise (via load_xml_file's XMLLoadError) on a
            missing file or malformed XML instead of returning False.

    Returns:
        True if the save file was read (individual system restore failures
        are logged as warnings but don't fail the whole load). False if the
        file itself couldn't be found or parsed.
    """
    save_dir = _resolve_save_dir(directory)
    file_path = save_dir / f"{_sanitize_filename(save_name)}.xml"

    root = load_xml_file(str(file_path), strict=strict)
    if root is None:
        # load_xml_file already logged a warning; strict=True would have
        # raised XMLLoadError instead of returning None.
        return False

    save_version = root.get("version")
    if save_version != str(SAVE_VERSION):
        warning(
            f"Save '{save_name}' was written with version {save_version}, "
            f"current version is {SAVE_VERSION}. Attempting load anyway "
            f"(no migrations defined yet)."
        )

    systems_el = root.find("systems")
    if systems_el is None:
        warning(f"Save '{save_name}' has no <systems> element, nothing to restore")
        return True

    providers = get_providers()
    for system_el in systems_el.findall("system"):
        key = system_el.get("key", "")
        provider = providers.get(key)
        if provider is None:
            warning(f"Save contains data for unknown system '{key}', skipping")
            continue

        _save_fn, load_fn = provider
        try:
            state = element_to_value(system_el)
            load_fn(state)
        except Exception as e:
            warning(f"Failed to restore system '{key}': {e}")

    return True


def list_saves(directory: Optional[str] = None) -> List[str]:
    """Return save names (without .xml) available in the save directory, sorted."""
    save_dir = _resolve_save_dir(directory)
    return sorted(p.stem for p in save_dir.glob("*.xml"))


def delete_save(save_name: str, directory: Optional[str] = None) -> bool:
    """Delete a save file. Returns True if it existed and was removed."""
    save_dir = _resolve_save_dir(directory)
    file_path = save_dir / f"{_sanitize_filename(save_name)}.xml"
    if file_path.is_file():
        file_path.unlink()
        return True
    return False
