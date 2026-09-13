"""
MTT Dashboard V5 — Textual command-prompt hub over the command registry.

Run:
    python -m core.renderer.dashboard_v5.dashboardv5
    python dashboard_v5.py

Prompt syntax (key=value + positional, per V5 spec):
    <command> [positional...] [key=value...]

    inventory.add 1 101 quantity=3
    economy.balance player_id=1
    system.echo text="hello world"

Type a command prefix and a dropdown filters as you type.
Tab (or click) completes the highlighted suggestion; Up/Down moves
through the dropdown, Enter runs (or completes a partial command).
Later tokens complete param names as ``name=`` — and once a known
param has ``=``, its plausible values are suggested too
(e.g. ``bank.join bank_name=`` offers the bank list).

Builtins (handled locally, also suggested):
    help [cmd] | commands [filter] | describe <cmd> | clear | history | exit

Only depends on ``core.command_registry`` + ``core.output`` — new
``@command`` files appear automatically via registry autodiscovery.
Textual is required only to launch the UI; the parser/suggester
helpers import cleanly without it (so tests stay light).
"""

from __future__ import annotations

import argparse
import ast
import json
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Paths ---------------------------------------------------------------------
# core/renderer/dashboard_v5/dashboardv5.py -> parents[3] -> MilkToastTaco/
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Value coercion
# ---------------------------------------------------------------------------

def coerce_value(raw: str) -> Any:
    """Coerce a CLI token string to int/float/bool/None/list/dict/str.

    Order: quoted strings stay strings, then bool/null words, int,
    float, JSON/AST list-dict, else plain string.
    """
    s = raw.strip()
    # bool / null words
    low = s.lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    if low in ("none", "null", "nil", "~"):
        return None
    # int (incl. negative)
    try:
        if s and (s.lstrip("+-").isdigit()):
            return int(s)
    except Exception:
        pass
    # float
    try:
        if any(c in s for c in (".", "e", "E")):
            return float(s)
    except Exception:
        pass
    # list / dict / tuple via JSON first, then literal_eval
    if s[:1] in ("[", "{", "("):
        try:
            return json.loads(s)
        except Exception:
            pass
        try:
            return ast.literal_eval(s)
        except Exception:
            pass
    return s


# ---------------------------------------------------------------------------
# Command-line parsing: <command> [positional...] [key=value...]
# ---------------------------------------------------------------------------

@dataclass
class ParsedLine:
    command: str
    args: List[Any]
    kwargs: Dict[str, Any]


def parse_command_line(line: str) -> ParsedLine:
    """Parse one prompt line into (command, args, kwargs).

    - First token is the command name (a leading ``/`` or ``>`` is stripped
      so ``/help`` and ``>help`` work like ``help``).
    - Tokens containing ``=`` become kwargs (leading ``--`` stripped, so
      both ``quantity=3`` and ``--quantity=3`` work).
    - Everything else is a positional arg, coerced via :func:`coerce_value`.
    - Respects quotes: ``text="hello world"`` -> ``{"text": "hello world"}``.
    """
    text = (line or "").strip()
    if not text:
        return ParsedLine(command="", args=[], kwargs={})
    try:
        tokens = shlex.split(text, posix=True)
    except ValueError:
        # Unbalanced quote — fall back to naive split so typing stays live
        tokens = text.split()
    if not tokens:
        return ParsedLine(command="", args=[], kwargs={})
    cmd = tokens[0].lstrip("/>").strip().lower()
    args: List[Any] = []
    kwargs: Dict[str, Any] = {}
    i = 0
    rest = tokens[1:]
    while i < len(rest):
        tok = rest[i]
        if "=" in tok:
            key, _, val = tok.partition("=")
            key = key.strip().lstrip("-").strip().lower().replace("-", "_")
            if not key:
                i += 1
                continue
            kwargs[key] = coerce_value(val.strip())
            i += 1
        elif tok.startswith("--") and len(tok) > 2:
            # --key value  /  --flag (boolean) two-token form
            key = tok[2:].strip().lower().replace("-", "_")
            nxt = rest[i + 1] if i + 1 < len(rest) else None
            if nxt is not None and "=" not in nxt and not nxt.startswith("--"):
                kwargs[key] = coerce_value(nxt.strip())
                i += 2
            else:
                kwargs[key] = True
                i += 1
        else:
            args.append(coerce_value(tok))
            i += 1
    return ParsedLine(command=cmd, args=args, kwargs=kwargs)


def split_line_for_completion(line: str) -> Tuple[str, List[str], str, bool]:
    """Split a raw (unstripped-right) line for suggestion purposes.

    Returns (cmd_token, middle_tokens, current_token, ends_with_space).
    Unlike :func:`parse_command_line`, this preserves the in-progress
    last token and does not coerce anything.
    """
    ends_with_space = len(line) > 0 and line[-1] in (" ", "\t")
    try:
        tokens = shlex.split(line, posix=True)
    except ValueError:
        tokens = line.split()
    if line.strip() == "":
        return ("", [], "", True)
    if not tokens:
        # line is all whitespace
        return ("", [], "", True)
    if ends_with_space:
        return (tokens[0], tokens[1:], "", True)
    # last token is in progress
    if len(tokens) == 1:
        return (tokens[0], [], tokens[0], False)
    return (tokens[0], tokens[1:-1], tokens[-1], False)


