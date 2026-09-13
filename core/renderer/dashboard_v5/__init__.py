"""
MTT Dashboard V5 — Textual command prompt (package marker).

Lazy re-export (mirrors dashboard_v4) so
``python -m core.renderer.dashboard_v5.dashboardv5`` stays warning-free.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.renderer.dashboard_v5.dashboardv5 import DashboardV5App, run


def __getattr__(name: str):
    if name in ("DashboardV5App", "run"):
        from core.renderer.dashboard_v5 import dashboardv5
        return getattr(dashboardv5, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["DashboardV5App", "run"]
