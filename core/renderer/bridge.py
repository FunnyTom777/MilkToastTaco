"""
MTT Dashboard Command Bridge — shared mixin for ALL dashboards and future game GUI.

This is the single place that wires ``pywebview`` JS bridge methods to
``core.command_registry``. Any new dashboard (V3, in-game overlay, etc.)
or the future game itself can reuse it without copy-pasting:

    # Future dashboard example:
    from core.renderer.bridge import CommandBridgeMixin

    class MyDashboardAPI(CommandBridgeMixin):
        def get_state(self): ...  # your own

    # Standalone game / REPL:
    from core.command_registry import execute, list_commands  # auto-discovers
    execute("player.move", player_id=1, pos=[10,0,5])

All registry discovery is automatic — adding a new file
``core/systems/vehicles/car.py`` with ``@command("vehicles.spawn", ...)``
makes it appear in ``list_commands()`` and runnable via ``execute()``
on next call, with no registry list to edit.

Design: thin mixin, no hard dependency on pywebview. Each method normalises
``args`` shapes from JS (dict vs list vs single value) and delegates to
``core.command_registry``.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class CommandBridgeMixin:
    """
    Reusable pywebview API mixin: ``call_command`` / ``call_function`` /
    ``list_commands`` / ``get_commands``.

    Mix into any dashboard API class:

        class DashboardV2API(CommandBridgeMixin):
            ...

    Future dashboards get autodiscovery for free — no manual import list.
    """

    # ---- single dispatch --------------------------------------------------------

    def call_command(self, name: str, args=None) -> Dict[str, Any]:
        """
        Dispatch any registered command (string id, e.g. 'player.move').

        JS: ``pywebview.api.call_command("player.move", {player_id:1, pos:[10,0,5]})``
        Also accepts positional array: ``["player.move", [1, [10,0,5]]]``
        """
        try:
            from core.command_registry import execute

            if args is None:
                return execute(name)
            if isinstance(args, dict):
                return execute(name, **args)
            if isinstance(args, (list, tuple)):
                return execute(name, *args)
            return execute(name, args)
        except Exception as e:
            return {"status": "error", "message": str(e), "command": name}

    def call_function(self, function_id, args=None) -> Dict[str, Any]:
        """Alias for call_command — supports original ``function_id`` naming."""
        try:
            from core.command_registry import call_function as _cf

            if isinstance(function_id, (list, tuple)) and len(function_id) == 1:
                function_id = function_id[0]
            if args is None:
                return _cf(function_id)
            if isinstance(args, dict):
                return _cf(function_id, **args)
            if isinstance(args, (list, tuple)):
                return _cf(function_id, *args)
            return _cf(function_id, args)
        except Exception as e:
            return {"status": "error", "message": str(e), "command": str(function_id)}

    # ---- discovery / listing ---------------------------------------------------

    def list_commands(self, category: Optional[str] = None, refresh: bool = False) -> Dict[str, Any]:
        """
        List available commands, optionally filtered by category.

        Args:
            category: "player" | "dev" | "system" | None (all).
            refresh: If True, force a filesystem rescan so brand-new
                     ``@command`` files appear without restarting.
        """
        try:
            from core.command_registry import list_commands as _list

            cmds = _list(category, refresh=refresh)
            return {"status": "success", "commands": cmds, "category": category}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_commands(self, category: Optional[str] = None, refresh: bool = False) -> Dict[str, Any]:
        """Alias for list_commands."""
        return self.list_commands(category, refresh=refresh)

    def refresh_commands(self) -> Dict[str, Any]:
        """
        Force a rescan and return the fresh command list.
        Convenience for dashboards with a Refresh button.
        """
        return self.list_commands(refresh=True)


# -- standalone helpers for non-mixin use (game loop, REPL, etc.) --------------

def bridge_list_commands(category: Optional[str] = None, refresh: bool = False) -> Dict[str, Any]:
    """Standalone helper — no class needed."""
    try:
        from core.command_registry import list_commands as _list

        cmds = _list(category, refresh=refresh)
        return {"status": "success", "commands": cmds, "category": category}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def bridge_call_command(name: str, args=None) -> Dict[str, Any]:
    """Standalone helper — dispatch a command dict/list."""
    try:
        from core.command_registry import execute

        if args is None:
            return execute(name)
        if isinstance(args, dict):
            return execute(name, **args)
        if isinstance(args, (list, tuple)):
            return execute(name, *args)
        return execute(name, args)
    except Exception as e:
        return {"status": "error", "message": str(e), "command": name}


__all__ = [
    "CommandBridgeMixin",
    "bridge_list_commands",
    "bridge_call_command",
]
