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

Auto-discovery: any new file under ``core/`` or ``engine/`` that uses
``@command(...)`` is automatically imported on first use. No manual list
to keep in sync. All dashboards (V1, V2, future game/GUI) share the same
registry via ``autodiscover()`` / lazy ``_ensure_autodiscovered()``.
"""

from __future__ import annotations

import importlib
import inspect
import sys
import threading
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
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

# -- autodiscovery state -------------------------------------------------
# Project root = core/command_registry.py -> parents[1] -> MilkToastTaco/
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Packages / roots scanned on autodiscover. Add new top-level packages here
# if the game grows beyond core/ + engine/.
_DEFAULT_SCAN_PACKAGES: List[str] = ["core", "engine"]

_AUTO_DISCOVERED: bool = False
_SEEN_MODULES: set[str] = set()
_FAILED_MODULES: set[str] = set()
_DISCOVERY_LOCK = threading.Lock()


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
    _ensure_autodiscovered()
    return _COMMANDS.get(name.strip().lower())


def list_commands(category: Optional[str] = None, refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Return list of registered commands as JSON-serializable dicts.

    Args:
        category: If given, only return commands matching that category.
                  Use None to return all. Case-insensitive.
        refresh: If True, force a filesystem rescan before listing so
                 newly-created ``@command`` files appear without restart.

    Returns:
        List of {name, help, category, params} sorted by name.
    """
    if refresh:
        autodiscover(force=True)
    else:
        _ensure_autodiscovered()

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


def get_commands_dict(category: Optional[str] = None, refresh: bool = False) -> Dict[str, CommandSpec]:
    """Return copy of internal dict, optionally filtered by category."""
    if refresh:
        autodiscover(force=True)
    else:
        _ensure_autodiscovered()
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

    _ensure_autodiscovered()

    key = name.strip().lower()
    spec = _COMMANDS.get(key)
    if spec is None:
        # Retry once after a forced rescan — picks up brand-new files
        # created after the first autodiscover without requiring a restart.
        autodiscover(force=False)
        spec = _COMMANDS.get(key)
        if spec is None:
            # One more try with force (re-import failed modules)
            # only if we haven't yet discovered everything.
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
    # Keep discovery flags so tests can re-discover if needed
    # (callers may also call _reset_discovery_for_tests)


def _reset_discovery_for_tests() -> None:
    """Reset autodiscovery state — for test isolation only."""
    global _AUTO_DISCOVERED
    with _DISCOVERY_LOCK:
        _AUTO_DISCOVERED = False
        _SEEN_MODULES.clear()
        _FAILED_MODULES.clear()


def _iter_candidate_modules(
    packages: Optional[List[str]] = None,
) -> List[str]:
    """
    Walk the filesystem under each package root and return dotted module names.
    Skips tests, __pycache__, and non-python files.
    """
    if packages is None:
        packages = _DEFAULT_SCAN_PACKAGES
    candidates: List[str] = []
    for pkg in packages:
        pkg_path = _PROJECT_ROOT / pkg
        if not pkg_path.is_dir():
            continue
        for py in pkg_path.rglob("*.py"):
            # Skip caches / tests / hidden
            if "__pycache__" in py.parts:
                continue
            if "tests" in py.parts:
                continue
            if py.name.startswith("test_"):
                continue
            # Skip .pyc etc (rglob already filters)
            rel = py.relative_to(_PROJECT_ROOT).with_suffix("")
            parts = list(rel.parts)
            # __init__.py -> package name
            if py.name == "__init__.py":
                parts = parts[:-1]
                if not parts:
                    continue
            mod = ".".join(parts)
            # Skip empty or obviously non-importable
            if not mod or mod.endswith(".__init__"):
                continue
            candidates.append(mod)
    # De-dupe and sort for deterministic import order (parents first)
    return sorted(set(candidates))


