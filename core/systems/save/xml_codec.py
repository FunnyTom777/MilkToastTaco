"""
Generic Python <-> XML value codec for the save/load system.

Save providers hand back plain Python values (dicts, lists, strings,
numbers, bools, None) — the same shapes you'd normally give json.dumps.
This module serializes those into XML elements and back again, so save
files stay honest XML like everything else in data/, instead of JSON.

Format:

    <tag type="dict">
        <entry key="..." type="...">...</entry>
        ...
    </tag>

    <tag type="list">
        <item type="...">...</item>
        ...
    </tag>

    <tag type="int|float|str|bool|null">text</tag>

The `type` attribute is what makes this lossless and round-trippable —
plain XML has no native way to tell "35" (int) apart from "35" (string),
so we say so explicitly.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any


def value_to_element(tag: str, value: Any) -> ET.Element:
    """
    Serialize a plain Python value (dict/list/str/int/float/bool/None)
    into an XML element named `tag`.

    Raises:
        TypeError: if value is a type this codec doesn't know how to
            represent (e.g. a custom class — save providers should
            return plain data, not objects).
    """
    el = ET.Element(tag)

    if isinstance(value, bool):
        # NOTE: bool check must come before int, since bool is an int subclass
        el.set("type", "bool")
        el.text = "true" if value else "false"
    elif isinstance(value, int):
        el.set("type", "int")
        el.text = str(value)
    elif isinstance(value, float):
        el.set("type", "float")
        el.text = repr(value)  # repr() round-trips floats exactly
    elif value is None:
        el.set("type", "null")
    elif isinstance(value, str):
        el.set("type", "str")
        el.text = value
    elif isinstance(value, dict):
        el.set("type", "dict")
        for key, sub_value in value.items():
            entry = value_to_element("entry", sub_value)
            entry.set("key", str(key))
            el.append(entry)
    elif isinstance(value, (list, tuple)):
        el.set("type", "list")
        for item in value:
            el.append(value_to_element("item", item))
    else:
        raise TypeError(
            f"Cannot serialize value of type {type(value).__name__} to XML: {value!r}. "
            f"Save providers should return plain dicts/lists/str/int/float/bool/None."
        )

    return el


def element_to_value(el: ET.Element) -> Any:
    """Deserialize an XML element (produced by value_to_element) back into a plain Python value."""
    vtype = el.get("type", "str")

    if vtype == "bool":
        return (el.text or "").strip().lower() == "true"
    if vtype == "int":
        return int((el.text or "0").strip())
    if vtype == "float":
        return float((el.text or "0").strip())
    if vtype == "null":
        return None
    if vtype == "str":
        return el.text or ""
    if vtype == "dict":
        result = {}
        for entry in el.findall("entry"):
            key = entry.get("key", "")
            result[key] = element_to_value(entry)
        return result
    if vtype == "list":
        return [element_to_value(item) for item in el.findall("item")]

    raise ValueError(f"Unknown type attribute '{vtype}' on <{el.tag}> — save file may be corrupt or from a newer version")
