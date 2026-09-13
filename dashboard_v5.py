#!/usr/bin/env python3
"""
Project-root shim for MTT Dashboard V5.

Canonical implementation lives at core/renderer/dashboard_v5/dashboardv5.py
(mirroring the XMB pattern core/renderer/main_menu/xmb.py).

This shim exists so `python dashboard_v5.py` and
`python -m core.renderer.dashboard_v5.dashboardv5` both work.
"""

from core.renderer.dashboard_v5.dashboardv5 import DashboardV5App, run

__all__ = ["DashboardV5App", "run"]

if __name__ == "__main__":
    run()
