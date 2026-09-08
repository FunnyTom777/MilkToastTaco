#!/usr/bin/env python3
"""
Milk Toast Taco Launcher
A small Tkinter launcher for the four MTT dashboard versions.

Run:
    python launcher.py
    python -m Launcher.launcher
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import webbrowser
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from tkinter import messagebox, ttk
import tkinter as tk
import urllib.error
import urllib.request

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# launcher.py lives in MilkToastTaco/Launcher/ -> project root is parent
PROJECT_ROOT = Path(__file__).resolve().parents[1]
# For backwards compat if someone moved file, ensure core is importable
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

XMB_SETTINGS_PATH = PROJECT_ROOT / "xmbsettings.xml"
LAUNCHER_CONFIG_PATH = Path(__file__).resolve().parent / "launcher_config.json"

# ---------------------------------------------------------------------------
# GitHub
# ---------------------------------------------------------------------------

GITHUB_REPO = "FunnyTom777/MilkToastTaco"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/commits"
GITHUB_HTML_URL = f"https://github.com/{GITHUB_REPO}"
GITHUB_COMMITS_HTML = f"{GITHUB_HTML_URL}/commits"

# ---------------------------------------------------------------------------
# Dashboard definitions
# ---------------------------------------------------------------------------

DASHBOARDS = {
    "V1": {
        "module": "core.renderer.dashboard.dashboard",
        "description": "Classic MTT dashboard",
    },
    "V2": {
        "module": "core.renderer.dashboard_v2.dashboard_v2",
        "description": "Game System Debugger / XMB dashboard",
    },
    "V3": {
        "module": "core.renderer.dashboard_v3.dashboard_v3",
        "description": "Console-style hub",
    },
    "V4": {
        "module": "core.renderer.dashboard_v4.dashboard_v4",
        "description": "Native desktop hub",
    },
}

# ---------------------------------------------------------------------------
# xmbsettings.xml helpers (standalone, no core import required)
# ---------------------------------------------------------------------------

def _load_xmb_settings_standalone(path: Path | None = None) -> dict:
    """Load xmbsettings.xml without importing core. Returns defaults on failure."""
    defaults = {"fullscreen": False, "theme": "default", "dev_mode": False}
    fp = Path(path) if path else XMB_SETTINGS_PATH
    if not fp.exists():
        return dict(defaults)
    try:
        tree = ET.parse(fp)
        root = tree.getroot()
        fs_el = root.find("fullscreen")
        if fs_el is not None and fs_el.text is not None:
            defaults["fullscreen"] = fs_el.text.strip().lower() in ("true", "1", "yes", "on")
        theme_el = root.find("theme")
        if theme_el is not None and theme_el.text is not None:
            t = theme_el.text.strip()
            if t:
                defaults["theme"] = t
        dev_el = root.find("dev_mode")
        if dev_el is not None and dev_el.text is not None:
            defaults["dev_mode"] = dev_el.text.strip().lower() in ("true", "1", "yes", "on")
    except Exception:
        pass
    return defaults


def _save_xmb_settings_standalone(fullscreen: bool, path: Path | None = None) -> None:
    """Save fullscreen to xmbsettings.xml, preserving theme/dev_mode."""
    fp = Path(path) if path else XMB_SETTINGS_PATH
    # Load existing to preserve theme/dev_mode
    current = _load_xmb_settings_standalone(fp)
    current["fullscreen"] = bool(fullscreen)

    # Try to use core helper first (validates themes etc.)
    try:
        from core.renderer.main_menu.xmb_settings import save_settings as _core_save
        _core_save(current, path=fp)
        return
    except Exception:
        pass

    # Fallback: write ourselves
    root = ET.Element("xmb_settings")
    fs_el = ET.SubElement(root, "fullscreen")
    fs_el.text = "true" if current["fullscreen"] else "false"
    theme_el = ET.SubElement(root, "theme")
    theme_el.text = str(current.get("theme", "default"))
    dev_el = ET.SubElement(root, "dev_mode")
    dev_el.text = "true" if current.get("dev_mode", False) else "false"
    ET.indent(root, space="  ")
    tree = ET.ElementTree(root)
    tmp = fp.with_suffix(".xml.tmp")
    tree.write(tmp, encoding="utf-8", xml_declaration=True)
    os.replace(tmp, fp)


def load_fullscreen() -> bool:
    """Public helper: load fullscreen bool."""
    # Prefer core if available
    try:
        from core.renderer.main_menu.xmb_settings import load_settings
        return bool(load_settings().get("fullscreen", False))
    except Exception:
        return bool(_load_xmb_settings_standalone().get("fullscreen", False))


def save_fullscreen(enabled: bool) -> None:
    _save_xmb_settings_standalone(bool(enabled))


# ---------------------------------------------------------------------------
# Launcher config helpers (selected dashboard persistence)
# ---------------------------------------------------------------------------

def _load_launcher_config() -> dict:
    try:
        if LAUNCHER_CONFIG_PATH.exists():
            with open(LAUNCHER_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    return {}


def _save_launcher_config(data: dict) -> None:
    try:
        LAUNCHER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LAUNCHER_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# GitHub fetch helper
# ---------------------------------------------------------------------------

def fetch_github_commits(per_page: int = 20, timeout: int = 12) -> list[dict]:
    """Fetch recent commits from GitHub API. Raises on failure."""
    url = f"{GITHUB_API_URL}?per_page={per_page}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "MTT-Launcher",
            "Accept": "application/vnd.github.v3+json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, list):
            raise ValueError("Unexpected GitHub response")
        return data


def _format_github_date(iso_str: str) -> str:
    """2024-03-15T14:22:10Z -> '15 Mar 2024, 14:22 UTC'  (fallback to raw)."""
    if not iso_str:
        return "—"
    try:
        # GitHub returns ISO8601 like 2024-03-15T14:22:10Z
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        # Use local-ish display but keep UTC label
        return dt.strftime("%d %b %Y, %H:%M UTC")
    except Exception:
        return iso_str[:16].replace("T", " ")


# ---------------------------------------------------------------------------
# Settings Window
# ---------------------------------------------------------------------------

class SettingsWindow(tk.Toplevel):
    def __init__(self, parent: MTTLauncher) -> None:  # type: ignore[name-defined]
        super().__init__(parent)
        self.parent = parent
        self.title("MTT Settings")
        self.geometry("420x320")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Center on parent
        try:
            px, py = parent.winfo_rootx(), parent.winfo_rooty()
            pw, ph = parent.winfo_width(), parent.winfo_height()
            x = px + (pw - 420) // 2
            y = py + (ph - 320) // 2
            self.geometry(f"420x320+{max(0,x)}+{max(0,y)}")
        except Exception:
            pass

        self.fullscreen_var = tk.BooleanVar(value=load_fullscreen())
        # Keep original to detect changes
        self._original = bool(self.fullscreen_var.get())

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.bind("<Escape>", lambda e: self._on_cancel())

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=16)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Settings", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Label(outer, text="Milk Toast Taco • Launcher preferences", font=("Segoe UI", 8), foreground="#666").pack(anchor="w", pady=(2, 12))

        # Fullscreen card -------------------------------------------------
        card = tk.Frame(outer, bg="white", highlightthickness=1, highlightbackground="#d9d9d9")
        card.pack(fill="x", pady=(0, 8))

        inner = tk.Frame(card, bg="white")
        inner.pack(fill="x", padx=12, pady=12)

        cb = ttk.Checkbutton(
            inner,
            text="Launch MTT in fullscreen",
            variable=self.fullscreen_var,
            command=self._on_toggle,
        )
        cb.pack(anchor="w")

        ttk.Label(inner, text="When enabled, dashboards will start in fullscreen mode.\nSaved to xmbsettings.xml (shared with all dashboards).", font=("Segoe UI", 8), foreground="#666", justify="left").pack(anchor="w", pady=(6, 0))

        # Show current state hint
        self.hint_var = tk.StringVar(value=self._hint_text())
        ttk.Label(inner, textvariable=self.hint_var, font=("Segoe UI", 8, "italic"), foreground="#444").pack(anchor="w", pady=(6, 0))

        # Info box --------------------------------------------------------
        info = tk.Frame(outer, bg="#f5f5f5", highlightthickness=1, highlightbackground="#e0e0e0")
        info.pack(fill="x", pady=(6, 12))
        tk.Label(info, text=f"Config file:  {XMB_SETTINGS_PATH.name}  (project root)", bg="#f5f5f5", fg="#555", font=("Segoe UI", 8), anchor="w", justify="left").pack(fill="x", padx=10, pady=8)

        # Buttons ---------------------------------------------------------
        btns = ttk.Frame(outer)
        btns.pack(fill="x", side="bottom", pady=(8, 0))

        self.status_var = tk.StringVar(value="")
        ttk.Label(btns, textvariable=self.status_var, font=("Segoe UI", 8), foreground="#1a7a1a").pack(side="left")

        ttk.Button(btns, text="Cancel", command=self._on_cancel).pack(side="right", padx=(8, 0))
        ttk.Button(btns, text="Save", style="Launch.TButton", command=self._on_save).pack(side="right")
        # Also allow Reset
        ttk.Button(btns, text="Open folder", command=self._open_config_folder).pack(side="right", padx=(0, 8))

    def _hint_text(self) -> str:
        return "Fullscreen: ON — dashboards will open fullscreen" if self.fullscreen_var.get() else "Fullscreen: OFF — dashboards will open windowed"

    def _on_toggle(self) -> None:
        self.hint_var.set(self._hint_text())
        # live preview status
        if self.fullscreen_var.get() != self._original:
            self.status_var.set("• Unsaved changes")
        else:
            self.status_var.set("")

    def _on_save(self) -> None:
        try:
            save_fullscreen(self.fullscreen_var.get())
            self.parent.status_var.set(f"Settings saved — fullscreen {'ON' if self.fullscreen_var.get() else 'OFF'}.")
            # Also update parent's fullscreen hint if any
            self.destroy()
            messagebox.showinfo("MTT Settings", f"Saved!\n\nLaunch MTT in fullscreen: {'ON' if self.fullscreen_var.get() else 'OFF'}\n\nNext launch will use this setting.", parent=self.parent)
        except Exception as exc:
            messagebox.showerror("MTT Settings", f"Could not save settings:\n{exc}", parent=self)

    def _on_cancel(self) -> None:
        self.grab_release()
        self.destroy()

    def _open_config_folder(self) -> None:
        try:
            folder = str(PROJECT_ROOT)
            if sys.platform == "win32":
                os.startfile(folder)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as exc:
            messagebox.showerror("Open folder", f"Could not open folder:\n{exc}", parent=self)


# ---------------------------------------------------------------------------
# Recent Updates Window
# ---------------------------------------------------------------------------

class UpdatesWindow(tk.Toplevel):
    def __init__(self, parent: MTTLauncher) -> None:  # type: ignore[name-defined]
        super().__init__(parent)
        self.parent = parent
        self.title("Recent Updates — Milk Toast Taco")
        self.geometry("620x560")
        self.minsize(520, 400)
        self.transient(parent)
        # Don't grab — allow interaction with launcher behind
        # self.grab_set()

        try:
            px, py = parent.winfo_rootx(), parent.winfo_rooty()
            pw, ph = parent.winfo_width(), parent.winfo_height()
            x = px + (pw - 620) // 2
            y = py + (ph - 560) // 2
            self.geometry(f"620x560+{max(0,x)}+{max(0,y)}")
        except Exception:
            pass

        self.per_page = 20
        self._commits: list[dict] = []
        self._loading = False

        self._build_ui()
        self._set_loading(True)
        self._fetch_async()

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<Escape>", lambda e: self.destroy())

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)

        # Header
        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 8))

        left = ttk.Frame(header)
        left.pack(side="left", fill="x", expand=True)
        ttk.Label(left, text="Recent Updates", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Label(left, text=f"From GitHub: {GITHUB_REPO}  •  live commits", font=("Segoe UI", 8), foreground="#666").pack(anchor="w", pady=(2, 0))
        self.subtitle_var = tk.StringVar(value="Fetching latest commits…")
        ttk.Label(left, textvariable=self.subtitle_var, font=("Segoe UI", 8, "italic"), foreground="#444").pack(anchor="w", pady=(2, 0))

        right = ttk.Frame(header)
        right.pack(side="right", anchor="n")
        ttk.Button(right, text="↻ Refresh", command=self._on_refresh, width=10).pack(pady=(2, 4))
        ttk.Button(right, text="Open GitHub ↗", command=self._open_github, width=13).pack()

        # Progress
        self.progress = ttk.Progressbar(outer, mode="indeterminate")
        # packed dynamically in _set_loading

        # Error / empty banner
        self.banner_var = tk.StringVar(value="")
        self.banner = ttk.Label(outer, textvariable=self.banner_var, font=("Segoe UI", 8), foreground="#a33", wraplength=580, justify="left")

        # Scrollable commits area -----------------------------------------
        container = ttk.Frame(outer)
        container.pack(fill="both", expand=True, pady=(6, 0))

        # Canvas + scrollbar for cards
        self.canvas = tk.Canvas(container, bg="#f7f7f7", highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.inner = tk.Frame(self.canvas, bg="#f7f7f7")
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        # Mouse wheel
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        self.canvas.bind_all("<Button-4>", self._on_mousewheel, add="+")
        self.canvas.bind_all("<Button-5>", self._on_mousewheel, add="+")

        # Footer
        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(8, 0))
        ttk.Label(footer, text="Tip: click a commit to view it on GitHub.", font=("Segoe UI", 8), foreground="#888").pack(side="left")
        ttk.Label(footer, text="MTT Launcher • GitHub API", font=("Segoe UI", 8), foreground="#888").pack(side="right")

        # Initial placeholder
        self._show_placeholder("Loading commits from GitHub…")

    def _on_mousewheel(self, event) -> None:
        try:
            if event.num == 4:
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.canvas.yview_scroll(1, "units")
            else:
                delta = int(-1 * (event.delta / 120))
                self.canvas.yview_scroll(delta, "units")
        except Exception:
            pass

    def _set_loading(self, loading: bool) -> None:
        self._loading = loading
        if loading:
            self.progress.pack(fill="x", pady=(0, 6))
            self.progress.start(10)
            self.subtitle_var.set("Fetching latest commits from GitHub…")
            self.banner_var.set("")
            if hasattr(self, "banner") and self.banner.winfo_ismapped():
                self.banner.pack_forget()
        else:
            self.progress.stop()
            self.progress.pack_forget()

    def _show_placeholder(self, text: str) -> None:
        for w in self.inner.winfo_children():
            w.destroy()
        lbl = tk.Label(self.inner, text=text, bg="#f7f7f7", fg="#888", font=("Segoe UI", 9), pady=20, wraplength=560, justify="center")
        lbl.pack(fill="x", padx=12, pady=12)

    def _on_refresh(self) -> None:
        if self._loading:
            return
        self._show_placeholder("Refreshing…")
        self._set_loading(True)
        self._fetch_async()

    def _open_github(self) -> None:
        webbrowser.open(GITHUB_HTML_URL)

    def _fetch_async(self) -> None:
        def worker():
            try:
                commits = fetch_github_commits(per_page=self.per_page)
                self.after(0, lambda: self._on_fetch_success(commits))
            except urllib.error.HTTPError as e:
                msg = f"GitHub API error {e.code}: {e.reason}"
                if e.code == 403:
                    msg += " (rate limited — try again later)"
                elif e.code == 404:
                    msg += " (repo not found)"
                self.after(0, lambda: self._on_fetch_error(msg))
            except urllib.error.URLError as e:
                self.after(0, lambda: self._on_fetch_error(f"Network error: {e.reason} — check your internet connection."))
            except Exception as e:
                self.after(0, lambda: self._on_fetch_error(str(e)))

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _on_fetch_success(self, commits: list[dict]) -> None:
        self._set_loading(False)
        self._commits = commits
        if not commits:
            self.subtitle_var.set("No commits found.")
            self._show_placeholder("No commits returned from GitHub.")
            return

        self.subtitle_var.set(f"Showing {len(commits)} most recent commits • {GITHUB_REPO}")
        self._render_commits(commits)

    def _on_fetch_error(self, msg: str) -> None:
        self._set_loading(False)
        self.subtitle_var.set("Could not load commits.")
        self.banner_var.set(msg)
        # show banner if hidden
        if not self.banner.winfo_ismapped():
            # insert above canvas container: need to repack trick — just pack it
            self.banner.pack(fill="x", pady=(0, 4), before=self.canvas.master)
        self._show_placeholder("Could not fetch commits.\n\n" + msg + "\n\nPress Refresh to retry or Open GitHub to view in browser.")

        # On error, fall back to recent local git log if available
        try:
            local = self._local_git_log_fallback()
            if local:
                self.banner_var.set(msg + "   — showing local git log as fallback.")
                self.subtitle_var.set(f"Offline — showing {len(local)} local commits")
                self._render_commits(local, is_local=True)
        except Exception:
            pass

    def _local_git_log_fallback(self) -> list[dict]:
        """Build pseudo GitHub commit dicts from local git log."""
        import subprocess as sp
        try:
            out = sp.check_output(
                ["git", "log", f"--max-count={self.per_page}", "--pretty=format:%H%x1f%s%x1f%b%x1f%an%x1f%aI%x1f%h", "--no-merges"],
                cwd=str(PROJECT_ROOT),
                text=True,
                timeout=5,
            )
        except Exception:
            return []
        commits = []
        for line in out.splitlines():
            parts = line.split("\x1f")
            if len(parts) < 5:
                continue
            sha, subject, body, author, date_iso, short = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5] if len(parts) > 5 else parts[0][:7]
            msg = subject + ("\n\n" + body if body.strip() else "")
            commits.append({
                "sha": sha,
                "html_url": f"{GITHUB_HTML_URL}/commit/{sha}",
                "commit": {
                    "message": msg,
                    "author": {"name": author, "date": date_iso},
                },
                "author": {"login": author},
            })
        return commits

    def _render_commits(self, commits: list[dict], is_local: bool = False) -> None:
        for w in self.inner.winfo_children():
            w.destroy()

        for idx, c in enumerate(commits):
            sha = c.get("sha", "")[:7]
            full_sha = c.get("sha", "")
            html_url = c.get("html_url", f"{GITHUB_HTML_URL}/commit/{full_sha}" if full_sha else GITHUB_HTML_URL)
            commit = c.get("commit", {}) or {}
            msg_full = commit.get("message", "") or ""
            # First line is title
            lines = msg_full.splitlines()
            title = lines[0].strip() if lines else "(no message)"
            body = "\n".join(l.strip() for l in lines[1:] if l.strip())
            if len(body) > 220:
                body = body[:220].rstrip() + "…"

            author_info = commit.get("author", {}) or {}
            author_name = author_info.get("name") or (c.get("author", {}) or {}).get("login", "unknown")
            date_raw = author_info.get("date", "") or commit.get("committer", {}).get("date", "")
            date_str = _format_github_date(date_raw)

            # Card frame
            card = tk.Frame(self.inner, bg="white", highlightthickness=1, highlightbackground="#e6e6e6", highlightcolor="#e6e6e6")
            card.pack(fill="x", padx=10, pady=5)
            # Make card clickable
            def _open(u=html_url):
                webbrowser.open(u)

            # Top row: SHA + date + author
            top = tk.Frame(card, bg="white")
            top.pack(fill="x", padx=10, pady=(8, 2))

            sha_lbl = tk.Label(top, text=sha, bg="white", fg="#0b57d0", font=("Consolas", 9, "bold"), cursor="hand2")
            sha_lbl.pack(side="left")
            sha_lbl.bind("<Button-1>", lambda e, u=html_url: webbrowser.open(u))

            tk.Label(top, text=f"  •  {author_name}  •  {date_str}", bg="white", fg="#666", font=("Segoe UI", 8)).pack(side="left")

            if idx == 0:
                tk.Label(top, text="latest", bg="#e8f0fe", fg="#1a56db", font=("Segoe UI", 7, "bold"), padx=6, pady=1).pack(side="right")

            # Title
            title_lbl = tk.Label(card, text=title, bg="white", fg="#1a1a1a", font=("Segoe UI", 9, "bold"), anchor="w", justify="left", wraplength=560)
            title_lbl.pack(fill="x", padx=10, pady=(2, 2))
            title_lbl.bind("<Button-1>", lambda e, u=html_url: webbrowser.open(u))
            card.bind("<Button-1>", lambda e, u=html_url: webbrowser.open(u))

            if body:
                body_lbl = tk.Label(card, text=body, bg="white", fg="#555", font=("Segoe UI", 8), anchor="w", justify="left", wraplength=560)
                body_lbl.pack(fill="x", padx=10, pady=(0, 4))

            # Bottom row: View link
            bottom = tk.Frame(card, bg="white")
            bottom.pack(fill="x", padx=10, pady=(0, 8))
            link = tk.Label(bottom, text="View on GitHub ↗", bg="white", fg="#0b57d0", font=("Segoe UI", 8, "underline"), cursor="hand2")
            link.pack(side="left")
            link.bind("<Button-1>", lambda e, u=html_url: webbrowser.open(u))
            # SHA full hint
            tk.Label(bottom, text=full_sha[:12] if full_sha else "", bg="white", fg="#999", font=("Consolas", 7)).pack(side="right")

            # Hover effect
            def _enter(e, c=card):
                c.configure(highlightbackground="#c9c9c9")
            def _leave(e, c=card):
                c.configure(highlightbackground="#e6e6e6")
            card.bind("<Enter>", _enter)
            card.bind("<Leave>", _leave)

        # Add bottom spacer
        tk.Label(self.inner, text="", bg="#f7f7f7", height=1).pack()

        # Update scrollregion
        self.inner.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.yview_moveto(0)


# ---------------------------------------------------------------------------
# Launcher
# ---------------------------------------------------------------------------

class MTTLauncher(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Milk Toast Taco")
        self.geometry("440x480")
        self.resizable(False, False)

        self.status_var = tk.StringVar(
            value="Ready to launch Milk Toast Taco."
        )

        # Load last selected dashboard from launcher config, else default V2
        cfg = _load_launcher_config()
        default_dash = cfg.get("selected_dashboard", "V2")
        if default_dash not in DASHBOARDS:
            default_dash = "V2"
        self.selected_dashboard = tk.StringVar(value=default_dash)

        self.dashboard_buttons: dict[str, tk.Button] = {}
        self._settings_win: tk.Toplevel | None = None
        self._updates_win: tk.Toplevel | None = None

        self._configure_style()
        self._build_ui()

    # ------------------------------------------------------------------
    # Styling
    # ------------------------------------------------------------------

    def _configure_style(self) -> None:
        style = ttk.Style(self)

        # Use the default native theme (light / white) — no forced dark theme.
        # Keep ttk defaults; only tweak fonts/padding.

        style.configure(
            "Title.TLabel",
            font=("Segoe UI", 16, "bold"),
        )

        style.configure(
            "Subtitle.TLabel",
            font=("Segoe UI", 9),
            foreground="#555555",
        )

        style.configure(
            "Launch.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(14, 6),
        )

        style.configure(
            "Bottom.TLabel",
            font=("Segoe UI", 8),
            foreground="#666666",
        )

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = ttk.Frame(
            self,
            padding=16,
        )

        root.pack(fill="both", expand=True)

        # Header --------------------------------------------------------

        header = ttk.Frame(root)

        header.pack(
            fill="x",
            pady=(0, 12),
        )

        ttk.Label(
            header,
            text="MILK TOAST TACO",
            style="Title.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            header,
            text="Community Edition  •  Game Launcher",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        # Dashboard selector -------------------------------------------

        dashboard_frame = ttk.Frame(root)

        dashboard_frame.pack(
            fill="both",
            expand=True,
        )

        ttk.Label(
            dashboard_frame,
            text="SELECT DASHBOARD",
            style="Subtitle.TLabel",
        ).pack(
            anchor="w",
            pady=(0, 6),
        )

        for name, info in DASHBOARDS.items():
            self._create_dashboard_card(
                dashboard_frame,
                name,
                info,
            )

        # Default selection
        self._select_dashboard(self.selected_dashboard.get())

        # Buttons -------------------------------------------------------

        actions = ttk.Frame(root)

        actions.pack(
            fill="x",
            pady=(12, 0),
        )

        ttk.Button(
            actions,
            text="LAUNCH MTT",
            style="Launch.TButton",
            command=self.launch_selected,
        ).pack(side="left")

        ttk.Button(
            actions,
            text="Settings",
            command=self.open_settings,
        ).pack(
            side="right",
            padx=(8, 0),
        )

        ttk.Button(
            actions,
            text="Recent Updates",
            command=self.show_updates,
        ).pack(side="right")

        # Footer --------------------------------------------------------

        footer = ttk.Frame(root)

        footer.pack(
            fill="x",
            pady=(12, 0),
        )

        ttk.Label(
            footer,
            textvariable=self.status_var,
            style="Bottom.TLabel",
        ).pack(side="left")

        ttk.Label(
            footer,
            text="MTT Launcher • Build 78",
            style="Bottom.TLabel",
        ).pack(side="right")

    def _create_dashboard_card(
        self,
        parent: ttk.Frame,
        name: str,
        info: dict[str, str],
    ) -> None:

        card = tk.Frame(
            parent,
            bg="white",
            highlightthickness=1,
            highlightbackground="#d9d9d9",
            highlightcolor="#d9d9d9",
        )

        card.pack(
            fill="x",
            pady=3,
        )

        # Dashboard selection button -------------------------------

        button = tk.Button(
            card,
            text=name,
            command=lambda n=name: self._select_dashboard(n),
            bg="#e9e9e9",
            fg="#1a1a1a",
            activebackground="#d6d6d6",
            activeforeground="black",
            relief="flat",
            borderwidth=0,
            width=7,
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=6,
        )

        button.pack(
            side="left",
            padx=8,
            pady=8,
        )

        self.dashboard_buttons[name] = button

        # Dashboard information -------------------------------------

        text = tk.Frame(
            card,
            bg="white",
        )

        text.pack(
            side="left",
            fill="x",
            expand=True,
            pady=6,
        )

        tk.Label(
            text,
            text=f"MTT Dashboard {name[1:]}",
            bg="white",
            fg="#1a1a1a",
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(anchor="w")

        tk.Label(
            text,
            text=info["description"],
            bg="white",
            fg="#5a5a5a",
            font=("Segoe UI", 8),
            anchor="w",
        ).pack(anchor="w")

        # Make entire card clickable (bind to same select)
        for w in (card, text):
            w.bind("<Button-1>", lambda e, n=name: self._select_dashboard(n))
        # Also bind labels inside text frame for full area
        for child in text.winfo_children():
            child.bind("<Button-1>", lambda e, n=name: self._select_dashboard(n))

    # ------------------------------------------------------------------
    # Dashboard selection
    # ------------------------------------------------------------------

    def _select_dashboard(self, dashboard: str) -> None:
        self.selected_dashboard.set(dashboard)

        for name, button in self.dashboard_buttons.items():
            if name == dashboard:
                button.configure(
                    bg="#d0d0d0",
                )
            else:
                button.configure(
                    bg="#e9e9e9",
                )

        self.status_var.set(
            f"Selected MTT Dashboard {dashboard[1:]}. "
            "Ready to launch."
        )
        # Persist selection
        try:
            cfg = _load_launcher_config()
            cfg["selected_dashboard"] = dashboard
            _save_launcher_config(cfg)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Launch
    # ------------------------------------------------------------------

    def launch_selected(self) -> None:
        dashboard = self.selected_dashboard.get()
        info = DASHBOARDS[dashboard]

        command = [
            sys.executable,
            "-m",
            info["module"],
        ]

        # If fullscreen is ON, pass --fullscreen for dashboards that accept it (V4) — harmless for others that ignore
        try:
            if load_fullscreen():
                # Only dashboards known to accept --fullscreen should get it to avoid argparse errors.
                # V4 accepts --fullscreen; others read xmbsettings.xml internally, so skip.
                if dashboard == "V4":
                    command.append("--fullscreen")
        except Exception:
            pass

        try:
            subprocess.Popen(
                command,
                cwd=str(PROJECT_ROOT),
                env=os.environ.copy(),
            )

            self.status_var.set(
                f"Launching MTT Dashboard {dashboard[1:]}..."
            )

        except Exception as exc:
            messagebox.showerror(
                "MTT Launcher",
                (
                    f"Could not launch Dashboard {dashboard[1:]}.\n\n"
                    f"{exc}"
                ),
            )

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def open_settings(self) -> None:
        # Reuse existing window if still open
        if self._settings_win is not None and self._settings_win.winfo_exists():
            try:
                self._settings_win.lift()
                self._settings_win.focus_force()
                return
            except Exception:
                pass
        # Also scan children for orphaned instance
        for w in list(self.winfo_children()):
            if isinstance(w, SettingsWindow) and w.winfo_exists():
                try:
                    w.lift()
                    w.focus_force()
                    self._settings_win = w
                    return
                except Exception:
                    pass
        win = SettingsWindow(self)
        self._settings_win = win
        # Clear ref on close
        def _on_close(_w=win):
            try:
                if self._settings_win is _w:
                    self._settings_win = None
            except Exception:
                pass
        win.bind("<Destroy>", lambda e, _w=win: _on_close(_w) if e.widget is _w else None, add="+")

    # ------------------------------------------------------------------
    # Recent updates
    # ------------------------------------------------------------------

    def show_updates(self) -> None:
        if self._updates_win is not None and self._updates_win.winfo_exists():
            try:
                self._updates_win.lift()
                self._updates_win.focus_force()
                return
            except Exception:
                pass
        for w in list(self.winfo_children()):
            if isinstance(w, UpdatesWindow) and w.winfo_exists():
                try:
                    w.lift()
                    w.focus_force()
                    self._updates_win = w
                    return
                except Exception:
                    pass
        win = UpdatesWindow(self)
        self._updates_win = win
        def _on_close(_w=win):
            try:
                if self._updates_win is _w:
                    self._updates_win = None
            except Exception:
                pass
        win.bind("<Destroy>", lambda e, _w=win: _on_close(_w) if e.widget is _w else None, add="+")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    app = MTTLauncher()
    app.mainloop()


if __name__ == "__main__":
    main()
