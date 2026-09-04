"""
MTT Command Registry — decoupled dashboard ↔ systems bridge.

Mirrors save/registry.py and xmb.py @menu_option pattern:

    from core.command_registry import command, execute, list_commands

    @command("player.move", help_text="Move player", category="player")
    def update_player_pos(player_id: int, pos: list): ...

Dashboards / game / REPL import only this module:

    from core.command_registry import execute
    execute("player.move", player_id=1, pos=[10,0,5])

Categories enable filtering (player vs dev). Dashboards can expose
one pywebview method: call_command(name, args_dict) -> execute(name, **args_dict)

Manual discovery for now: system modules import `command` and register at
import time (like save providers). Ensure systems are imported once before
list_commands/execute is used. No auto-scan yet.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

# Valid categories — keep small; dashboards filter on this.
VALID_CATEGORIES = {"player", "dev", "system", "debug"}
DEFAULT_CATEGORY = "player"


@dataclass
class CommandSpec:
    """Metadata for a registered command."""
    name: str
    fn: Callable[..., Any]
    help_text: str
    category: str
    signature: inspect.Signature = field(repr=False)
    # Derived param info for JS/UI generation
    params: List[Dict[str, Any]] = field(default_factory=list)


# name -> CommandSpec
_COMMANDS: Dict[str, CommandSpec] = {}


def _build_params(sig: inspect.Signature) -> List[Dict[str, Any]]:
    params: List[Dict[str, Any]] = []
    for p in sig.parameters.values():
        info: Dict[str, Any] = {
            "name": p.name,
            "required": p.default is inspect.Parameter.empty,
            "has_default": p.default is not inspect.Parameter.empty,
        }
        if p.default is not inspect.Parameter.empty:
            # Keep repr small; None/str/int/float/list are JSON-ish
            try:
                info["default"] = p.default
            except Exception:
                info["default"] = str(p.default)
        # annotation as string if present
        if p.annotation is not inspect.Parameter.empty:
            try:
                info["annotation"] = getattr(p.annotation, "__name__", str(p.annotation))
            except Exception:
                info["annotation"] = str(p.annotation)
        # kind (POSITIONAL_OR_KEYWORD etc.) for UI hints
        info["kind"] = str(p.kind).split(".")[-1]
        params.append(info)
    return params


def command(name: str, help_text: str = "", category: str = DEFAULT_CATEGORY):
    """
    Decorator to register a function as a dashboard-callable command.

    Args:
        name: Namespaced string like "player.move" or "inventory.add".
              Must contain at least one dot, lowercase recommended.
        help_text: Short description shown in dashboards / help.
        category: One of VALID_CATEGORIES. Used for filtering.
                  "player" = safe for player dashboards,
                  "dev"    = dev/debug only (Dashboard V2 shows),
                  "system" = internal/system use.

    Example:
        @command("player.move", "Update player position", category="player")
        def update_player_pos(player_id: int, pos): ...
    """
    # Validate early so typos are caught at import time
    if not isinstance(name, str) or not name.strip():
        raise ValueError("command name must be a non-empty string")
    name = name.strip()
    if "." not in name:
        raise ValueError(f"command name '{name}' must be namespaced like 'system.verb' (contain a dot)")
    if category not in VALID_CATEGORIES:
        raise ValueError(f"command category '{category}' must be one of {sorted(VALID_CATEGORIES)}")
    # Normalize name to lower for case-insensitive dispatch, but preserve original for display
    # We store as given but lookup is case-insensitive via lower.
    # To keep it simple and predictable, store lower and require lower usage.
    # Enforce lower to avoid JS mismatches.
    if name != name.lower():
        # warn but store lower — avoids duplicate keys like "Player.Move" vs "player.move"
        try:
            from core.systems.orchestrator import warning as _warn

            _warn(f"command '{name}' should be lowercase; normalizing to '{name.lower()}'")
        except Exception:
            pass
        name = name.lower()

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        sig = inspect.signature(fn)
        params_info = _build_params(sig)

        if name in _COMMANDS:
            try:
                from core.systems.orchestrator import warning as _warn2

                _warn2(f"Command '{name}' registered twice, overwriting previous registration")
            except Exception:
                pass

        spec = CommandSpec(
            name=name,
            fn=fn,
            help_text=help_text or (fn.__doc__.strip().split("\n")[0] if fn.__doc__ else ""),
            category=category,
            signature=sig,
            params=params_info,
        )
        _COMMANDS[name] = spec

        @wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)

        # Attach metadata to wrapper for introspection if needed
        wrapper._command_spec = spec  # type: ignore
        wrapper._command_name = name  # type: ignore
        return wrapper

    return decorator


def get_command(name: str) -> Optional[CommandSpec]:
    """Return CommandSpec for name (case-insensitive) or None."""
    if not isinstance(name, str):
        return None
    return _COMMANDS.get(name.strip().lower())


def list_commands(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Return list of registered commands as JSON-serializable dicts.

    Args:
        category: If given, only return commands matching that category.
                  Use None to return all. Case-insensitive.

    Returns:
        List of {name, help, category, params} sorted by name.
    """
    if category is not None:
        cat = category.strip().lower()
        if cat not in VALID_CATEGORIES:
            # Unknown category -> empty rather than error so dashboards don't crash
            return []
        filtered = [s for s in _COMMANDS.values() if s.category == cat]
    else:
        filtered = list(_COMMANDS.values())

    result: List[Dict[str, Any]] = []
    for spec in sorted(filtered, key=lambda s: s.name):
        result.append(
            {
                "name": spec.name,
                "help": spec.help_text,
                "category": spec.category,
                "params": spec.params,
            }
        )
    return result