# ---------------------------------------------------------------------------
# Suggestions (pure logic — no Textual import, unit-testable)
# ---------------------------------------------------------------------------

BUILTINS: List[Dict[str, Any]] = [
    {"name": "help", "help": "Show help — 'help' lists, 'help <cmd>' details", "category": "builtin", "params": [{"name": "cmd", "required": False}]},
    {"name": "commands", "help": "List registry commands — 'commands [filter]'", "category": "builtin", "params": [{"name": "filter", "required": False}]},
    {"name": "describe", "help": "Show params for a command — 'describe <cmd>'", "category": "builtin", "params": [{"name": "cmd", "required": True}]},
    {"name": "clear", "help": "Clear the screen", "category": "builtin", "params": []},
    {"name": "history", "help": "Show command history", "category": "builtin", "params": []},
    {"name": "exit", "help": "Quit Dashboard V5 (alias: quit)", "category": "builtin", "params": []},
    {"name": "quit", "help": "Quit Dashboard V5 (alias: exit)", "category": "builtin", "params": []},
    {"name": "launcher", "help": "Exit Dashboard V5 and return to the MTT launcher", "category": "builtin", "params": []},
]

_BUILTIN_NAMES = {b["name"] for b in BUILTINS}


@dataclass
class Suggestion:
    """One dropdown row: what to show + what to insert."""
    display: str       # rich-markup row shown in the dropdown
    completion: str    # full replacement line when accepted
    insert: str        # token fragment inserted (for reference)
    hint: str = ""     # short right-side hint (help text / annotation)
    append_space: bool = False  # add trailing space (finished value -> next arg)


def _registry_commands() -> List[Dict[str, Any]]:
    try:
        from core.command_registry import list_commands as _list
        return _list()
    except Exception:
        return []


def all_command_entries() -> List[Dict[str, Any]]:
    """Builtins + registry commands (builtins first, then alpha)."""
    cmds = list(BUILTINS)
    seen = set(_BUILTIN_NAMES)
    for c in _registry_commands():
        if c.get("name") not in seen:
            cmds.append(c)
            seen.add(c.get("name"))
    return cmds


def command_matches(prefix: str, limit: int = 12) -> List[Dict[str, Any]]:
    """Filter all commands by prefix (substring, case-insensitive)."""
    p = (prefix or "").strip().lstrip("/>").lower()
    entries = all_command_entries()
    if not p:
        return sorted(entries, key=lambda c: c["name"])[:limit]
    scored: List[Tuple[int, Dict[str, Any]]] = []
    for c in entries:
        name = str(c.get("name", ""))
        low = name.lower()
        if low.startswith(p):
            scored.append((0, c))
        elif p in low:
            scored.append((1, c))
        elif p in str(c.get("help", "")).lower():
            scored.append((2, c))
    scored.sort(key=lambda t: (t[0], t[1].get("name", "")))
    return [c for _, c in scored[:limit]]


def _param_hint(p: Dict[str, Any]) -> str:
    ann = p.get("annotation", "")
    req = "required" if p.get("required") else "optional"
    default = p.get("default", None)
    extra = f" = {default!r}" if p.get("has_default") else ""
    return f"{ann} · {req}{extra}".strip(" ·")


def _get_params(cmd_name: str) -> List[Dict[str, Any]]:
    """Registry param dicts for a command, or [] if unknown."""
    try:
        from core.command_registry import get_command as _get
        spec = _get(cmd_name)
        if spec is not None:
            return list(spec.params)
    except Exception:
        pass
    return []


# ---------------------------------------------------------------------------
# Per-param value providers — `bank.join bank_name=<TAB>` suggests banks.
#
# Register with @value_provider("bank.join", "bank_name"). The command may
# be "*" to cover a param name on every command (e.g. player_id).
# Providers return [(value, hint)] and must never raise (wrap in
# try/except, return [] when the system has no data).
# ---------------------------------------------------------------------------

_ValueRow = Tuple[str, str]  # (value, hint)

_VALUE_PROVIDERS: Dict[Tuple[str, str], Callable[[], List[_ValueRow]]] = {}


def value_provider(command: str, param: str):
    """Decorator registering value completion for one command param.

    Example:
        @value_provider("bank.join", "bank_name")
        def _bank_names():
            from core.systems.economy.bank import get_bank_names
            return [(b, "bank") for b in get_bank_names()]

    Use command="*" for a param name shared across commands.
    New systems add their own providers — no V5 edits needed.
    """
    key = (command.strip().lower(), param.strip().lower())

    def deco(fn: Callable[[], List[_ValueRow]]) -> Callable[[], List[_ValueRow]]:
        _VALUE_PROVIDERS[key] = fn
        return fn

    return deco


def provider_values(cmd_name: str, param_name: str) -> List[_ValueRow]:
    """Look up registered values: exact (cmd, param) first, then (*, param)."""
    cmd = (cmd_name or "").strip().lower()
    par = (param_name or "").strip().lower()
    fn = _VALUE_PROVIDERS.get((cmd, par)) or _VALUE_PROVIDERS.get(("*", par))
    if fn is None:
        return []
    try:
        rows = fn() or []
    except Exception:
        return []
    out: List[_ValueRow] = []
    for r in rows:
        try:
            if isinstance(r, (tuple, list)):
                out.append((str(r[0]), str(r[1]) if len(r) > 1 else ""))
            else:
                out.append((str(r), ""))
        except Exception:
            continue
    return out


