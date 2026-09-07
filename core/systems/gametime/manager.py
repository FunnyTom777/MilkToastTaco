"""
Gametime — central Time/Date system for MTT.

Manages the current in-game clock (date + time of day) and exposes a
simple API for any future system that needs time to pass:

    from core.systems.gametime.manager import (
        get_datetime, get_date, get_time,
        advance_minutes, advance_hours, advance_days,
        set_datetime, set_date, set_time,
        get_formatted, subscribe, get_weekday_name,
    )

    # advance 3 hours (e.g. after sleeping, working, travelling)
    advance_hours(3)

    # react to time passing (weather, spoilage, interest, ...)
    def on_time_change(event):
        print(f"Time moved {event['old']} -> {event['new']}")

    unsub = subscribe(on_time_change)

Save/load is automatic via ``register_save_provider("gametime", ...)``.
Commands are auto-discovered via ``core.command_registry`` so dashboards
and other systems can drive time without importing this module:

    from core.command_registry import execute
    execute("time.get")
    execute("time.advance", minutes=60, hours=2)
    execute("time.set", year=2015, month=6, day=14, hour=9, minute=30)
"""

from __future__ import annotations

import datetime
import threading
from typing import Any, Callable, Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants / defaults
# ---------------------------------------------------------------------------
# Game is set primarily around 2015 (see README). Start at a friendly
# Monday morning — 2015-01-01 was a Thursday, but we start Monday for gameplay.
START_YEAR = 2015
START_MONTH = 1
START_DAY = 1
START_HOUR = 6
START_MINUTE = 0
START_SECOND = 0

START_DATETIME = datetime.datetime(
    START_YEAR, START_MONTH, START_DAY, START_HOUR, START_MINUTE, START_SECOND
)

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

# How many game minutes pass per real-world minute when the simulation
# is running (informational — not auto-ticking yet). Systems can read/
# write this to control pacing.
DEFAULT_TIME_SCALE = 60.0  # 60 game minutes per real minute = 1 game hour per real minute

# ---------------------------------------------------------------------------
# Module-level state (singleton)
# ---------------------------------------------------------------------------
_lock = threading.Lock()
_current: datetime.datetime = START_DATETIME
_time_scale: float = DEFAULT_TIME_SCALE
_paused: bool = False

# Callbacks: fn(event_dict)
_subscribers: List[Callable[[Dict[str, Any]], None]] = []

# Monotonic tick counter (how many advance calls have happened)
_tick_count: int = 0

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _coerce_int(value: Any, name: str) -> int:
    try:
        return int(value)
    except Exception:
        raise ValueError(f"{name} must be an int, got {value!r}")


def _validate_datetime(dt: datetime.datetime) -> None:
    if not isinstance(dt, datetime.datetime):
        raise ValueError(f"Expected datetime, got {type(dt).__name__}")


def _notify(old: datetime.datetime, new: datetime.datetime, delta_minutes: float) -> None:
    """Call all subscribers with a time-change event (best-effort)."""
    # Compute helper fields
    days_advanced = (new.date() - old.date()).days
    crossed_midnight = old.date() != new.date()
    event: Dict[str, Any] = {
        "old": old.isoformat(sep=" "),
        "new": new.isoformat(sep=" "),
        "old_dt": old,
        "new_dt": new,
        "delta_minutes": float(delta_minutes),
        "delta_hours": float(delta_minutes) / 60.0,
        "delta_days": float(delta_minutes) / 1440.0,
        "crossed_midnight": crossed_midnight,
        "days_advanced": days_advanced,
        "tick": _tick_count,
    }
    # Snapshot to avoid holding lock while calling arbitrary code
    with _lock:
        subs = list(_subscribers)
    for cb in subs:
        try:
            cb(event)
        except Exception:
            # Don't let a bad subscriber break time for everyone
            try:
                from core.systems.orchestrator import warning as _warn
                _warn(f"gametime subscriber {cb!r} raised")
            except Exception:
                pass

    # Also emit to the universal output bus so dashboards see it
    try:
        from core.output import info as _info
        # Only spam output when something time-notable happens
        # (advance >= 60 min or date changed). Small ticks stay quiet.
        if abs(delta_minutes) >= 60 or crossed_midnight:
            _info(
                f"Time advanced {delta_minutes:+.0f} min -> {new.strftime('%Y-%m-%d %H:%M')}",
                source="gametime",
                channel="general",
            )
    except Exception:
        pass


