"""
Torsion — MTT's 3D engine.

Quickstart (no dependencies, headless):
    import torsion
    app = torsion.App(title="Milk Toast Taco")
    scene = torsion.Scene()
    scene.add(torsion.Ground())
    scene.spawn(torsion.Mesh.cube(), position=(0, 0.5, 0))
    app.run(scene, max_frames=1)

With Panda3D (real window):
    pip install -e ".[torsion]"   # pulls panda3d + dearpygui
    python -m torsion.examples.basic

Design goals (per engine/Torsion/torsion_engine.md):
  - Panda3D for rendering (lazy — headless fallback if missing)
  - DearPyGUI for debug/tool UI (lazy)
  - VERY easy for MTT and future games to use
"""

from __future__ import annotations

# -- version --
from ._version import __version__, __engine_name__, __full_name__

# -- math --
from .math import Vec2, Vec3, Vec4, Color, Quat, Mat4

# -- core --
from .transform import Transform
from .scene import Scene, Entity
from .assets import Mesh, Material, Texture
from .camera import Camera, PerspectiveCamera, OrthographicCamera
from .light import Light, DirectionalLight, PointLight, SpotLight
from .renderer import Renderer, Backend, get_backend, is_panda_available, create_renderer
from .app import App, WindowConfig
from .debug import DebugOverlay
from . import primitives as _primitives

# -- sugar re-exports so `torsion.Cube` works --
Cube = _primitives.Cube
Sphere = _primitives.Sphere
Ground = _primitives.Ground
Plane = _primitives.Plane

# alias: `import torsion3d` should also work via engine alias
# (we keep `torsion` as canonical; `torsion3d` is just a friendly name)

__all__ = [
    "__version__",
    "__engine_name__",
    "__full_name__",
    # math
    "Vec2",
    "Vec3",
    "Vec4",
    "Color",
    "Quat",
    "Mat4",
    "Transform",
    # scene
    "Scene",
    "Entity",
    # assets
    "Mesh",
    "Material",
    "Texture",
    # camera
    "Camera",
    "PerspectiveCamera",
    "OrthographicCamera",
    # light
    "Light",
    "DirectionalLight",
    "PointLight",
    "SpotLight",
    # app/renderer
    "App",
    "WindowConfig",
    "Renderer",
    "Backend",
    "get_backend",
    "is_panda_available",
    "create_renderer",
    "DebugOverlay",
    # primitives sugar
    "Cube",
    "Sphere",
    "Ground",
    "Plane",
    # helpers
    "quick_start",
]


def quick_start(title: str = "Torsion3D", size: tuple[int, int] = (1280, 720)) -> tuple[App, Scene]:
    """
    One-liner for MTT prototyping:

        app, scene = torsion.quick_start("My Scene")
        scene.spawn(torsion.Mesh.cube(), position=(0,1,0))
        app.run(scene)
    """
    app = App(title=title, width=size[0], height=size[1])
    scene = Scene(name=title)
    return app, scene


# `import torsion3d` alias support — register this package as torsion3d
import sys as _sys

_sys.modules.setdefault("torsion3d", _sys.modules[__name__])