def _quote_value(v: str) -> str:
    """Quote a value for the prompt line if it contains whitespace."""
    if any(c in v for c in (" ", "\t", '"', "'")):
        return '"' + v.replace('"', "'") + '"'
    return v


# -- built-in providers (live game data, best-effort) ------------------------

def _players_provider() -> List[_ValueRow]:
    try:
        from core.systems import player_manager as _pm
        ids = sorted(getattr(_pm, "_players", {}).keys(),
                     key=lambda k: int(k) if str(k).isdigit() else str(k))
        if ids:
            return [(str(i), "player") for i in ids]
    except Exception:
        pass
    return [("1", "player")]


value_provider("*", "player_id")(_players_provider)


@value_provider("*", "agent_id")
def _agents_provider() -> List[_ValueRow]:
    try:
        from core.systems.realestate.realestate import get_catalog as _cat
        agents = (_cat() or {}).get("agents", [])
        return [(a.get("id", ""), a.get("name", "agent"))
                for a in agents if isinstance(a, dict) and a.get("id")]
    except Exception:
        return []


@value_provider("*", "level")
def _levels_provider() -> List[_ValueRow]:
    try:
        from core.output import VALID_LEVELS
        return [(lvl, "output level") for lvl in sorted(VALID_LEVELS)]
    except Exception:
        return [("info", "output level")]


@value_provider("*", "channel")
def _channels_provider() -> List[_ValueRow]:
    return [(c, "output channel") for c in ("general", "toast", "log", "debug", "system")]


def _bank_names_provider() -> List[_ValueRow]:
    try:
        from core.systems.economy.bank import get_bank_names as _names
        return [(b, "bank") for b in _names()]
    except Exception:
        return []


for _cmd in ("bank.apply", "bank.join", "bank.leave"):
    value_provider(_cmd, "bank_name")(_bank_names_provider)
value_provider("bank.get_loan", "bank")(_bank_names_provider)


def _item_ids_provider() -> List[_ValueRow]:
    try:
        from core.systems.inventory.loader import get_all_item_defs as _all
        defs = _all() or {}
        return [(str(i), getattr(d, "name", f"item {i}"))
                for i, d in sorted(defs.items(), key=lambda kv: kv[0])]
    except Exception:
        return []


for _cmd in ("inventory.add", "inventory.has", "inventory.remove_item"):
    value_provider(_cmd, "item_id")(_item_ids_provider)


def _property_ids_provider() -> List[_ValueRow]:
    try:
        from core.systems.realestate.realestate import get_catalog as _cat
        props = (_cat() or {}).get("properties", [])
        rows: List[_ValueRow] = []
        for p in props:
            if not isinstance(p, dict) or not p.get("id"):
                continue
            label = str(p.get("name", p["id"]))
            price = p.get("price", 0) or 0
            try:
                hint = f"{label} · ${int(price):,}"
            except Exception:
                hint = label
            rows.append((str(p["id"]), hint))
        return rows
    except Exception:
        return []


for _cmd in ("realestate.buy", "realestate.cancel_rent", "realestate.garage",
             "realestate.info", "realestate.rent", "realestate.retrieve_vehicle",
             "realestate.sell", "realestate.store_vehicle"):
    value_provider(_cmd, "property_id")(_property_ids_provider)
for _cmd in ("realestate.buy", "realestate.cancel_rent", "realestate.garage",
             "realestate.rent", "realestate.sell"):
    value_provider(_cmd, "id")(_property_ids_provider)


def _vehicle_ids_provider() -> List[_ValueRow]:
    try:
        from core.systems.shop.vehicle_shop import get_catalog as _cat
        vehicles = (_cat() or {}).get("vehicles", [])
        rows2: List[_ValueRow] = []
        for v in vehicles:
            if not isinstance(v, dict) or not v.get("id"):
                continue
            label = str(v.get("name", v["id"]))
            price = v.get("price", 0) or 0
            try:
                hint = f"{label} · ${int(price):,}"
            except Exception:
                hint = label
            rows2.append((str(v["id"]), hint))
        return rows2
    except Exception:
        return []


for _cmd in ("vehicleshop.buy", "vehicleshop.info"):
    value_provider(_cmd, "vehicle_id")(_vehicle_ids_provider)
for _cmd in ("vehicleshop.buy", "vehicleshop.sell"):
    value_provider(_cmd, "id")(_vehicle_ids_provider)


@value_provider("vehicleshop.list_vehicles", "category")
def _vehicle_categories_provider() -> List[_ValueRow]:
    try:
        from core.systems.shop.vehicle_shop import get_categories as _cats
        return [(c.get("id", ""), c.get("name", "category"))
                for c in (_cats() or []) if isinstance(c, dict) and c.get("id")]
    except Exception:
        return []


@value_provider("realestate.list_properties", "type")
def _property_types_provider() -> List[_ValueRow]:
    try:
        from core.systems.realestate.realestate import get_catalog as _cat
        types = sorted({p.get("type") for p in (_cat() or {}).get("properties", [])
                        if isinstance(p, dict) and p.get("type")})
        return [(t, "property type") for t in types] or [
            (t, "property type") for t in
            ("house", "apartment", "farm", "business", "commercial", "vacant_land")]
    except Exception:
        return []


