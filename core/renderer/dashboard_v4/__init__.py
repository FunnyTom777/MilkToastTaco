"""
MTT Dashboard V4 — Native Desktop Hub (PyQt6).
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.renderer.dashboard_v4.dashboard_v4 import DashboardV4API, run
    from core.renderer.dashboard_v4.ui.main_window import DashboardV4MainWindow


def __getattr__(name: str):
    if name in ("DashboardV4API", "run"):
        from core.renderer.dashboard_v4 import dashboard_v4
        return getattr(dashboard_v4, name)
    if name == "DashboardV4MainWindow":
        from core.renderer.dashboard_v4.ui.main_window import DashboardV4MainWindow
        return DashboardV4MainWindow
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["DashboardV4API", "run", "DashboardV4MainWindow"]
