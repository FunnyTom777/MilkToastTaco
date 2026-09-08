"""
torsion.renderer — backend abstraction.

Backends:
  - "panda3d"  : real window via Panda3D (if installed)
  - "headless" : no window, logs calls, great for tests / CI
  - "mock"     : alias for headless

Auto-detect: try Panda3D, fall back to headless.

MTT code never imports panda3d directly:
    from torsion.renderer import Renderer, get_backend
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Any

from .scene import Scene


class Backend(str, Enum):
    PANDA3D = "panda3d"
    HEADLESS = "headless"
    MOCK = "mock"


_detected: Backend | None = None


def _detect_backend() -> Backend:
    """Probe for Panda3D without importing it at module load."""
    # Allow override via env var
    env = os.environ.get("TORSION_BACKEND", "").lower().strip()
    if env in ("headless", "mock"):
        return Backend.HEADLESS
    if env in ("panda3d", "panda"):
        return Backend.PANDA3D
    # auto
    try:
        import importlib.util

        if importlib.util.find_spec("panda3d") is not None:
            return Backend.PANDA3D
    except Exception:
        pass
    return Backend.HEADLESS


def get_backend() -> Backend:
    global _detected
    if _detected is None:
        _detected = _detect_backend()
    return _detected


def is_panda_available() -> bool:
    return get_backend() == Backend.PANDA3D


# ------------------------------------------------------------------ base
class Renderer:
    """Abstract renderer. Subclassed by PandaRenderer / HeadlessRenderer."""

    def __init__(self, scene: Scene | None = None):
        self.scene = scene

    def attach_scene(self, scene: Scene) -> None:
        self.scene = scene

    def init(self) -> None:
        raise NotImplementedError

    def frame(self, dt: float) -> None:
        """Called each frame."""
        pass

    def shutdown(self) -> None:
        pass

    def screenshot(self, path: str) -> None:
        raise NotImplementedError


# ------------------------------------------------------------------ headless
class HeadlessRenderer(Renderer):
    """Logs scene state, does not open a window. Perfect for MTT logic tests."""

    def __init__(self, scene: Scene | None = None, verbose: bool = False):
        super().__init__(scene)
        self.verbose = verbose
        self.frames = 0

    def init(self) -> None:
        print(f"[Torsion:headless] init — scene={self.scene!r}")

    def frame(self, dt: float) -> None:
        self.frames += 1
        if self.verbose and self.scene is not None:
            print(f"[Torsion:headless] frame {self.frames} dt={dt:.4f} entities={len(self.scene)}")

    def shutdown(self) -> None:
        print(f"[Torsion:headless] shutdown after {self.frames} frames")

    def screenshot(self, path: str) -> None:
        print(f"[Torsion:headless] screenshot('{path}') — no-op in headless")


# ------------------------------------------------------------------ Panda3D (lazy)
class PandaRenderer(Renderer):
    """
    Real renderer. Only instantiated when Panda3D is installed and App requests it.
    Import is deferred to init() so `import torsion` never fails if panda3d missing.
    """

    def __init__(self, scene: Scene | None = None, window_title: str = "Torsion3D", size=(1280, 720)):
        super().__init__(scene)
        self.window_title = window_title
        self.size = size
        self._app = None  # ShowBase instance

    def init(self) -> None:
        try:
            from direct.showbase.ShowBase import ShowBase  # type: ignore
            from panda3d.core import WindowProperties  # type: ignore
        except ImportError as e:
            print(f"[Torsion] Panda3D not installed ({e}), falling back to headless")
            # degrade gracefully
            fallback = HeadlessRenderer(self.scene)
            fallback.init()
            self.__class__ = HeadlessRenderer  # type: ignore
            self.__dict__.update(fallback.__dict__)
            return

        # Minimal ShowBase — MTT will expand this later
        class _TorsionShowBase(ShowBase):
            def __init__(inner_self, outer):  # noqa: N805
                ShowBase.__init__(inner_self)
                wp = WindowProperties()
                wp.setTitle(outer.window_title)
                wp.setSize(*outer.size)
                inner_self.win.requestProperties(wp)
                inner_self.disableMouse()
                # TODO: attach scene entities to render
                print(f"[Torsion:panda3d] window '{outer.window_title}' {outer.size[0]}x{outer.size[1]}")
                if outer.scene:
                    print(f"[Torsion:panda3d] scene '{outer.scene.name}' with {len(outer.scene)} entities (attach TODO)")

        self._app = _TorsionShowBase(self)

    def frame(self, dt: float) -> None:
        if self._app is not None:
            self._app.taskMgr.step()

    def shutdown(self) -> None:
        if self._app is not None:
            try:
                self._app.userExit()
            except SystemExit:
                pass

    def screenshot(self, path: str) -> None:
        if self._app is not None:
            self._app.win.saveScreenshot(path)
            print(f"[Torsion:panda3d] screenshot -> {path}")


# ------------------------------------------------------------------ factory
def create_renderer(backend: str | Backend | None = None, scene: Scene | None = None, **kwargs: Any) -> Renderer:
    """
    Factory used by App. Keeps MTT code backend-agnostic.
    """
    if backend is None:
        backend = get_backend()
    if isinstance(backend, str):
        backend = Backend(backend.lower())
    if backend == Backend.PANDA3D:
        return PandaRenderer(scene, **kwargs)
    # headless / mock / unknown -> headless (strip panda-only kwargs)
    kwargs.pop("window_title", None)
    kwargs.pop("size", None)
    return HeadlessRenderer(scene, **kwargs)
