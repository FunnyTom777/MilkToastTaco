"""MTT Dashboard V5 — Command Prompt.

Interactive REPL over ``core.command_registry`` with fancy
prompt_toolkit completions + automatic discovery of all MTT commands.

Usage:
    python core/renderer/dashboard_v5/systems/command_prompt.py
    # or from V5 menu -> Other

Syntax:
    <command> [pos_arg ...] [key=value ...]
    /list [player|dev|system|debug]   list commands (auto-discovered)
    /help [command]                   show help / params
    /refresh                          force filesystem rescan for new @command files
    /quit | /exit | Ctrl-D            leave

Examples:
    economy.balance player_id=1
    inventory.add 1 5 2
    inventory.add player_id=1 item_id=5 quantity=2
    player.move player_id=1 pos=[10,0,5]
"""

from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure project root on sys.path (file is core/renderer/dashboard_v5/systems/...)
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.table import Table

from core.command_registry import execute, get_command, list_commands

console = Console()

BUILTINS = ["/list", "/help", "/refresh", "/clear", "/quit", "/exit"]


def _coerce_value(raw: str, annotation: str | None = None) -> Any:
    """Smart-coerce a CLI token to int/float/bool/None/list/dict/str."""
    s = raw.strip()
    # Explicit annotation casting first (registry gives us the type name)
    if annotation in ("int",):
        try:
            return int(s)
        except ValueError:
            pass
    if annotation in ("float",):
        try:
            return float(s)
        except ValueError:
            pass
    if annotation in ("bool", "boolean"):
        if s.lower() in ("true", "1", "yes", "y", "on"):
            return True
        if s.lower() in ("false", "0", "no", "n", "off"):
            return False
    # JSON-ish (handles numbers, bools, null, lists, dicts, quoted strings)
    try:
        return json.loads(s)
    except Exception:
        pass
    # Bare bools / null outside JSON quirks
    if s.lower() in ("true", "false"):
        return s.lower() == "true"
    if s.lower() in ("null", "none", "~"):
        return None
    return s


def parse_line(line: str) -> Tuple[str, list, dict]:
    """Parse 'cmd pos1 key=value ...' -> (cmd, args, kwargs)."""
    try:
        tokens = shlex.split(line.strip())
    except ValueError as e:
        raise ValueError(f"Could not parse line: {e}")
    if not tokens:
        raise ValueError("Empty line")
    name = tokens[0].lstrip("/")  # allow /help style for builtins too
    # Map 'help X' without slash to builtin
    spec = get_command(name)
    annotations: Dict[str, str | None] = {}
    if spec is not None:
        for p in spec.params:
            annotations[p["name"]] = p.get("annotation")
    args: list = []
    kwargs: dict = {}
    for tok in tokens[1:]:
        if "=" in tok and not tok.startswith("="):
            key, _, val = tok.partition("=")
            kwargs[key.strip()] = _coerce_value(val.strip(), annotations.get(key.strip()))
        else:
            args.append(_coerce_value(tok))
    return name, args, kwargs


class MTTCompleter(Completer):
    """Fuzzy completer fed by the live command registry.

    - First word: command names (+ builtins), with help text as meta.
    - Later words: param names as ``key=`` for the typed command.
    Cache refreshes on every /refresh and lazily when new commands appear.
    """

    def __init__(self):
        self._cache: List[Dict[str, Any]] = []
        self.refresh()

    def refresh(self) -> None:
        try:
            self._cache = list_commands()
        except Exception:
            self._cache = []

    def _command_matches(self, word: str) -> List[Dict[str, Any]]:
        w = word.lower()
        if not w:
            return sorted(self._cache, key=lambda c: c["name"])
        starts = [c for c in self._cache if c["name"].lower().startswith(w)]
        contains = [c for c in self._cache if w in c["name"].lower() and c not in starts]
        return starts + contains

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        try:
            tokens = shlex.split(text)
        except ValueError:
            tokens = text.split()
        # Are we completing the first word?
        if not text.strip() or (len(tokens) <= 1 and not text.endswith((" ", "\t"))):
            word = tokens[0] if tokens else ""
            # builtins
            for b in BUILTINS:
                if b.startswith(word or "/"):
                    yield Completion(b, start_position=-len(word), display_meta="builtin")
            for cmd in self._command_matches(word.lstrip("/")):
                meta = f"{cmd.get('help','')} [{cmd.get('category','')}]"
                yield Completion(
                    cmd["name"],
                    start_position=-len(word),
                    display=cmd["name"],
                    display_meta=meta,
                )
        else:
            # Completing args: suggest param names for the known command
            cmd_name = tokens[0].lstrip("/") if tokens else ""
            spec = get_command(cmd_name)
            if spec is None:
                return
            # current fragment after last space
            frag = text.split()[-1] if text.split() else ""
            if "=" in frag:
                return  # completing a value — leave to history/autosuggest
            used = {t.split("=")[0] for t in tokens[1:] if "=" in t}
            for p in spec.params:
                pname = p["name"]
                if pname in used:
                    continue
                if pname.startswith(frag):
                    if p.get("required"):
                        suffix = "(required)"
                    elif p.get("has_default"):
                        suffix = f"= {p.get('default')!r}"
                    else:
                        suffix = ""
                    meta = f"{p.get('annotation', '')} {suffix}".strip()
                    yield Completion(f"{pname}=", start_position=-len(frag), display_meta=meta)


