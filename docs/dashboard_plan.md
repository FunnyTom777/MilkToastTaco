# Milk Toast Taco — Dev Dashboard V1

**Status:** Planning
**Goal:** A runnable, terminal-based dev console for manipulating MTT's systems independently of a full game — a debug harness that lets systems (mud, vehicles, economy, etc.) be built and tested in isolation via `/` commands, long before there's anything "playable."

---

## 1. Core Philosophy

- **Not a game, a harness.** V1 has no map, no rendering, no win condition — just a REPL you can poke systems with.
- **Systems-first.** Every system (mud, vehicle damage, economy...) should be usable and testable through the console the moment it exists in code, with zero UI work required to wire it in.
- **One backend, many front doors.** The command registry itself should not know or care whether it's being driven by a terminal, a script, or (down the track) a Flask web dashboard. Keep execution decoupled from I/O so V2 doesn't mean a rewrite.

---

## 2. Architecture

### 2.1 Command Registry

Decorator-based, not config-file-based. Commands are behavior, not data — so they live in Python, not XML/YAML. (XML/YAML stays reserved for actual game *data*: prices, vehicle stats, mud types, etc. — consistent with the rest of MTT's modding approach.)

```python
COMMANDS = {}

def command(name, help_text=""):
    def wrapper(fn):
        COMMANDS[name] = {"fn": fn, "help": help_text}
        return fn
    return wrapper
```

### 2.2 Namespacing

Commands are namespaced by system to avoid a flat command soup as more systems get added:

```
/mud depth 0.4
/mud type wet_clay
/vehicle spawn f150
/vehicle damage engine 30
/econ price wheat
```

### 2.3 World State

A single shared `State` object that all systems read/write against. This is the same object shape the eventual "game" would use — building it now means the console isn't throwaway scaffolding, it's the real spine.

### 2.4 Output Layer

Use `rich` for terminal output — Markdown rendering, tables, color, progress bars — without needing a web server. Output formatting (tables for stats, colored diffs for state changes, etc.) matters a lot here since there's no visual game to fall back on; the console output *is* the feedback loop.

---

## 3. V1 Scope (what actually ships)

- [ ] REPL loop (`/command args...` parsing, `help`, `exit`)
- [ ] Command registry + decorator system
- [ ] Shared `State` object (minimal — just enough to hold whatever systems exist)
- [ ] `rich`-based output (tables + basic Markdown rendering)
- [ ] Command history / basic error handling (bad command, bad args → helpful message, not a crash)
- [ ] A handful of real commands wired to whatever system is built first (mud physics is the likely candidate)

**Explicitly out of scope for V1:** persistence/save files, multiplayer, any visual/graphical rendering, Flask/web dashboard, scripting/macro support.

---

## 4. Phase 2 (later, not now)

- **Web dashboard (Flask):** a browser-based skin over the *same* command registry — routes call `COMMANDS[name]["fn"]()` just like the REPL does. Only worth building once the terminal genuinely feels limiting.
- **Live state view:** auto-updating dashboard (likely needs websockets) showing current world state without re-running commands.
- **Command autocomplete / history file.**
- **Scripting:** run a sequence of commands from a file, for repeatable test scenarios.