def _set_current(new_dt: datetime.datetime, delta_minutes: float = 0) -> datetime.datetime:
    """Internal: set _current under lock, notify, return new_dt."""
    global _current, _tick_count
    _validate_datetime(new_dt)
    with _lock:
        old = _current
        _current = new_dt
        _tick_count += 1
    _notify(old, new_dt, delta_minutes)
    return new_dt

# ---------------------------------------------------------------------------
# Public API — getters
# ---------------------------------------------------------------------------

def get_datetime() -> datetime.datetime:
    """Return current game datetime (copy)."""
    with _lock:
        return _current

def get_date() -> datetime.date:
    """Return current game date."""
    with _lock:
        return _current.date()

def get_time() -> datetime.time:
    """Return current game time of day."""
    with _lock:
        return _current.time()

def get_iso() -> str:
    """ISO-8601 string of current game datetime (e.g. 2015-01-01T06:00:00)."""
    with _lock:
        return _current.isoformat()

def get_formatted(fmt: Optional[str] = None, include_weekday: bool = True) -> str:
    """
    Human-readable string.

    Default: "Thursday, 2015-01-01 06:00" (weekday derived from date).
    Pass a strftime fmt to customise, e.g. "%Y-%m-%d %H:%M".
    """
    with _lock:
        dt = _current
    if fmt:
        return dt.strftime(fmt)
    weekday = WEEKDAY_NAMES[dt.weekday()]
    base = dt.strftime("%Y-%m-%d %H:%M")
    return f"{weekday}, {base}" if include_weekday else base

def get_weekday() -> int:
    """Monday is 0, Sunday is 6 (datetime.weekday)."""
    with _lock:
        return _current.weekday()

def get_weekday_name() -> str:
    with _lock:
        return WEEKDAY_NAMES[_current.weekday()]

def get_month_name() -> str:
    with _lock:
        return MONTH_NAMES[_current.month]

def get_day_of_year() -> int:
    with _lock:
        return _current.timetuple().tm_yday

def is_weekend() -> bool:
    """True if Saturday or Sunday."""
    with _lock:
        return _current.weekday() >= 5

def get_year() -> int:
    with _lock:
        return _current.year

def get_month() -> int:
    with _lock:
        return _current.month

def get_day() -> int:
    with _lock:
        return _current.day

def get_hour() -> int:
    with _lock:
        return _current.hour

def get_minute() -> int:
    with _lock:
        return _current.minute

def get_second() -> int:
    with _lock:
        return _current.second

def days_elapsed(since: Optional[datetime.datetime] = None) -> int:
    """
    Days since game start (or since given datetime).

    Returns integer number of days.
    """
    with _lock:
        cur = _current
    base = since if since is not None else START_DATETIME
    if isinstance(base, datetime.datetime):
        return (cur.date() - base.date()).days
    if isinstance(base, datetime.date):
        return (cur.date() - base).days
    raise ValueError("since must be datetime or date or None")

def get_time_scale() -> float:
    with _lock:
        return _time_scale

def is_paused() -> bool:
    with _lock:
        return _paused

def get_state() -> Dict[str, Any]:
    """Full serializable snapshot (useful for HUD/dashboards)."""
    with _lock:
        dt = _current
        scale = _time_scale
        paused = _paused
        tick = _tick_count
    return {
        "iso": dt.isoformat(),
        "formatted": get_formatted(),
        "year": dt.year,
        "month": dt.month,
        "day": dt.day,
        "hour": dt.hour,
        "minute": dt.minute,
        "second": dt.second,
        "weekday": dt.weekday(),
        "weekday_name": WEEKDAY_NAMES[dt.weekday()],
        "month_name": MONTH_NAMES[dt.month],
        "day_of_year": dt.timetuple().tm_yday,
        "is_weekend": dt.weekday() >= 5,
        "date_str": dt.strftime("%Y-%m-%d"),
        "time_str": dt.strftime("%H:%M"),
        "time_str_seconds": dt.strftime("%H:%M:%S"),
        "days_elapsed": (dt.date() - START_DATETIME.date()).days,
        "time_scale": scale,
        "paused": paused,
        "tick": tick,
    }