def get_commands_dict(category: Optional[str] = None) -> Dict[str, CommandSpec]:
    """Return copy of internal dict, optionally filtered by category."""
    if category is None:
        return dict(_COMMANDS)
    cat = category.strip().lower()
    return {k: v for k, v in _COMMANDS.items() if v.category == cat}


def execute(name: str, *args, **kwargs) -> Dict[str, Any]:
    """
    Dispatch a registered command by name.

    Simplest for dashboards: execute("player.move", player_id=1, pos=[10,0,5])
    Also supports positional: execute("player.move", 1, [10,0,5])

    Args:
        name: Command name like "player.move" (case-insensitive).
        *args, **kwargs: Arguments forwarded to the underlying function.

    Returns:
        {"status": "success", "result": <fn return>, "command": name}
        or {"status": "error", "message": "...", "command": name}

    Never raises — all errors are returned as dicts so pywebview JS
    always gets JSON back.
    """
    if not isinstance(name, str) or not name.strip():
        return {"status": "error", "message": "command name must be a non-empty string", "command": str(name)}

    key = name.strip().lower()
    spec = _COMMANDS.get(key)
    if spec is None:
        available = sorted(_COMMANDS.keys())
        hint = f" Available: {', '.join(available[:8])}" + ("..." if len(available) > 8 else "") if available else ""
        return {"status": "error", "message": f"Unknown command '{name}'.{hint}", "command": name}

    # Validate args against signature before calling, to give nice errors
    try:
        bound = spec.signature.bind(*args, **kwargs)
        bound.apply_defaults()
    except TypeError as e:
        # e.g. missing required arg, too many args
        return {
            "status": "error",
            "message": f"Invalid arguments for '{name}': {e}",
            "command": name,
            "expected_params": spec.params,
        }

    try:
        result = spec.fn(*bound.args, **bound.kwargs)
        # Normalize None -> success with no result; if fn already returns a dict with status, pass through?
        # We wrap uniformly so dashboards can always check .status
        # If result is already a {"status": ...} dict, unwrap its payload but keep outer success
        # to avoid double-nesting. But we preserve original if it's an error dict from legacy fns.
        if isinstance(result, dict) and "status" in result:
            # Legacy functions that return status dicts: return them directly, but ensure command field
            if "command" not in result:
                result = {**result, "command": name}
            return result
        return {"status": "success", "result": result, "command": name}
    except Exception as e:
        # Log warning for server-side visibility
        try:
            from core.systems.orchestrator import warning as _warn

            _warn(f"Command '{name}' raised: {e}")
        except Exception:
            pass
        return {"status": "error", "message": f"Command '{name}' failed: {e}", "command": name}


def call_function(function_id: str, *args, **kwargs) -> Dict[str, Any]:
    """
    Alias for execute() to match the user's original naming idea.

    Args:
        function_id: Same as command name (string). Kept for backwards compat
                     with the proposed `call_function([function_id])` shape.

    Returns:
        Same as execute().
    """
    # Support old proposal's list-wrapped id: call_function([function_id])
    if isinstance(function_id, (list, tuple)) and len(function_id) == 1:
        function_id = function_id[0]
    return execute(str(function_id), *args, **kwargs)


def unregister_all() -> None:
    """Clear registry. Useful for test isolation."""
    _COMMANDS.clear()


def ensure_commands_loaded() -> None:
    """
    Ensure all known system modules have been imported so their @command
    decorators have run. Manual discovery for now.

    Call this once at startup (dashboards do it lazily before list/execute).
    """
    # Import each system that registers commands. Keep this list in sync
    # as new systems add @command decorators. Each import is best-effort
    # so a missing optional system doesn't break the registry.
    modules = [
        "core.output",
        "core.systems.player_manager",
        "core.systems.inventory.manager",
        "core.systems.economy.bank",
        "core.systems.phone.phone",
        # Add future: "core.systems.vehicles.*", "core.systems.economy.finance_purchase", etc.
    ]
    for mod in modules:
        try:
            __import__(mod)
        except Exception as e:
            try:
                from core.systems.orchestrator import warning as _warn

                _warn(f"ensure_commands_loaded: failed to import {mod}: {e}")
            except Exception:
                pass


__all__ = [
    "command",
    "execute",
    "call_function",
    "get_command",
    "list_commands",
    "get_commands_dict",
    "unregister_all",
    "ensure_commands_loaded",
    "VALID_CATEGORIES",
    "DEFAULT_CATEGORY",
    "CommandSpec",
]
