"""
Torsion — MTT's 3D engine.

REALLY easy (procedural, no boilerplate):

    import torsion
    torsion.new_window("Milk Toast Taco", 1280, 720)
    torsion.draw_mesh("assets/models/truck.glb", (0, 0, 0))
    torsion.draw_cube((2, 0, 0), size=1.5, color="#ff4422")
    torsion.draw_ground(size=30, color="#3a7d44")
    torsion.camera((6, 5, 8), look_at=(0, 0, 0))
    torsion.sun(direction=(-0.5, -1, -0.3))
    torsion.run()  # or torsion.run(max_frames=1) headless

Classic OOP still works:

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
from . import easy as _easy

# -- sugar re-exports so `torsion.Cube` works --
Cube = _primitives.Cube
Sphere = _primitives.Sphere
Ground = _primitives.Ground
Plane = _primitives.Plane

# -- REALLY easy procedural API (global default window/scene) --
#   torsion.new_window() / torsion.draw_mesh("cube", (0,0,0)) / torsion.run()
new_window = _easy.new_window
create_window = _easy.create_window
open_window = _easy.open_window
window = _easy.window
get_app = _easy.get_app
get_scene = _easy.get_scene
draw_mesh = _easy.draw_mesh
mesh = _easy.mesh
spawn = _easy.spawn
add_mesh = _easy.add_mesh
draw_cube = _easy.draw_cube
draw_sphere = _easy.draw_sphere
draw_plane = _easy.draw_plane
draw_ground = _easy.draw_ground
sun = _easy.sun
light = _easy.light
spot_light = _easy.spot_light
camera = _easy.camera
set_camera = _easy.set_camera
clear = _easy.clear
run = _easy.run
close_window = _easy.close_window
quit = _easy.quit
exit = _easy.exit
screenshot = _easy.screenshot
# extra discoverability aliases
draw_model = _easy.draw_model
load_model = _easy.load_model
cube = _easy.cube
sphere = _easy.sphere
plane = _easy.plane
ground = _easy.ground
sky = _easy.sky

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
    # REALLY easy sugar
    "new_window",
    "create_window",
    "open_window",
    "window",
    "get_app",
    "get_scene",
    "draw_mesh",
    "draw_model",
    "load_model",
    "mesh",
    "spawn",
    "add_mesh",
    "draw_cube",
    "cube",
    "draw_sphere",
    "sphere",
    "draw_plane",
    "plane",
    "draw_ground",
    "ground",
    "sun",
    "light",
    "spot_light",
    "camera",
    "set_camera",
    "sky",
    "clear",
    "run",
    "close_window",
    "quit",
    "exit",
    "screenshot",
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
