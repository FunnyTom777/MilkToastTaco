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

    p = argparse.ArgumentParser(description="MTT Dashboard V4 (PyQt6) — Native Desktop Hub")
    p.add_argument("--debug", action="store_true", help="Enable debug logging")
    p.add_argument("--width", type=int, default=1280, help="Initial window width")
    p.add_argument("--height", type=int, default=800, help="Initial window height")
    p.add_argument("--fullscreen", action="store_true", help="Open fullscreen (default from settings)")
    p.add_argument("--theme", type=str, default=None, help="Theme override (default, dark_purple, crimson_red, midnight_green, ocean_blue)")
    p.add_argument("--player-id", type=int, default=1, help="Active player ID (default: 1)")
    args = p.parse_args()
    run(
        debug=args.debug,
        width=args.width,
        height=args.height,
        fullscreen=True if args.fullscreen else None,
        theme=args.theme,
        player_id=args.player_id,
    )
