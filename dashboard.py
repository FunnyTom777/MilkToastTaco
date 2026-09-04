#!/usr/bin/env python3
"""
Project-root shim for the MTT Dashboard.

Canonical implementation lives at core/renderer/dashboard/dashboard.py
(mirroring the XMB pattern core/renderer/main_menu/xmb.py).

This shim exists so `python dashboard.py` and `python -m core.renderer.dashboard.dashboard`
both work, and to satisfy the issue spec wording "its own 'dashboard.py'".
"""

from core.renderer.dashboard.dashboard import DashboardAPI, get_dashboard_html_path, run

__all__ = ["DashboardAPI", "get_dashboard_html_path", "run"]

if __name__ == "__main__":
    # Re-parse args here to avoid double-parse inside dashboard.run
    import argparse
    p = argparse.ArgumentParser(description="MTT Dashboard (root shim)")
    p.add_argument("--dev", action="store_true", help="Start in Dev Mode")
    p.add_argument("--debug", action="store_true", help="Enable pywebview debug")
    args = p.parse_args()
    run(dev_mode=args.dev, debug=args.debug)