def _show_commands(category: str | None = None) -> None:
    cmds = list_commands(category)
    if category and not cmds:
        console.print(f"[yellow]No commands in category '{category}'.[/yellow]")
        return
    table = Table(title=f"Available Commands ({len(cmds)})", show_lines=False)
    table.add_column("Command", style="cyan", no_wrap=True)
    table.add_column("Help", style="white")
    table.add_column("Category", style="magenta")
    table.add_column("Params", style="green")
    for c in cmds:
        params = ", ".join(
            p["name"] if p.get("required") else f"[{p['name']}]" for p in c.get("params", [])
        )
        table.add_row(c["name"], c.get("help", ""), c.get("category", ""), params)
    console.print(table)


def _show_help(name: str | None = None) -> None:
    if not name:
        console.print(
            "[bold]MTT Command Prompt[/bold]\n"
            "Type a command with live suggestions (Tab to complete).\n"
            "Syntax: [cyan]<command> [pos ...] [key=value ...][/cyan]\n"
            "Builtins: [green]/list [cat]  /help [cmd]  /refresh  /clear  /quit[/green]\n"
            "Examples: [dim]economy.balance player_id=1 | inventory.add 1 5 2[/dim]"
        )
        return
    spec = get_command(name.strip().lower())
    if spec is None:
        console.print(f"[red]Unknown command '{name}'. Try /list[/red]")
        return
    console.print(f"[bold cyan]{spec.name}[/bold cyan] [{spec.category}] — {spec.help_text}")
    if not spec.params:
        console.print("[dim](no params)[/dim]")
        return
    table = Table(show_header=True)
    table.add_column("Param")
    table.add_column("Type")
    table.add_column("Required")
    table.add_column("Default")
    for p in spec.params:
        table.add_row(
            p["name"],
            str(p.get("annotation", "")),
            "yes" if p.get("required") else "no",
            repr(p.get("default")) if p.get("has_default") else "—",
        )
    console.print(table)


def _handle_line(line: str, completer: "MTTCompleter") -> bool:
    """Handle one input line. Returns False when the prompt should quit."""
    line = line.strip()
    if not line:
        return True
    low = line.lower()
    if low in ("/quit", "/exit", "quit", "exit"):
        console.print("[dim]Bye![/dim]")
        return False
    if low in ("/clear", "clear"):
        console.clear()
        return True
    if low in ("/refresh", "refresh"):
        refreshed = list_commands(refresh=True)
        completer.refresh()
        console.print(f"[green]Refreshed — {len(refreshed)} commands.[/green]")
        return True
    if low == "/list" or low.startswith("/list ") or low == "list":
        parts = line.split()
        cat = parts[1] if len(parts) > 1 else None
        _show_commands(cat)
        return True
    if low == "/help" or low == "help" or low.startswith(("/help ", "help ")):
        parts = line.split(None, 1)
        _show_help(parts[1] if len(parts) > 1 else None)
        return True
    # Regular command dispatch
    try:
        name, args, kwargs = parse_line(line)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        return True
    res = execute(name, *args, **kwargs)
    if res.get("status") == "success":
        result = res.get("result", res)
        # Unwrap the envelope when the payload is trivial
        if set(res.keys()) == {"status", "result", "command"}:
            console.print(f"[green]OK {name}[/green] -> {result!r}")
        else:
            console.print(f"[green]OK {name}[/green]")
            console.print_json(json.dumps(res, default=str))
    else:
        console.print(f"[red]ERR {name}: {res.get('message')}[/red]")
        if "expected_params" in res:
            console.print(f"[dim]Expected: {res['expected_params']}[/dim]")
        # Nudge: refresh completer in case the command is brand new
        completer.refresh()
    return True


def _run_simple_loop(completer: "MTTCompleter", reason: str = "") -> None:
    """Plain-input() fallback when prompt_toolkit has no usable console.

    Happens with ``NoConsoleScreenBufferError`` on Windows when stdout is
    not a real console (IDE runner, redirected output, etc.). Same commands,
    just no Tab-completion / suggestions.
    """
    if reason:
        console.print(f"[yellow]{reason}[/yellow]")
    console.print("[dim]Running in simple mode (no Tab-completion). Type /quit to leave.[/dim]")
    while True:
        try:
            line = input("MTT> ")
        except (KeyboardInterrupt,):
            continue
        except EOFError:
            console.print("[dim]Bye![/dim]")
            break
        if not _handle_line(line, completer):
            break


def run_prompt(force_simple: bool = False) -> None:
    completer = MTTCompleter()
    cmds = list_commands()
    console.print(
        f"[green bold]MTT Command Prompt[/green bold] [dim]({len(cmds)} commands auto-discovered — Tab for suggestions)[/dim]"
    )
    console.print("[dim]Type /help, /list, /refresh, or /quit. Ctrl-D also quits.[/dim]")

    if force_simple or "--simple" in sys.argv:
        _run_simple_loop(completer)
        return

    try:
        style = Style.from_dict({"prompt": "ansigreen bold"})
        history_path = _PROJECT_ROOT / ".mtt_prompt_history"
        session: PromptSession = PromptSession(
            completer=completer,
            history=FileHistory(str(history_path)),
            auto_suggest=AutoSuggestFromHistory(),
            complete_while_typing=True,
        )
    except Exception as e:
        # No usable console (e.g. NoConsoleScreenBufferError) — fall back
        # to plain input() instead of crashing so the V5 "Other" button
        # always lands somewhere usable.
        _run_simple_loop(completer, reason=f"Fancy prompt unavailable ({e});")
        return

    while True:
        try:
            line = session.prompt("MTT> ", style=style)
        except (KeyboardInterrupt,):
            continue
        except EOFError:
            console.print("[dim]Bye![/dim]")
            break
        if not _handle_line(line, completer):
            break


if __name__ == "__main__":
    run_prompt()
