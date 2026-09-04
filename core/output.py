"""
MTT Universal Output — one import for every system to reach the player.

  from core.output import print_to_user, warning, error, success, info

Any system (player_manager, inventory, economy, phone, weather, vehicles, ...)
calls print_to_user() and the message appears wherever the player is:

  * Dashboard V2 debug console (chatHistory) — polled via get_output()
  * Dashboard V1 (same poll API)
  * Future in-game console / HUD — subscribe(callback) or poll
  * Dev console / terminal — fallback print() when no UI sink is active
  * logs/log.txt — optional file sink for warnings/errors

Design mirrors command_registry.py and save/registry.py:
  - Pure Python, no hard dependency on pywebview / dashboards
  - Systems import ONLY this module — no circular imports
  - Dashboards import ONLY this module to poll — never import systems directly
  - Thread-safe ring buffer (deque maxlen 512) so background systems can emit

Levels control styling in Dashboard V2:
  debug / info / success / warning / error / system

Channels let the future game route differently (toast vs chat vs log):
  general / toast / log / debug / system / <custom>

Auto-fallback: if no sink is registered, emit() also print()s to stdout so
headless / test runs still show output.

Example for a new system:

    from core.output import print_to_user

    def on_weather_change(old, new):
        print_to_user(f"Weather changed: {old} → {new}", level="info", channel="general")

    # warning helper also logs to file like orchestrator.warning:
    from core.output import warning
    warning("Mud depth 0.8 exceeds safe limit")
"""

from __future__ import annotations

import collections
import datetime
import threading
import time
from typing import Any, Callable, Dict, List, Optional

# ---------------------------------------------------------------------------
# Levels / channels
# ---------------------------------------------------------------------------
VALID_LEVELS = {"debug", "info", "success", "warning", "error", "system"}
DEFAULT_LEVEL = "info"
DEFAULT_CHANNEL = "general"

# ---------------------------------------------------------------------------
# Ring buffer + sinks
# ---------------------------------------------------------------------------
_MAXLEN = 512
_buffer: collections.deque = collections.deque(maxlen=_MAXLEN)
_lock = threading.Lock()
_next_id: int = 1

# Optional callbacks: sink(entry_dict) — UI can register to get push instead of poll
_sinks: List[Callable[[Dict[str, Any]], None]] = []

# Monotonic timestamp helper (iso)
def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

# ---------------------------------------------------------------------------
# Core emit
# ---------------------------------------------------------------------------

