#!/usr/bin/env python3
"""
Project-root shim for MTT Dashboard V3.

Canonical implementation lives at core/renderer/dashboard_v3/dashboard_v3.py
(mirroring the XMB pattern core/renderer/main_menu/xmb.py).

This shim exists so `python dashboard_v3.py` and
`python -m core.renderer.dashboard_v3.dashboard_v3` both work.
"""

from core.renderer.dashboard_v3.dashboard_v3 import DashboardV3API, get_dashboard_v3_html_path, get_controller_js_path, run

__all__ = ["DashboardV3API", "get_dashboard_v3_html_path", "get_controller_js_path", "run"]

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="MTT Dashboard V3 (root shim) — Console Hub")
    p.add_argument("--debug", action="store_true", help="Enable pywebview debug")
    args = p.parse_args()
    run(debug=args.debug)