def autodiscover(
    packages: Optional[List[str]] = None,
    force: bool = False,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Auto-import every Python module under ``packages`` so ``@command``
    decorators run and populate the registry.

    This is the single discovery entry-point for *all* dashboards and the
    future game GUI. Adding a new file like
    ``core/systems/vehicles/car.py`` with ``@command("vehicles.spawn", ...)``
    is enough — the next ``list_commands()`` or ``execute()`` will see it
    without editing any registry list.

    Args:
        packages: Top-level package names to scan (default: ["core", "engine"]).
                  List is filesystem-relative to the project root.
        force: If False, modules already attempted once are skipped.
               If True, re-attempts even previously-failed modules (useful
               after fixing an import error or when forcing a refresh).
        verbose: If True, emit warnings for failed imports.

    Returns:
        {"imported": int, "failed": int, "skipped": int, "commands": int,
         "modules": [imported module names]}
    """
    global _AUTO_DISCOVERED
    with _DISCOVERY_LOCK:
        candidates = _iter_candidate_modules(packages)
        imported: List[str] = []
        failed: List[str] = []
        skipped = 0

        for mod in candidates:
            # Skip only successfully-seen modules when not forcing.
            # Failed modules are retried automatically so a fix (like
            # fixing Ownership.py's `from orchestrator import ...`) shows
            # up without requiring `refresh=True` / `force=True`.
            if not force and mod in _SEEN_MODULES and mod not in _FAILED_MODULES:
                skipped += 1
                continue
            _SEEN_MODULES.add(mod)
            # If this module previously failed, drop its cached (partial)
            # entry so `import_module` re-executes the file.
            if mod in _FAILED_MODULES and mod in sys.modules:
                try:
                    del sys.modules[mod]
                except Exception:
                    pass
            try:
                # Re-import or reload: use import_module for fresh modules,
                # reload if already loaded and previously succeeded but
                # force requested (handled via cache invalidation).
                if mod in sys.modules and force:
                    try:
                        importlib.invalidate_caches()
                    except Exception:
                        pass
                    importlib.reload(sys.modules[mod])
                else:
                    importlib.import_module(mod)
                imported.append(mod)
                _FAILED_MODULES.discard(mod)
            except Exception as e:
                failed.append(mod)
                _FAILED_MODULES.add(mod)
                if verbose:
                    try:
                        from core.systems.orchestrator import warning as _warn

                        _warn(f"autodiscover: failed to import {mod}: {e}")
                    except Exception:
                        pass
                # best-effort — do not crash registry on one bad module

        _AUTO_DISCOVERED = True
        return {
            "imported": len(imported),
            "failed": len(failed),
            "skipped": skipped,
            "commands": len(_COMMANDS),
            "modules": imported,
            "failed_modules": failed,
        }


def _ensure_autodiscovered() -> None:
    """
    Lazy hook: ensure registry is populated and pick up any new files.

    First call does a full scan; subsequent calls do an incremental
    scan (only unseen modules) so a newly-added ``@command`` file shows
    up automatically without a restart or manual ``refresh=True``.
    Cheap because ``autodiscover(force=False)`` skips already-seen modules.
    """
    try:
        autodiscover(force=False)
    except Exception:
        pass


def ensure_commands_loaded(
    packages: Optional[List[str]] = None,
    force: bool = False,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Ensure all known system modules have been imported so their @command
    decorators have run.

    Now delegates to :func:`autodiscover` — kept for backwards compat.
    Dashboards historically called this lazily before list/execute; future
    code can call ``autodiscover()`` directly or rely on the lazy hook in
    ``list_commands`` / ``execute``.

    Args:
        packages: Optional package list to scan (default: ["core","engine"]).
        force: Re-import even previously attempted modules.
        verbose: Emit warnings for failed imports.

    Returns:
        Same dict as :func:`autodiscover`.
    """
    return autodiscover(packages=packages, force=force, verbose=verbose)


__all__ = [
    "command",
    "execute",
    "call_function",
    "get_command",
    "list_commands",
    "get_commands_dict",
    "unregister_all",
    "ensure_commands_loaded",
    "autodiscover",
    "_ensure_autodiscovered",
    "_reset_discovery_for_tests",
    "VALID_CATEGORIES",
    "DEFAULT_CATEGORY",
    "CommandSpec",
]
