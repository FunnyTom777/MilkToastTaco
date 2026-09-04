"""
Save/Load system public exports.

See docs for the registry pattern: systems call register_save_provider()
once (typically at module import time) to opt in to saves. This module
never needs to change when a new system adds save support.
"""

from core.systems.save.registry import register_save_provider, get_providers, unregister_all
from core.systems.save.manager import (
    save_game,
    load_game,
    list_saves,
    delete_save,
    SAVE_VERSION,
    load_save,
    save_state,
)
from core.systems.save.xml_codec import value_to_element, element_to_value

__all__ = [
    "register_save_provider",
    "get_providers",
    "unregister_all",
    "save_game",
    "load_game",
    "list_saves",
    "delete_save",
    "SAVE_VERSION",
    "load_save",
    "save_state",
    "value_to_element",
    "element_to_value",
]