@value_provider("phone.delete_contact", "contact_name")
def _contacts_provider() -> List[_ValueRow]:
    try:
        from core.systems.phone.phone import contacts_list as _contacts
        if isinstance(_contacts, dict):
            return [(k, "contact") for k in sorted(_contacts.keys())]
    except Exception:
        pass
    return []


@value_provider("time.scale", "scale")
def _scales_provider() -> List[_ValueRow]:
    try:
        from core.systems.gametime.manager import get_allowed_scales as _scales
        return [(str(int(s) if float(s).is_integer() else s), f"{s}× speed")
                for s in (_scales() or [])]
    except Exception:
        return []


def arg_suggestions(cmd_name: str, token: str, used_keys: List[str], limit: int = 12) -> List[Suggestion]:
    """Suggest ``name=`` params for a bare (no ``=``) in-progress arg token.

    ``used_keys`` are kwarg names already present on the line (excluded).
    For ``key=value`` tokens use :func:`arg_value_suggestions` instead.
    """
    key_part = token.lstrip("-").lower().replace("-", "_")
    params = _get_params(cmd_name)
    if not params:
        # builtin fallback: complete nested command names for help/describe
        if cmd_name in ("help", "describe"):
            out: List[Suggestion] = []
            for c in command_matches(key_part, limit=limit):
                out.append(Suggestion(
                    display=f"[bold]{c['name']}[/]  [dim]{c.get('help','')}[/]",
                    completion=f"{cmd_name} {c['name']}",
                    insert=c["name"],
                    hint=str(c.get("help", "")),
                ))
            return out
        return []
    used = {u.lower() for u in used_keys}
    cands = [p for p in params if p["name"].lower() not in used]
    if key_part:
        cands = [p for p in cands if p["name"].lower().startswith(key_part)]
    # required-first ordering
    cands.sort(key=lambda p: (not p.get("required", False), p["name"]))
    out2: List[Suggestion] = []
    for p in cands[:limit]:
        hint = _param_hint(p)
        out2.append(Suggestion(
            display=f"[bold]{p['name']}=[/]  [dim]{hint}[/]",
            completion="",
            insert=f"{p['name']}=",
            hint=hint,
        ))
    return out2


def arg_value_suggestions(cmd_name: str, key: str, val_prefix: str, limit: int = 12) -> List[Suggestion]:
    """Suggest values for a ``key=value`` token whose key matches a param.

    Values come from :func:`provider_values` (best-effort live game data);
    ``bool`` params always offer true/false. Returns [] when nothing is
    known — the caller then shows no dropdown rather than wrong guesses.
    """
    params = _get_params(cmd_name)
    match = next((p for p in params if p["name"].lower() == key.lower()), None)
    if match is None:
        return []
    rows = provider_values(cmd_name, match["name"])
    if not rows and match.get("annotation") == "bool":
        rows = [("true", "boolean"), ("false", "boolean")]
    if not rows:
        return []
    vp = (val_prefix or "").strip().strip("'\"").lower()
    out: List[Suggestion] = []
    for v, hint in rows:
        if vp and not v.lower().startswith(vp):
            continue
        disp = f"[bold]{match['name']}={v}[/]"
        if hint:
            disp += f"  [dim]{hint}[/]"
        out.append(Suggestion(
            display=disp,
            completion="",
            insert=f"{match['name']}={_quote_value(v)}",
            hint=hint,
            append_space=True,
        ))
    return out[:limit]


def positional_value_suggestions(cmd_name: str, middle: List[str], token: str,
                                 used_keys: List[str], limit: int = 12) -> List[Suggestion]:
    """Suggest values for the positional slot the cursor is filling.

    Slot = number of positional tokens already on the line, mapped onto the
    command's params in order (params already given as ``key=value`` are
    skipped). E.g. ``bank.join 1 <TAB>`` offers bank names for slot 1.
    """
    params = _get_params(cmd_name)
    if not params:
        return []
    used = {u.lower() for u in used_keys}
    positionals = [t for t in middle if "=" not in t and not t.lstrip().startswith("--")]
    avail = [p for p in params if p["name"].lower() not in used]
    if len(positionals) >= len(avail):
        return []
    target = avail[len(positionals)]
    rows = provider_values(cmd_name, target["name"])
    if not rows and target.get("annotation") == "bool":
        rows = [("true", "boolean"), ("false", "boolean")]
    if not rows:
        return []
    tp = (token or "").strip().strip("'\"").lower()
    out: List[Suggestion] = []
    for v, hint in rows:
        if tp and not v.lower().startswith(tp):
            continue
        disp = f"[bold]{v}[/]  [dim]{target['name']}"
        if hint:
            disp += f" · {hint}"
        disp += "[/]"
        out.append(Suggestion(
            display=disp,
            completion="",
            insert=_quote_value(v),
            hint=hint,
            append_space=True,
        ))
    return out[:limit]


