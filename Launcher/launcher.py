#!/usr/bin/env python3
"""
Milk Toast Taco Launcher
A small Tkinter launcher for the four MTT dashboard versions.

Run:
    python launcher.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk


PROJECT_ROOT = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Dashboard definitions
# ---------------------------------------------------------------------------

DASHBOARDS = {
    "V1": {
        "module": "core.renderer.dashboard_v1.dashboard_v1",
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

        self.selected_dashboard = tk.StringVar(value="V2")

        self.dashboard_buttons: dict[str, tk.Button] = {}

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
        self._select_dashboard("V2")

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
            text="MTT Launcher • Build 77",
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
        messagebox.showinfo(
            "MTT Settings",
            "Settings UI coming soon!\n\n"
            "Planned options:\n"
            "• Default dashboard\n"
            "• Debug mode\n"
            "• Fullscreen\n"
            "• Game launch arguments\n"
            "• Game directory",
        )

    # ------------------------------------------------------------------
    # Recent updates
    # ------------------------------------------------------------------

    def show_updates(self) -> None:
        messagebox.showinfo(
            "Recent Updates",
            "Recent MTT development:\n\n"
            "• Commit 76 — latest MTT changes\n"
            "• Commit 75 — replaced online Font Awesome icons "
            "with local icons\n"
            "• Commit 74 — previous MTT improvements\n\n"
            "Full changelog integration coming soon!",
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    app = MTTLauncher()
    app.mainloop()


if __name__ == "__main__":
    main()
