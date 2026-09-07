#!/usr/bin/env python3
"""
Project-root shim for MTT Dashboard V4.

Canonical implementation lives at core/renderer/dashboard_v4/dashboard_v4.py
(mirroring the XMB pattern core/renderer/main_menu/xmb.py).

This shim exists so `python dashboard_v4.py` and
`python -m core.renderer.dashboard_v4.dashboard_v4` both work.
"""

from core.renderer.dashboard_v4.dashboard_v4 import DashboardV4API, run

__all__ = ["DashboardV4API", "run"]

if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="MTT Dashboard V4 (PyImGui) — Console Hub")
    p.add_argument("--debug", action="store_true", help="Verbose + ImGui metrics")
    p.add_argument("--width", type=int, default=1280, help="Window width")
    p.add_argument("--height", type=int, default=800, help="Window height")
    p.add_argument("--fullscreen", action="store_true", help="Open fullscreen (default windowed)")
    p.add_argument("--no-fullscreen", action="store_true", help="Force windowed (default)")
    args = p.parse_args()
    # run() inspects sys.argv for --fullscreen, so keep argv in sync
    run(debug=args.debug, width=args.width, height=args.height)