def get_suggestions(line: str, limit: int = 12) -> List[Suggestion]:
    """Top-level suggester for the prompt's current text.

    - Completing the first token -> command matches.
    - Bare later tokens -> ``param=`` matches (falling back to positional
      value matches when no param name fits).
    - Empty token after a space -> remaining ``param=`` rows plus value
      rows for the positional slot being filled.
    - ``key=value`` tokens -> value matches for that param.
    """
    if line.strip() == "":
        return [
            Suggestion(
                display=f"[bold]{c['name']}[/]  [dim]{c.get('help','')}[/]",
                completion=c["name"] + " ",
                insert=c["name"],
                hint=str(c.get("help", "")),
            )
            for c in command_matches("", limit=limit)
        ]
    cmd_tok, middle, current, ends_ws = split_line_for_completion(line)
    if not middle and not ends_ws and " " not in line.strip():
        # still on first token
        prefix = cmd_tok.lstrip("/>")
        out: List[Suggestion] = []
        for c in command_matches(prefix, limit=limit):
            out.append(Suggestion(
                display=f"[bold]{c['name']}[/]  [dim]{c.get('help','')}[/]",
                completion=c["name"] + " ",
                insert=c["name"],
                hint=str(c.get("help", "")),
            ))
        return out
    # completing an argument
    cmd_name = cmd_tok.lstrip("/>").lower()
    used_keys: List[str] = []
    for tok in middle:
        if "=" in tok:
            used_keys.append(tok.partition("=")[0].lstrip("-").lower().replace("-", "_"))
    head = line[: len(line) - len(current)] if not ends_ws else line
    if head and not head.endswith((" ", "\t")):
        head += " "

    def _final(rows: List[Suggestion]) -> List[Suggestion]:
        fixed: List[Suggestion] = []
        for s in rows:
            tail = " " if s.append_space else ""
            fixed.append(Suggestion(display=s.display, completion=head + s.insert + tail,
                                    insert=s.insert, hint=s.hint, append_space=s.append_space))
        return fixed

    if "=" in current:
        # key=value -> value completion for that param
        raw_key, _, raw_val = current.partition("=")
        key = raw_key.lstrip("-").lower().replace("-", "_")
        vals = arg_value_suggestions(cmd_name, key, raw_val, limit=limit)
        if vals:
            return _final(vals)
        # partial key with '=' typed early — fall back to param-name rows
        return _final(arg_suggestions(cmd_name, key, used_keys, limit=limit))
    if ends_ws or current == "":
        # fresh arg: remaining param= rows + positional-slot value rows
        rows = arg_suggestions(cmd_name, "", used_keys, limit=limit)
        seen_inserts = {s.insert for s in rows}
        for s in positional_value_suggestions(cmd_name, middle, "", used_keys,
                                              limit=limit - len(rows)):
            if s.insert not in seen_inserts:
                rows.append(s)
                seen_inserts.add(s.insert)
        return _final(rows)
    rows2 = arg_suggestions(cmd_name, current, used_keys, limit=limit)
    if not rows2:
        # no param name fits — try positional values (e.g. `bank.join 1 Coa`)
        rows2 = positional_value_suggestions(cmd_name, middle, current, used_keys, limit=limit)
    return _final(rows2)


# ---------------------------------------------------------------------------
# Execution (builtins + registry dispatch)
# ---------------------------------------------------------------------------

def execute_line(line: str) -> Tuple[str, str]:
    """Execute one prompt line. Returns (status, rendered_text).

    ``status`` is one of "success" | "error" | "info" | "exit" | "empty".
    ``rendered_text`` is rich-markup for the output pane.
    """
    parsed = parse_command_line(line)
    if not parsed.command:
        return ("empty", "")
    cmd = parsed.command

    if cmd in ("exit", "quit"):
        return ("exit", "[dim]Bye — Dashboard V5 closed.[/]")
    if cmd == "launcher":
        return ("exit", "[dim]Returning to launcher…[/]")
    if cmd == "clear":
        return ("clear", "")
    if cmd == "history":
        return ("history", "")
    if cmd in ("help", "commands", "describe"):
        return _run_help_builtin(cmd, parsed)
    # registry dispatch
    try:
        from core.command_registry import execute as _exec
        res = _exec(cmd, *parsed.args, **parsed.kwargs)
    except Exception as e:
        return ("error", f"[red]error:[/] {e}")
    return _render_result(cmd, res)


