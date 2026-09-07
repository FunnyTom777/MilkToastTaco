"""MTT Dashboard V4 — PyImGui console hub (controller + KBM)."""

# Lazy exports to avoid RuntimeWarning when running `python -m core.renderer.dashboard_v4.dashboard_v4`
# (eager `from .dashboard_v4 import ...` preloads the submodule before runpy does).
__all__ = ["DashboardV4API", "run"]

def __getattr__(name):
    if name in __all__:
        from . import dashboard_v4 as _mod
        return getattr(_mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
