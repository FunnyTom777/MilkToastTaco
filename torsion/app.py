"""
torsion.app — Application / window loop.

The easiest MTT entry point:

    import torsion
    app = torsion.App(title="Milk Toast Taco", width=1280, height=720)
    scene = torsion.Scene()
    scene.add(torsion.primitives.Ground())
    app.run(scene)

Advanced:
    app = torsion.App(backend="headless")  # for tests
    app.on_update = lambda dt: print(dt)
    app.run(scene, max_frames=60)

Backends are auto-detected (panda3d if installed else headless).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from .scene import Scene
from .renderer import Renderer, create_renderer, get_backend, Backend


@dataclass
class WindowConfig:
    title: str = "Torsion3D"
    width: int = 1280
    height: int = 720
    resizable: bool = True
    vsync: bool = True
    fullscreen: bool = False
    backend: str | Backend | None = None  # None = auto

    @property
    def size(self) -> tuple[int, int]:
        return (self.width, self.height)


class App:
    """
    Owns the window + renderer + main loop.
    Keeps MTT gameplay decoupled from Panda3D.
    """

    def __init__(
        self,
        title: str = "Torsion3D",
        width: int = 1280,
        height: int = 720,
        backend: str | Backend | None = None,
        vsync: bool = True,
        fullscreen: bool = False,
        target_fps: int = 60,
    ):
        self.config = WindowConfig(
            title=title, width=width, height=height, vsync=vsync, fullscreen=fullscreen, backend=backend
        )
        self.target_fps = max(1, int(target_fps))
        self.renderer: Renderer | None = None
        self.scene: Scene | None = None
        self.on_update: Callable[[float], None] | None = None
        self.on_init: Callable[[], None] | None = None
        self._running = False
        self._frame = 0

    # -- properties -----------------------------------------------------------
    @property
    def title(self) -> str:
        return self.config.title

    @title.setter
    def title(self, v: str) -> None:
        self.config.title = str(v)

    @property
    def backend_name(self) -> str:
        return get_backend().value if self.config.backend is None else str(self.config.backend)

    # -- lifecycle ------------------------------------------------------------
    def init(self, scene: Scene | None = None) -> Renderer:
        if scene is not None:
            self.scene = scene
        # create renderer (deferred Panda3D import inside)
        self.renderer = create_renderer(
            backend=self.config.backend,
            scene=self.scene,
            window_title=self.config.title,
            size=self.config.size,
        )
        self.renderer.init()
        if self.on_init:
            self.on_init()
        return self.renderer

    def step(self, dt: float) -> None:
        self._frame += 1
        if self.on_update:
            self.on_update(dt)
        if self.renderer:
            self.renderer.frame(dt)
        # sync scene transforms -> renderer would happen here

    def run(
        self,
        scene: Scene | None = None,
        max_frames: int | None = None,
        dt: float | None = None,
    ) -> None:
        """
        Blocking main loop.
        - dt=None -> real delta time
        - max_frames -> for tests / headless demos (e.g. run 1 frame)
        """
        self.init(scene)
        self._running = True
        last = time.perf_counter()
        fixed_dt = dt
        try:
            while self._running:
                now = time.perf_counter()
                frame_dt = fixed_dt if fixed_dt is not None else min(now - last, 0.1)
                last = now
                self.step(frame_dt)
                if max_frames is not None and self._frame >= max_frames:
                    break
                if fixed_dt is None:
                    # throttle to target_fps (headless only; Panda handles its own loop)
                    if self.renderer and self.renderer.__class__.__name__ == "HeadlessRenderer":
                        sleep = max(0, (1 / self.target_fps) - (time.perf_counter() - now))
                        if sleep:
                            time.sleep(sleep)
                    else:
                        # PandaRenderer steps via taskMgr — don't sleep, but yield
                        pass
                # For PandaRenderer the loop is actually ShowBase-driven;
                # we have a simplified step() here. Full integration will
                # hook into ShowBase task chain later.
                if self.renderer and self.renderer.__class__.__name__ == "PandaRenderer":
                    # In real Panda mode, we'd hand off to ShowBase.run()
                    # For now headless-style loop is fine for scaffolding
                    pass
        except KeyboardInterrupt:
            print("[Torsion] interrupted")
        finally:
            self.shutdown()

    def run_one_frame(self, scene: Scene | None = None) -> None:
        """Convenience for tests."""
        self.run(scene, max_frames=1, dt=1 / 60)

    def stop(self) -> None:
        self._running = False

    def shutdown(self) -> None:
        self._running = False
        if self.renderer:
            self.renderer.shutdown()
            self.renderer = None

    # -- context manager ------------------------------------------------------
    def __enter__(self) -> App:
        self.init()
        return self

    def __exit__(self, *_) -> None:
        self.shutdown()

    def __repr__(self) -> str:
        return f"App(title='{self.title}', {self.config.width}x{self.config.height}, backend={self.backend_name})"