def _run_help_builtin(cmd: str, parsed: ParsedLine) -> Tuple[str, str]:
    entries = all_command_entries()
    if cmd == "commands":
        filt = " ".join(str(a) for a in parsed.args) or parsed.kwargs.get("filter", "")
        filt = str(filt or "").lower()
        rows = [c for c in entries if not filt or filt in c["name"].lower() or filt in str(c.get("help", "")).lower()]
        if not rows:
            return ("info", f"[yellow]No commands match '{filt}'.[/]")
        lines = [f"[bold]{len(rows)} commands[/]  [dim](type 'describe <cmd>' for params)[/]"]
        for c in sorted(rows, key=lambda c: c["name"])[:60]:
            lines.append(f"  [cyan]{c['name']}[/]  [dim]{c.get('help','')}[/]")
        if len(rows) > 60:
            lines.append(f"  [dim]… and {len(rows) - 60} more[/]")
        return ("info", "\n".join(lines))
    # help [cmd] / describe <cmd>
    target = ""
    if parsed.args:
        target = str(parsed.args[0]).lower()
    elif parsed.kwargs:
        target = str(next(iter(parsed.kwargs.values()))).lower()
    if not target:
        lines = [
            "[bold]MTT Dashboard V5[/] — type a command, Tab completes, Enter runs.",
            "",
            "[bold]Syntax:[/]  <command> [positional...] [key=value...]",
            "  [cyan]inventory.add 1 101 quantity=3[/]",
            "  [cyan]economy.balance player_id=1[/]",
            "",
            "[bold]Builtins:[/]",
        ]
        for b in BUILTINS:
            lines.append(f"  [cyan]{b['name']}[/]  [dim]{b['help']}[/]")
        lines.append("")
        lines.append("[dim]Type 'commands' to list all registry commands.[/]")
        return ("info", "\n".join(lines))
    # detail for one command
    match = next((c for c in entries if c["name"].lower() == target), None)
    if match is None:
        close = [c["name"] for c in command_matches(target, limit=5)]
        hint = f" Did you mean: {', '.join(close)}?" if close else ""
        return ("error", f"[red]Unknown command '{target}'.[/]{hint}")
    lines2 = [f"[bold cyan]{match['name']}[/]  [dim][{match.get('category','')}][/]", f"  {match.get('help','(no help)')}", ""]
    params = match.get("params", []) or []
    if not params:
        lines2.append("  [dim](no arguments)[/]")
    else:
        lines2.append("  [bold]Arguments:[/]")
        for p in params:
            lines2.append(f"    [cyan]{p['name']}[/]  [dim]{_param_hint(p)}[/]")
        pos = [p["name"] for p in params]
        lines2.append("")
        lines2.append(f"  [dim]Example: {match['name']} " + " ".join(f"{n}=…" for n in pos[:3]) + "[/]")
    return ("info", "\n".join(lines2))


def _render_result(cmd: str, res: Any) -> Tuple[str, str]:
    if isinstance(res, dict) and res.get("status") == "success":
        result = res.get("result", res)
        # output-bus echo commands return the entry dict — show message
        if isinstance(result, dict) and "message" in result and "id" in result:
            return ("success", f"[green]ok[/] [dim]{cmd}[/] — {result['message']}")
        pretty = _pretty(result)
        return ("success", f"[green]ok[/] [dim]{cmd}[/]\n{pretty}")
    if isinstance(res, dict) and res.get("status") == "error":
        msg = res.get("message", "unknown error")
        expected = res.get("expected_params")
        extra = ""
        if expected:
            names = ", ".join(p.get("name", "?") for p in expected)
            extra = f"\n[dim]Expected params: {names} — try 'describe {cmd}'[/]"
        return ("error", f"[red]error[/] [dim]{cmd}[/] — {msg}{extra}")
    return ("success", f"[green]ok[/] [dim]{cmd}[/]\n{_pretty(res)}")


def _pretty(value: Any) -> str:
    if value is None:
        return "[dim](no result)[/]"
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, indent=2, default=str)[:4000]
    except Exception:
        return str(value)[:4000]


# ---------------------------------------------------------------------------
# Textual UI
# ---------------------------------------------------------------------------

_CSS = """
Screen { layout: vertical; }
#topbar { height: 3; border-bottom: solid $primary; padding: 0 1; }
#title { color: $text; }
#hint { color: $text-muted; }
#log { height: 1fr; border: none; padding: 0 1; }
#suggest { height: auto; max-height: 8; border-top: solid $primary; display: none; }
#suggest.visible { display: block; }
#prompt { border-top: solid $primary; }
"""

_PromptPlaceholder = "Type a command…  (Tab completes · Enter runs · 'help' for help)"


def _load_textual():
    try:
        from textual.app import App, ComposeResult  # noqa
        from textual.containers import Vertical  # noqa
        from textual.widgets import Header, Input, Label, OptionList, RichLog  # noqa
        from textual.widgets._option_list import Option  # noqa
        return True
    except Exception:
        return False