# ---------------------------------------------------------------------------
# Mutations — set / advance
# ---------------------------------------------------------------------------

def set_datetime(
    year: Optional[int] = None,
    month: Optional[int] = None,
    day: Optional[int] = None,
    hour: Optional[int] = None,
    minute: Optional[int] = None,
    second: Optional[int] = None,
    iso: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Set game datetime.

    Provide either ``iso`` (e.g. "2015-06-14T09:30:00" or "2015-06-14 09:30")
    or individual components. Omitted components keep their current value.

    Returns the new state dict.
    """
    with _lock:
        cur = _current
    if iso is not None:
        try:
            # Accept both "T" and " " separators
            cleaned = str(iso).strip().replace(" ", "T", 1) if " " in str(iso) and "T" not in str(iso) else str(iso).strip()
            # Try fromisoformat first, fallback to strptime
            try:
                new_dt = datetime.datetime.fromisoformat(cleaned)
            except ValueError:
                # Try common formats
                for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                    try:
                        new_dt = datetime.datetime.strptime(str(iso).strip(), fmt)
                        break
                    except ValueError:
                        continue
                else:
                    raise
        except Exception as e:
            raise ValueError(f"Invalid iso datetime {iso!r}: {e}")
        # If date-only, keep current time
        if new_dt.hour == 0 and new_dt.minute == 0 and new_dt.second == 0 and "T" not in cleaned and ":" not in str(iso):
            new_dt = new_dt.replace(hour=cur.hour, minute=cur.minute, second=cur.second)
        delta = (new_dt - cur).total_seconds() / 60.0
        _set_current(new_dt, delta_minutes=delta)
        return get_state()

    # Component-wise update
    y = _coerce_int(year, "year") if year is not None else cur.year
    mo = _coerce_int(month, "month") if month is not None else cur.month
    d = _coerce_int(day, "day") if day is not None else cur.day
    h = _coerce_int(hour, "hour") if hour is not None else cur.hour
    mi = _coerce_int(minute, "minute") if minute is not None else cur.minute
    s = _coerce_int(second, "second") if second is not None else cur.second

    try:
        new_dt = datetime.datetime(y, mo, d, h, mi, s)
    except ValueError as e:
        raise ValueError(f"Invalid datetime components: {e}")

    delta = (new_dt - cur).total_seconds() / 60.0
    _set_current(new_dt, delta_minutes=delta)
    return get_state()


def set_date(year: int, month: int, day: int) -> Dict[str, Any]:
    """Set date, keep current time of day."""
    with _lock:
        cur = _current
    y = _coerce_int(year, "year")
    mo = _coerce_int(month, "month")
    d = _coerce_int(day, "day")
    try:
        new_dt = datetime.datetime(y, mo, d, cur.hour, cur.minute, cur.second)
    except ValueError as e:
        raise ValueError(f"Invalid date {y}-{mo}-{d}: {e}")
    delta = (new_dt - cur).total_seconds() / 60.0
    _set_current(new_dt, delta_minutes=delta)
    return get_state()


def set_time(hour: int, minute: int, second: int = 0) -> Dict[str, Any]:
    """Set time of day, keep current date."""
    with _lock:
        cur = _current
    h = _coerce_int(hour, "hour")
    mi = _coerce_int(minute, "minute")
    s = _coerce_int(second, "second")
    if not (0 <= h <= 23):
        raise ValueError("hour must be 0..23")
    if not (0 <= mi <= 59):
        raise ValueError("minute must be 0..59")
    if not (0 <= s <= 59):
        raise ValueError("second must be 0..59")
    try:
        new_dt = datetime.datetime(cur.year, cur.month, cur.day, h, mi, s)
    except ValueError as e:
        raise ValueError(f"Invalid time {h}:{mi}:{s}: {e}")
    delta = (new_dt - cur).total_seconds() / 60.0
    _set_current(new_dt, delta_minutes=delta)
    return get_state()


def advance(
    minutes: float = 0,
    hours: float = 0,
    days: float = 0,
    seconds: float = 0,
) -> Dict[str, Any]:
    """
    Advance game time by delta. Negative values go backwards.

    Args:
        minutes: Minutes to advance (can be fractional).
        hours: Hours to advance.
        days: Days to advance.
        seconds: Seconds to advance.

    Returns state dict.
    """
    total_minutes = float(minutes) + float(hours) * 60.0 + float(days) * 1440.0 + float(seconds) / 60.0
    if total_minutes == 0:
        # No-op still returns state but doesn't notify
        return get_state()
    delta = datetime.timedelta(minutes=total_minutes)
    with _lock:
        cur = _current
        new_dt = cur + delta
    _set_current(new_dt, delta_minutes=total_minutes)
    return get_state()


def advance_minutes(minutes: float) -> Dict[str, Any]:
    """Advance by minutes (fractional allowed)."""
    return advance(minutes=float(minutes))


def advance_hours(hours: float) -> Dict[str, Any]:
    """Advance by hours."""
    return advance(hours=float(hours))


def advance_days(days: float) -> Dict[str, Any]:
    """Advance by days."""
    return advance(days=float(days))


def tick(minutes: float = 1) -> Dict[str, Any]:
    """
    Single tick helper for the future game loop.

    Respects ``paused`` — if paused, does nothing.
    """
    if is_paused():
        return get_state()
    return advance_minutes(float(minutes))


def set_time_scale(scale: float) -> Dict[str, Any]:
    """Set game time scale (game minutes per real minute). Must be >= 0."""
    scale_f = float(scale)
    if scale_f < 0:
        raise ValueError("time_scale must be >= 0")
    global _time_scale
    with _lock:
        _time_scale = scale_f
    return get_state()


def set_paused(paused: bool) -> Dict[str, Any]:
    """Pause or unpause time ticking."""
    global _paused
    with _lock:
        _paused = bool(paused)
    return get_state()


def reset_to_start() -> Dict[str, Any]:
    """Reset clock to START_DATETIME."""
    with _lock:
        cur = _current
    delta = (START_DATETIME - cur).total_seconds() / 60.0
    _set_current(START_DATETIME, delta_minutes=delta)
    return get_state()


# ---------------------------------------------------------------------------
# Subscriptions — for future systems (weather, spoilage, rent, etc.)
# ---------------------------------------------------------------------------

def subscribe(callback: Callable[[Dict[str, Any]], None]) -> Callable[[], None]:
    """
    Subscribe to time changes.

    Args:
        callback: fn(event_dict) called on every advance/set.

    Returns:
        Unsubscribe callable: call it to remove the subscription.

    Example:
        def on_tick(evt):
            if evt["crossed_midnight"]:
                print("New day:", evt["new"])

        unsub = subscribe(on_tick)
        advance_days(1)  # triggers callback
        unsub()          # stop listening
    """
    if not callable(callback):
        raise ValueError("subscribe callback must be callable")
    with _lock:
        if callback not in _subscribers:
            _subscribers.append(callback)

    def _unsub() -> None:
        try:
            with _lock:
                if callback in _subscribers:
                    _subscribers.remove(callback)
        except Exception:
            pass

    return _unsub


def unsubscribe(callback: Callable[[Dict[str, Any]], None]) -> bool:
    """Remove a previously registered subscriber. Returns True if removed."""
    with _lock:
        if callback in _subscribers:
            _subscribers.remove(callback)
            return True
    return False


def _reset_for_tests() -> None:
    """Reset clock, scale, paused, subscribers, tick count — for tests."""
    global _current, _time_scale, _paused, _tick_count
    with _lock:
        _current = START_DATETIME
        _time_scale = DEFAULT_TIME_SCALE
        _paused = False
        _tick_count = 0
        _subscribers.clear()

# ---------------------------------------------------------------------------
# Save / Load provider
# ---------------------------------------------------------------------------

def _save_gametime() -> Dict[str, Any]:
    """Return JSON-serializable state for save manager."""
    with _lock:
        dt = _current
        scale = _time_scale
        paused = _paused
        tick = _tick_count
    return {
        "iso": dt.isoformat(),
        "year": dt.year,
        "month": dt.month,
        "day": dt.day,
        "hour": dt.hour,
        "minute": dt.minute,
        "second": dt.second,
        "time_scale": scale,
        "paused": paused,
        "tick": tick,
    }


def _load_gametime(state: Any) -> None:
    """Restore from save state (dict from _save_gametime)."""
    global _current, _time_scale, _paused, _tick_count
    if not isinstance(state, dict):
        try:
            from core.systems.orchestrator import warning as _warn
            _warn(f"_load_gametime: expected dict, got {type(state).__name__}")
        except Exception:
            pass
        return
    # Prefer iso if present
    iso = state.get("iso")
    try:
        if iso:
            dt = datetime.datetime.fromisoformat(str(iso))
        else:
            # Fallback to components
            y = int(state.get("year", START_YEAR))
            mo = int(state.get("month", START_MONTH))
            d = int(state.get("day", START_DAY))
            h = int(state.get("hour", START_HOUR))
            mi = int(state.get("minute", START_MINUTE))
            s = int(state.get("second", START_SECOND))
            dt = datetime.datetime(y, mo, d, h, mi, s)
    except Exception as e:
        try:
            from core.systems.orchestrator import warning as _warn
            _warn(f"_load_gametime: invalid datetime in save: {e}")
        except Exception:
            pass
        return

    scale = state.get("time_scale", DEFAULT_TIME_SCALE)
    paused = state.get("paused", False)
    tick = state.get("tick", 0)
    try:
        scale_f = float(scale)
        if scale_f < 0:
            scale_f = DEFAULT_TIME_SCALE
    except Exception:
        scale_f = DEFAULT_TIME_SCALE

    with _lock:
        _current = dt
        _time_scale = scale_f
        _paused = bool(paused)
        try:
            _tick_count = int(tick)
        except Exception:
            _tick_count = 0


try:
    from core.systems.save.registry import register_save_provider as _reg
    _reg("gametime", _save_gametime, _load_gametime)
    # Alias keys so either "time" or "gametime" in old saves works if someone
    # hand-edits. The save manager iterates providers; we only need one key
    # but alias helps for backwards compat if both are checked on load?
    # Instead we register an alias key "time" that shares same fns (save writes
    # both keys, load restores either — idempotent).
    _reg("time", _save_gametime, _load_gametime)
except Exception:
    pass

# ---------------------------------------------------------------------------
# Command registry — dashboard / other systems can drive time via execute()
# ---------------------------------------------------------------------------

try:
    from core.command_registry import command as _command
except ImportError:  # graceful when imported in isolation
    def _command(*_a, **_k):  # type: ignore
        def _d(fn): return fn
        return _d


@_command("time.get", "Get current game datetime and formatted strings", category="player")
def time_get() -> dict:
    """Return current game time as dict (for dashboards)."""
    return {"status": "success", **get_state()}


@_command("time.now", "Alias for time.get — current game datetime", category="player")
def time_now() -> dict:
    return {"status": "success", **get_state()}


@_command("time.format", "Get formatted game datetime string", category="player")
def time_format(fmt: str = "", include_weekday: bool = True) -> dict:
    """Return formatted string. Pass fmt as strftime pattern if desired."""
    formatted = get_formatted(fmt if fmt else None, include_weekday=bool(include_weekday))
    return {"status": "success", "formatted": formatted, **get_state()}


@_command("time.set", "Set game datetime (year month day hour minute second or iso)", category="dev")
def time_set(
    year: Optional[int] = None,
    month: Optional[int] = None,
    day: Optional[int] = None,
    hour: Optional[int] = None,
    minute: Optional[int] = None,
    second: Optional[int] = None,
    iso: Optional[str] = None,
) -> dict:
    """
    Set game datetime. Provide either iso like "2015-06-14T09:30" or
    components. Missing components keep current value.
    """
    state = set_datetime(year=year, month=month, day=day, hour=hour, minute=minute, second=second, iso=iso)
    return {"status": "success", "message": f"Time set to {state['formatted']}", **state}


@_command("time.set_date", "Set game date (year month day), keep time of day", category="dev")
def time_set_date(year: int, month: int, day: int) -> dict:
    state = set_date(int(year), int(month), int(day))
    return {"status": "success", "message": f"Date set to {state['date_str']}", **state}


@_command("time.set_time", "Set game time of day (hour minute second), keep date", category="dev")
def time_set_time(hour: int, minute: int, second: int = 0) -> dict:
    state = set_time(int(hour), int(minute), int(second))
    return {"status": "success", "message": f"Time set to {state['time_str_seconds']}", **state}


@_command("time.advance", "Advance game time by delta (minutes/hours/days/seconds)", category="dev")
def time_advance(
    minutes: float = 0,
    hours: float = 0,
    days: float = 0,
    seconds: float = 0,
) -> dict:
    """
    Advance clock.

    Example: time.advance hours=6
             time.advance days=1 minutes=30
    """
    state = advance(minutes=float(minutes), hours=float(hours), days=float(days), seconds=float(seconds))
    # Use ascii for Windows console compatibility
    return {"status": "success", "message": f"Advanced to {state['formatted']}", **state}


@_command("time.add_minutes", "Advance game time by minutes", category="player")
def time_add_minutes(minutes: float) -> dict:
    state = advance_minutes(float(minutes))
    return {"status": "success", "message": f"+{float(minutes):g} min -> {state['formatted']}", **state}


@_command("time.add_hours", "Advance game time by hours", category="player")
def time_add_hours(hours: float) -> dict:
    state = advance_hours(float(hours))
    return {"status": "success", "message": f"+{float(hours):g} h -> {state['formatted']}", **state}


@_command("time.add_days", "Advance game time by days", category="player")
def time_add_days(days: float) -> dict:
    state = advance_days(float(days))
    return {"status": "success", "message": f"+{float(days):g} days -> {state['formatted']}", **state}


@_command("time.tick", "Advance game clock by one tick (default 1 minute, respects pause)", category="dev")
def time_tick(minutes: float = 1) -> dict:
    state = tick(float(minutes))
    return {"status": "success", "message": f"Tick {float(minutes):g} min -> {state['formatted']}", **state}


@_command("time.scale", "Get or set time scale (game minutes per real minute)", category="dev")
def time_scale(scale: Optional[float] = None) -> dict:
    """If scale is None, just returns current; otherwise sets it."""
    if scale is None:
        return {"status": "success", **get_state()}
    state = set_time_scale(float(scale))
    return {"status": "success", "message": f"Time scale set to {state['time_scale']}", **state}


@_command("time.pause", "Pause or unpause game time (paused=true/false)", category="dev")
def time_pause(paused: bool = True) -> dict:
    # Allow string bool variants via command_registry (will be bool already if typed)
    if isinstance(paused, str):
        paused = paused.strip().lower() in ("true", "1", "yes", "on")
    state = set_paused(bool(paused))
    return {"status": "success", "message": f"{'Paused' if state['paused'] else 'Unpaused'}", **state}


@_command("time.reset", "Reset game clock to 2015-01-01 06:00", category="dev")
def time_reset() -> dict:
    state = reset_to_start()
    return {"status": "success", "message": f"Reset to {state['formatted']}", **state}


__all__ = [
    "START_DATETIME", "START_YEAR", "START_MONTH", "START_DAY", "START_HOUR", "START_MINUTE",
    "WEEKDAY_NAMES", "MONTH_NAMES", "DEFAULT_TIME_SCALE",
    "get_datetime", "get_date", "get_time", "get_iso", "get_formatted",
    "get_weekday", "get_weekday_name", "get_month_name", "get_day_of_year",
    "is_weekend", "get_year", "get_month", "get_day", "get_hour", "get_minute", "get_second",
    "days_elapsed", "get_time_scale", "is_paused", "get_state",
    "set_datetime", "set_date", "set_time", "advance", "advance_minutes", "advance_hours", "advance_days",
    "tick", "set_time_scale", "set_paused", "reset_to_start",
    "subscribe", "unsubscribe", "_reset_for_tests",
]