def _make_entry(
    message: str,
    level: str = DEFAULT_LEVEL,
    channel: str = DEFAULT_CHANNEL,
    source: str = "system",
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    global _next_id
    lvl = level.strip().lower() if isinstance(level, str) else DEFAULT_LEVEL
    if lvl not in VALID_LEVELS:
        lvl = DEFAULT_LEVEL
    ch = channel.strip().lower() if isinstance(channel, str) else DEFAULT_CHANNEL
    if not isinstance(source, str) or not source.strip():
        source = "system"
    with _lock:
        eid = _next_id
        _next_id += 1
    entry: Dict[str, Any] = {
        "id": eid,
        "timestamp": _now_iso(),
        "level": lvl,
        "channel": ch,
        "source": source.strip(),
        "message": str(message),
        "mono": time.monotonic(),
    }
    if meta:
        entry["meta"] = dict(meta)
    return entry


def emit(
    message: str,
    level: str = DEFAULT_LEVEL,
    channel: str = DEFAULT_CHANNEL,
    source: str = "system",
    also_print: Optional[bool] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Emit a message to the player.

    Args:
        message: Text (or markdown) to show.
        level: debug|info|success|warning|error|system — controls colour/toast.
        channel: general|toast|log|debug|... — lets game route differently.
        source: who emitted (e.g. "inventory", "weather", "bank").
        also_print: if True, also print() to stdout even when sinks exist.
                    None = auto (print only if no sinks registered).
        meta: optional extra dict (not shown, for JS/game logic).

    Returns:
        The entry dict that was buffered (id, timestamp, level, ...).
    """
    entry = _make_entry(message, level=level, channel=channel, source=source, meta=meta)

    # Buffer
    with _lock:
        _buffer.append(entry)
        sinks_snapshot = list(_sinks)

    # Push to sinks (best-effort, never crash caller)
    for cb in sinks_snapshot:
        try:
            cb(entry)
        except Exception:
            pass

    # Fallback print: always visible in headless / when no UI
    should_print = also_print if also_print is not None else (len(sinks_snapshot) == 0)
    if should_print:
        # Keep output tidy: prefix for non-info levels
        prefix = f"[{level.upper()}]" if level != "info" else ""
        try:
            print(f"{prefix} {message}" if prefix else str(message))
        except Exception:
            pass

    # Optional file logging for warning/error/system (mirrors orchestrator.warning)
    if level in {"warning", "error", "system"}:
        try:
            import os
            from pathlib import Path
            # Project root = core/output.py -> parents[1] -> MilkToastTaco/
            root = Path(__file__).resolve().parents[1]
            log_path = root / "logs" / "log.txt"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            line = f"[{entry['timestamp']}] {entry['level'].upper()} [{entry['source']}] {entry['message']}\n"
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass

    return entry


# ---------------------------------------------------------------------------
# Convenience wrappers — what systems will actually import
# ---------------------------------------------------------------------------

def print_to_user(
    text: str,
    level: str = "info",
    channel: str = DEFAULT_CHANNEL,
    source: str = "system",
    **meta: Any,
) -> Dict[str, Any]:
    """
    Primary API for every MTT system.

        from core.output import print_to_user
        print_to_user("You picked up 3x Bread", level="success")
        print_to_user("Mud is deep here!", level="warning", channel="toast", source="physics.mud")

    Wrapper around emit(); same args plus any **meta forwarded as entry['meta'].
    """
    return emit(str(text), level=level, channel=channel, source=source, meta=meta or None)


def info(text: str, channel: str = DEFAULT_CHANNEL, source: str = "system", **meta: Any) -> Dict[str, Any]:
    return emit(str(text), level="info", channel=channel, source=source, meta=meta or None)


def success(text: str, channel: str = DEFAULT_CHANNEL, source: str = "system", **meta: Any) -> Dict[str, Any]:
    return emit(str(text), level="success", channel=channel, source=source, meta=meta or None)


def warning(text: str, channel: str = DEFAULT_CHANNEL, source: str = "system", **meta: Any) -> Dict[str, Any]:
    # Mirrors orchestrator.warning but also buffered for dashboards
    return emit(str(text), level="warning", channel=channel, source=source, meta=meta or None)


def error(text: str, channel: str = DEFAULT_CHANNEL, source: str = "system", **meta: Any) -> Dict[str, Any]:
    return emit(str(text), level="error", channel=channel, source=source, meta=meta or None)


def debug(text: str, channel: str = "debug", source: str = "system", **meta: Any) -> Dict[str, Any]:
    return emit(str(text), level="debug", channel=channel, source=source, meta=meta or None)


def system(text: str, channel: str = "system", source: str = "system", **meta: Any) -> Dict[str, Any]:
    return emit(str(text), level="system", channel=channel, source=source, meta=meta or None)


# ---------------------------------------------------------------------------
# Poll / subscribe API — what dashboards & game use
# ---------------------------------------------------------------------------

def get_messages(
    since_id: int = 0,
    limit: int = 100,
    level: Optional[str] = None,
    channel: Optional[str] = None,
    source: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Poll for messages since a given id (for dashboards / game).

    Args:
        since_id: Return only entries with id > since_id (0 = from start).
        limit: Max entries (newest last). 1..500.
        level/channel/source: Optional filters (case-insensitive).

    Returns:
        List of entry dicts sorted by id ascending (oldest first).
    """
    lvl = level.strip().lower() if isinstance(level, str) and level.strip() else None
    ch = channel.strip().lower() if isinstance(channel, str) and channel.strip() else None
    src = source.strip().lower() if isinstance(source, str) and source.strip() else None
    if lvl is not None and lvl not in VALID_LEVELS:
        lvl = None
    lim = max(1, min(int(limit) if isinstance(limit, int) else 100, 500))
    try:
        sid = int(since_id)
    except Exception:
        sid = 0

    with _lock:
        buf = list(_buffer)

    out: List[Dict[str, Any]] = []
    for e in buf:
        if e["id"] <= sid:
            continue
        if lvl is not None and e.get("level") != lvl:
            continue
        if ch is not None and e.get("channel") != ch:
            continue
        if src is not None and e.get("source", "").lower() != src:
            continue
        out.append(dict(e))  # copy
        if len(out) >= lim:
            break
    return out


def get_output(
    since_id: int = 0,
    limit: int = 100,
    level: Optional[str] = None,
    channel: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Dashboard-friendly wrapper: returns {status, messages, latest_id}.
    """
    try:
        msgs = get_messages(since_id=since_id, limit=limit, level=level, channel=channel)
        latest = msgs[-1]["id"] if msgs else (since_id if isinstance(since_id, int) else 0)
        # Also report max id in buffer for polling convenience
        with _lock:
            max_id = _buffer[-1]["id"] if _buffer else 0
        return {"status": "success", "messages": msgs, "latest_id": latest, "max_id": max_id}
    except Exception as e:
        return {"status": "error", "message": str(e), "messages": []}


def poll_output(since_id: int = 0, limit: int = 100) -> Dict[str, Any]:
    """Alias for get_output — used by JS polling (same name as pywebview method)."""
    return get_output(since_id=since_id, limit=limit)


def clear() -> Dict[str, Any]:
    """Clear the ring buffer. Returns {status, cleared}."""
    with _lock:
        n = len(_buffer)
        _buffer.clear()
    return {"status": "success", "cleared": n}


def subscribe(callback: Callable[[Dict[str, Any]], None]) -> Callable[[], None]:
    """
    Register a push sink. Returns an unsubscribe callable.

        unsub = subscribe(lambda e: my_hud.show(e["message"]))
        ...
        unsub()
    """
    if not callable(callback):
        raise ValueError("subscribe callback must be callable")
    with _lock:
        if callback not in _sinks:
            _sinks.append(callback)

    def _unsub() -> None:
        try:
            with _lock:
                if callback in _sinks:
                    _sinks.remove(callback)
        except Exception:
            pass

    return _unsub


def unsubscribe(callback: Callable[[Dict[str, Any]], None]) -> bool:
    """Remove a previously registered sink. Returns True if removed."""
    with _lock:
        if callback in _sinks:
            _sinks.remove(callback)
            return True
    return False


def _reset_for_tests() -> None:
    """Clear buffer, sinks, and id counter — for test isolation."""
    global _next_id
    with _lock:
        _buffer.clear()
        _sinks.clear()
        _next_id = 1


# --- demo commands for Dashboard V2 (so /system.echo works immediately) ---
try:
    from core.command_registry import command as _cmd

    @_cmd("system.echo", "Echo a message via the universal output bus (tests Dashboard V2 output)", category="player")
    def _echo_cmd(text: str, level: str = "info", channel: str = "general"):
        """Echo text via output bus — test that print_to_user reaches Dashboard V2."""
        # Source is system.echo so dashboard shows it nicely
        return print_to_user(str(text), level=level or "info", channel=channel or "general", source="system.echo")

    @_cmd("system.warn", "Emit a warning via output bus", category="player")
    def _warn_cmd(text: str, channel: str = "general"):
        return warning(str(text), channel=channel or "general", source="system.warn")

    @_cmd("system.error_demo", "Emit an error via output bus", category="player")
    def _error_cmd(text: str, channel: str = "general"):
        return error(str(text), channel=channel or "general", source="system.error_demo")

    @_cmd("output.clear", "Clear the output buffer (dev)", category="dev")
    def _clear_cmd():
        return clear()
except Exception:
    pass


__all__ = [
    "emit",
    "print_to_user",
    "info",
    "success",
    "warning",
    "error",
    "debug",
    "system",
    "get_messages",
    "get_output",
    "poll_output",
    "clear",
    "subscribe",
    "unsubscribe",
    "VALID_LEVELS",
    "DEFAULT_LEVEL",
    "DEFAULT_CHANNEL",
]