class DashboardV5App:
    """Factory holder — real App class is built lazily so module import
    never requires Textual (tests import parser helpers freely)."""

    @staticmethod
    def create():
        from textual.app import App, ComposeResult
        from textual.widgets import Input, Label, OptionList, RichLog
        from textual.widgets._option_list import Option

        class _App(App):
            TITLE = "MTT Dashboard V5 — Command Prompt"
            CSS = _CSS
            BINDINGS = [
                ("ctrl+c", "cancel_or_quit", "Cancel / Quit"),
                ("ctrl+l", "clear_screen", "Clear"),
                ("ctrl+r", "refresh_cmds", "Refresh"),
            ]

            def __init__(self):
                super().__init__()
                self._suggestions: List[Suggestion] = []
                self._history: List[str] = []
                self._hist_idx: int = 0
                self._cmd_count: int = 0
                self._last_output_id: int = 0
                self._unsub = None

            def compose(self) -> ComposeResult:
                yield Label("", id="topbar")
                yield RichLog(id="log", highlight=True, markup=True, wrap=True)
                yield OptionList(id="suggest")
                yield Input(placeholder=_PromptPlaceholder, id="prompt")

            def on_mount(self) -> None:
                try:
                    from core.command_registry import list_commands as _list
                    self._cmd_count = len(_list())
                except Exception:
                    self._cmd_count = 0
                self._render_topbar()
                log = self.query_one("#log", RichLog)
                log.write("[bold]MTT Dashboard V5[/] — command prompt over the command registry.")
                log.write(f"[dim]{self._cmd_count} commands loaded · Tab completes · 'help' for help · 'commands' to list[/]")
                try:
                    from core.output import get_output as _get
                    res = _get(since_id=0, limit=5)
                    msgs = res.get("messages", []) if isinstance(res, dict) else []
                    if msgs:
                        self._last_output_id = max(m.get("id", 0) for m in msgs)
                except Exception:
                    pass
                # Live feed: push bus messages into the log via thread-safe call
                try:
                    from core.output import subscribe as _sub
                    def _sink(entry):
                        try:
                            self.call_from_thread(self._on_bus_message, entry)
                        except Exception:
                            pass
                    self._unsub = _sub(_sink)
                except Exception:
                    self._unsub = None
                self.set_interval(2.0, self._poll_bus)
                self.query_one("#prompt", Input).focus()

            def on_unmount(self) -> None:
                try:
                    if self._unsub is not None:
                        self._unsub()
                except Exception:
                    pass

            # -- top bar -------------------------------------------------
            def _render_topbar(self) -> None:
                try:
                    bar = self.query_one("#topbar", Label)
                    bar.update(f"[bold]MTT V5[/]  [dim]│ {self._cmd_count} cmds │ Tab: complete │ ↑↓: navigate │ Enter: run │ help · commands · describe <cmd> · exit[/]")
                except Exception:
                    pass

            # -- live output bus -----------------------------------------
            def _on_bus_message(self, entry: Dict[str, Any]) -> None:
                try:
                    self._last_output_id = max(self._last_output_id, int(entry.get("id", 0)))
                    if entry.get("source") == "dashboard_v5":
                        return  # our own echoes already print results
                    self.query_one("#log", RichLog).write(
                        f"[dim]\\[{entry.get('source', '?')}]\\[/] {entry.get('message', '')}"
                    )
                except Exception:
                    pass

            def _poll_bus(self) -> None:
                try:
                    from core.output import get_output as _get
                    res = _get(since_id=self._last_output_id, limit=20)
                    if not isinstance(res, dict) or res.get("status") != "success":
                        return
                    for m in res.get("messages", []):
                        self._on_bus_message(m)
                except Exception:
                    pass

            # -- suggestions ----------------------------------------------
            def on_input_changed(self, event: Input.Changed) -> None:
                if event.input.id != "prompt":
                    return
                self._refresh_suggestions(event.value)

            def _refresh_suggestions(self, text: str) -> None:
                try:
                    opt = self.query_one("#suggest", OptionList)
                except Exception:
                    return
                self._suggestions = get_suggestions(text)
                opt.clear_options()
                if not self._suggestions or not text.strip():
                    opt.remove_class("visible")
                    opt.display = False
                    return
                for i, s in enumerate(self._suggestions):
                    opt.add_option(Option(s.display, id=f"sug-{i}"))
                opt.display = True
                opt.add_class("visible")
                try:
                    opt.highlighted = 0
                except Exception:
                    try:
                        opt.action_first()
                    except Exception:
                        pass

            def _current_highlight(self) -> int:
                try:
                    opt = self.query_one("#suggest", OptionList)
                    h = opt.highlighted
                    return int(h) if h is not None else 0
                except Exception:
                    return 0

            def _apply_completion(self, idx: int) -> bool:
                if not self._suggestions:
                    return False
                idx = max(0, min(idx, len(self._suggestions) - 1))
                done = self._suggestions[idx].completion
                if not done:
                    return False
                prompt = self.query_one("#prompt", Input)
                prompt.value = done
                prompt.cursor_position = len(done)
                return True

            def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
                try:
                    idx = int(str(event.option.id).split("-")[-1])
                except Exception:
                    idx = self._current_highlight()
                if self._apply_completion(idx):
                    self.query_one("#prompt", Input).focus()

            # -- keys -------------------------------------------------------
            def _dropdown_visible(self) -> bool:
                return bool(self._suggestions)

            def _is_exact_command(self, text: str) -> bool:
                tok = (text or "").strip().lstrip("/>").lower()
                if not tok or " " in tok:
                    return False
                try:
                    names = {c.get("name", "").lower() for c in all_command_entries()}
                    return tok in names
                except Exception:
                    return False

            def _move_highlight(self, delta: int) -> None:
                try:
                    opt = self.query_one("#suggest", OptionList)
                    if delta < 0:
                        opt.action_cursor_up()
                    else:
                        opt.action_cursor_down()
                except Exception:
                    pass

            async def on_key(self, event) -> None:
                try:
                    focused = self.focused
                    prompt = self.query_one("#prompt", Input)
                except Exception:
                    return
                if focused is not prompt:
                    return
                key = event.key
                if key == "tab":
                    event.prevent_default()
                    event.stop()
                    self._apply_completion(self._current_highlight())
                elif key == "up":
                    if self._dropdown_visible():
                        # focus stays in Input, so drive the list ourselves
                        event.prevent_default()
                        event.stop()
                        self._move_highlight(-1)
                        return
                    event.prevent_default()
                    event.stop()
                    self._history_step(-1)
                elif key == "down":
                    if self._dropdown_visible():
                        event.prevent_default()
                        event.stop()
                        self._move_highlight(+1)
                        return
                    event.prevent_default()
                    event.stop()
                    self._history_step(+1)
                elif key == "enter":
                    text = (prompt.value or "").strip()
                    if (self._dropdown_visible() and text and " " not in text
                            and not self._is_exact_command(text)):
                        # partial command word + open dropdown: complete the
                        # highlighted row instead of running. Multi-token
                        # lines always fall through to run.
                        event.prevent_default()
                        event.stop()
                        self._apply_completion(self._current_highlight())
                        return
                    # otherwise fall through to the Submitted handler (run it)
                elif key == "escape":
                    try:
                        opt = self.query_one("#suggest", OptionList)
                        opt.clear_options()
                        opt.remove_class("visible")
                        opt.display = False
                    except Exception:
                        pass
                    self._suggestions = []

            def _history_step(self, delta: int) -> None:
                if not self._history:
                    return
                try:
                    prompt = self.query_one("#prompt", Input)
                except Exception:
                    return
                self._hist_idx = max(0, min(len(self._history) - 1, self._hist_idx + delta))
                prompt.value = self._history[self._hist_idx]
                prompt.cursor_position = len(prompt.value)

            # -- submit ------------------------------------------------------
            def on_input_submitted(self, event: Input.Submitted) -> None:
                if event.input.id != "prompt":
                    return
                line = event.value.strip()
                prompt = self.query_one("#prompt", Input)
                log = self.query_one("#log", RichLog)
                if not line:
                    return
                # history (in-memory)
                if not self._history or self._history[-1] != line:
                    self._history.append(line)
                self._hist_idx = len(self._history)
                if len(self._history) > 200:
                    self._history = self._history[-200:]
                    self._hist_idx = len(self._history)

                log.write(f"[bold cyan]>[/] {line}")
                status, rendered = execute_line(line)
                if status == "exit":
                    self.exit()
                    return
                if status == "clear":
                    log.clear()
                    return
                if status == "history":
                    if not self._history:
                        log.write("[dim](empty history)[/]")
                    else:
                        for i, h in enumerate(self._history[-30:], 1):
                            log.write(f"[dim]{i:>3}[/]  {h}")
                    prompt.value = ""
                    self._suggestions = []
                    self._hide_suggest()
                    return
                if rendered:
                    log.write(rendered)
                try:
                    from core.output import emit as _emit
                    _emit(f"> {line}", level="debug", channel="log", source="dashboard_v5")
                except Exception:
                    pass
                prompt.value = ""
                self._suggestions = []
                self._hide_suggest()
                prompt.focus()

            def _hide_suggest(self) -> None:
                try:
                    opt = self.query_one("#suggest", OptionList)
                    opt.clear_options()
                    opt.remove_class("visible")
                    opt.display = False
                except Exception:
                    pass

            # -- actions ------------------------------------------------------
            def action_cancel_or_quit(self) -> None:
                try:
                    prompt = self.query_one("#prompt", Input)
                    if prompt.value:
                        prompt.value = ""
                        self._suggestions = []
                        self._hide_suggest()
                        return
                except Exception:
                    pass
                self.exit()

            def action_clear_screen(self) -> None:
                try:
                    self.query_one("#log", RichLog).clear()
                except Exception:
                    pass

            def action_refresh_cmds(self) -> None:
                try:
                    from core.command_registry import list_commands as _list
                    cmds = _list(refresh=True)
                    self._cmd_count = len(cmds)
                    self._render_topbar()
                    self.query_one("#log", RichLog).write(f"[dim]Refreshed — {self._cmd_count} commands.[/]")
                except Exception as e:
                    try:
                        self.query_one("#log", RichLog).write(f"[red]Refresh failed: {e}[/]")
                    except Exception:
                        pass

        return _App


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def run() -> None:
    """Launch Dashboard V5 (Textual). Exits cleanly if Textual is missing."""
    if not _load_textual():
        print(
            "Error: Textual is not installed.\n"
            "Install with: pip install textual   or   pip install -e '.[dashboard_v5]'",
            file=sys.stderr,
        )
        sys.exit(1)
    app_cls = DashboardV5App.create()
    app_cls().run()


def _parse_args(argv: Optional[List[str]] = None):
    p = argparse.ArgumentParser(description="MTT Dashboard V5 — Textual command prompt over the command registry")
    p.add_argument("--exec", dest="exec_line", default=None, help="Execute one line non-interactively and print the result (for tests/scripts)")
    return p.parse_args(argv)


if __name__ == "__main__":
    _args = _parse_args()
    if _args.exec_line:
        status, rendered = execute_line(_args.exec_line)
        # strip rich markup for --exec readability
        import re as _re
        plain = _re.sub(r"\[(?:/?[a-z_]+[^\]]*)\]", "", rendered or "")
        print(plain.strip() or status)
        sys.exit(0 if status in ("success", "info", "empty", "clear", "history") else 1)
    run()


__all__ = [
    "DashboardV5App",
    "ParsedLine",
    "Suggestion",
    "BUILTINS",
    "all_command_entries",
    "arg_suggestions",
    "arg_value_suggestions",
    "coerce_value",
    "command_matches",
    "execute_line",
    "get_suggestions",
    "parse_command_line",
    "positional_value_suggestions",
    "provider_values",
    "run",
    "split_line_for_completion",
    "value_provider",
]
