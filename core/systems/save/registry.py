"""
Save/Load registry for MTT.

Systems register a (save_fn, load_fn) pair under a unique key. The save
manager (manager.py) iterates this registry and never imports individual
systems directly — mirrors the @command decorator pattern used by the dev
console command registry (see docs/dashboard_plan.md). Adding save support
to a new system (bank, career, weather, ...) never requires editing the
save manager itself.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Tuple

# key -> (save_fn, load_fn)
# save_fn: () -> JSON-serializable state
# load_fn: (state) -> None, restores the system from that state
_PROVIDERS: Dict[str, Tuple[Callable[[], Any], Callable[[Any], None]]] = {}


def register_save_provider(
    key: str,
    save_fn: Callable[[], Any],
    load_fn: Callable[[Any], None],
) -> None:
    """
    Register a system's save/load functions.

    Args:
        key: Unique key this system's data is stored under in the save file.
        save_fn: Zero-arg callable returning JSON-serializable state.
        load_fn: One-arg callable that restores state from what save_fn produced.
    """
    if key in _PROVIDERS:
        try:
            from core.systems.orchestrator import warning
            warning(f"Save provider '{key}' registered twice, overwriting previous registration")
        except ImportError:
            pass
    _PROVIDERS[key] = (save_fn, load_fn)


def get_providers() -> Dict[str, Tuple[Callable[[], Any], Callable[[Any], None]]]:
    """Return a copy of the current provider registry."""
    return dict(_PROVIDERS)


def unregister_all() -> None:
    """Clear the registry. Useful for test isolation."""
    _PROVIDERS.clear()
