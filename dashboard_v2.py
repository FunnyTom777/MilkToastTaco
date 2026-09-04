#!/usr/bin/env python3
"""
Project-root shim for MTT Dashboard V2.

Canonical implementation lives at core/renderer/dashboard_v2/dashboard_v2.py
(mirroring the XMB pattern core/renderer/main_menu/xmb.py).

This shim exists so `python dashboard_v2.py` and
`python -m core.renderer.dashboard_v2.dashboard_v2` both work.
"""

from core.renderer.dashboard_v2.dashboard_v2 import DashboardV2API, get_dashboard_v2_html_path, run

__all__ = ["DashboardV2API", "get_dashboard_v2_html_path", "run"]

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="MTT Dashboard V2 (root shim)")
    p.add_argument("--debug", action="store_true", help="Enable pywebview debug")
    args = p.parse_args()
    run(debug=args.debug)
