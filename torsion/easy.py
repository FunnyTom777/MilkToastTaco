"""
torsion.easy — the "REALLY easy" procedural sugar.

Goal: MTT can do this with ZERO boilerplate:

    import torsion

    torsion.new_window("Milk Toast Taco", 1280, 720)
    torsion.draw_mesh("assets/models/truck.glb", (0, 0, 0))
    torsion.draw_cube((2, 0, 0), size=1.5, color="#ff4422")
    torsion.draw_sphere((0, 3, 0), radius=0.5, color="skyblue")
    torsion.camera((6, 5, 8), look_at=(0, 0, 0))
    torsion.sun(direction=(-0.5, -1, -0.3))
    torsion.run()

No App/Scene/Mesh boilerplate needed. Advanced code can still use
the OOP API (`torsion.App`, `torsion.Scene`, etc.) — this layer is
just a thin global default.

All helpers auto-create a window/scene if you forgot `new_window()`.
"""

from __future__ import annotations

from typing import Any

from .math import Vec3, Color, Quat
from .assets import Mesh, Material
from .camera import PerspectiveCamera
from .light import DirectionalLight, PointLight, SpotLight
from .scene import Scene, Entity
from .app import App

# ------------------------------------------------------------------ globals
_default_app: App | None = None
_default_scene: Scene | None = None


def _coerce_vec3(pos: Any, y: Any = None, z: Any = None) -> Vec3:
    """Forgiving XYZ parser: Vec3, tuple, list, or separate x,y,z."""
    if isinstance(pos, Vec3):
        return pos
    if y is not None or z is not None:
        # draw_mesh("cube", 1, 2, 3) style
        x = pos
        return Vec3(float(x), float(y or 0), float(z or 0))
    if pos is None:
        return Vec3.zero()
    if isinstance(pos, (list, tuple)):
        if len(pos) == 2:
            return Vec3(float(pos[0]), float(pos[1]), 0)
        if len(pos) == 3:
            return Vec3(float(pos[0]), float(pos[1]), float(pos[2]))
        raise ValueError(f"xyz must be (x,y,z), got {pos!r}")
    raise TypeError(f"Cannot coerce {pos!r} to Vec3")


def _coerce_color(c: Any) -> Color | None:
    if c is None:
        return None
    if isinstance(c, Color):
        return c
    if isinstance(c, str):
        # named colors
        named = {
            "white": Color.WHITE,
            "black": Color.BLACK,
            "red": Color.RED,
            "green": Color.GREEN,
            "blue": Color.BLUE,
            "sky": Color.SKY,
            "skyblue": Color.SKY,
        }
        if c.lower() in named:
            return named[c.lower()]
        return Color.from_hex(c)
    if isinstance(c, (list, tuple)):
        if len(c) == 3:
            return Color(float(c[0]), float(c[1]), float(c[2]), 1)
        if len(c) == 4:
            return Color(float(c[0]), float(c[1]), float(c[2]), float(c[3]))
    raise TypeError(f"Cannot coerce {c!r} to Color")


def _ensure_window(title: str = "Torsion3D", width: int = 1280, height: int = 720, **kw) -> tuple[App, Scene]:
    global _default_app, _default_scene
    if _default_app is None or _default_scene is None:
        _default_app = App(title=title, width=width, height=height, **kw)
        _default_scene = Scene(name=title)
        # sensible defaults so empty scene isn't pitch black
        _default_scene.set_ambient("#ffffff", 0.35)
        _default_scene.add(DirectionalLight(direction=Vec3(-0.5, -1, -0.3), intensity=1.0))
        cam = PerspectiveCamera(fov=75, position=Vec3(6, 5, 8))
        cam.look_at(Vec3(0, 0, 0))
        _default_scene.add(cam, name="__default_cam")
    return _default_app, _default_scene


# ------------------------------------------------------------------ public sugar

def new_window(title: str = "Torsion3D", width: int = 1280, height: int = 720, **kwargs) -> App:
    """
    Create (or recreate) the default window + scene.

        torsion.new_window()  # 1280x720
        torsion.new_window("My Game", 1920, 1080, fullscreen=False)
        torsion.new_window(backend="headless")  # for tests

    Returns the App. Access scene via `torsion.get_scene()`.
    """
    global _default_app, _default_scene
    # allow new_window(1920,1080) positional width/height
    if isinstance(title, int):
        # called as new_window(1280,720)
        width, height = int(title), int(width) if isinstance(width, int) else 720
        title = "Torsion3D"
    _default_app = App(title=title, width=width, height=height, **kwargs)
    _default_scene = Scene(name=title)
    _default_scene.set_ambient("#ffffff", 0.35)
    return _default_app


# aliases people will try
create_window = new_window
window = new_window
open_window = new_window


def get_app() -> App:
    if _default_app is None:
        _ensure_window()
    return _default_app  # type: ignore


def get_scene() -> Scene:
    if _default_scene is None:
        _ensure_window()
    return _default_scene  # type: ignore


def _resolve_material(color: Any, material: Material | None, roughness: float | None, metallic: float | None) -> Material | None:
    if material is not None:
        return material
    col = _coerce_color(color)
    if col is None and roughness is None and metallic is None:
        return None
    m = Material.albedo(col or Color(0.8, 0.8, 0.8))
    if roughness is not None:
        m.roughness = float(roughness)
    if metallic is not None:
        m.metallic = float(metallic)
    return m


def draw_mesh(
    model: str | Mesh = "cube",
    pos: Any = None,
    y: Any = None,
    z: Any = None,
    *,
    xyz: Any = None,
    position: Any = None,
    rotation: Any = None,
    scale: Any = None,
    color: Any = None,
    material: Material | None = None,
    roughness: float | None = None,
    metallic: float | None = None,
    name: str | None = None,
    size: float | None = None,
    radius: float | None = None,
    **meta,
) -> Entity:
    """
    One-liner to drop a mesh into the default scene.

    All of these work:

        torsion.draw_mesh("assets/truck.glb", (0, 0, 0))
        torsion.draw_mesh("assets/truck.glb", 0, 0, 0)
        torsion.draw_mesh("cube", (1, 2, 3), size=2, color="#ff0000")
        torsion.draw_mesh("sphere", pos=(0,1,0), radius=0.7, color="skyblue")
        torsion.draw_mesh(Mesh.cube(), position=(0,0,0))
        torsion.draw_mesh("cube", xyz=(0,1,0))  # explicit kw

    `model` can be:
      - file path: "assets/models/truck.glb" / ".obj" / ".bam"
      - primitive name: "cube", "sphere", "plane", "ground"
      - Mesh instance
    """
    # normalize position — accept pos / xyz / position / or (x,y,z) as 2nd arg
    if xyz is not None:
        pos = xyz
    if position is not None:
        pos = position
    vec = _coerce_vec3(pos, y, z)

    # rotation: accept tuple degrees or Quat
    rot = None
    if rotation is not None:
        if isinstance(rotation, Quat):
            rot = rotation
        elif isinstance(rotation, (list, tuple)):
            rot = Quat.from_euler_deg(*rotation)
        else:
            raise TypeError(f"rotation must be (x,y,z) degrees or Quat, got {rotation!r}")

    sc = None
    if scale is not None:
        sc = Vec3(*scale) if isinstance(scale, (list, tuple)) else scale

    mat = _resolve_material(color, material, roughness, metallic)

    # resolve Mesh
    if isinstance(model, Mesh):
        mesh = model
        if mat is not None:
            mesh.material = mat
    elif isinstance(model, str):
        low = model.lower().strip()
        if low in ("cube", "box"):
            mesh = Mesh.cube(size=size or 1.0, material=mat or Material())
        elif low in ("sphere", "ball"):
            mesh = Mesh.sphere(radius=radius or 0.5, material=mat or Material())
        elif low in ("plane", "ground", "floor"):
            mesh = Mesh.plane(size=size or 10.0, material=mat or Material())
        else:
            # treat as file path — size/radius ignored
            mesh = Mesh.from_file(model, material=mat)
    else:
        raise TypeError(f"model must be str or Mesh, got {type(model).__name__}")

    _, scene = _ensure_window()
    return scene.spawn(mesh, position=vec, rotation=rot, scale=sc, name=name, **meta)


# even shorter aliases
mesh = draw_mesh
spawn = draw_mesh
add_mesh = draw_mesh


def draw_cube(pos: Any = None, y: Any = None, z: Any = None, *, size: float = 1.0, color: Any = None, **kw) -> Entity:
    """Sugar: `torsion.draw_cube((0,1,0), size=2, color="#ff0000")`"""
    vec = _coerce_vec3(pos, y, z) if pos is not None or y is not None else Vec3.zero()
    # allow draw_cube(1,2,3) without kw
    if isinstance(pos, (int, float)) and isinstance(y, (int, float)):
        vec = _coerce_vec3(pos, y, z)
        # shift kwargs handling
    return draw_mesh("cube", vec, size=size, color=color, **kw)


def draw_sphere(pos: Any = None, y: Any = None, z: Any = None, *, radius: float = 0.5, color: Any = None, **kw) -> Entity:
    vec = _coerce_vec3(pos, y, z) if pos is not None or y is not None else Vec3.zero()
    return draw_mesh("sphere", vec, radius=radius, color=color, **kw)


def draw_plane(pos: Any = None, *, size: float = 10.0, color: Any = "#3a7d44", **kw) -> Entity:
    vec = _coerce_vec3(pos) if pos is not None else Vec3.zero()
    return draw_mesh("plane", vec, size=size, color=color, **kw)


def draw_ground(*a, **kw) -> Entity:
    return draw_plane(*a, **kw)


# light / camera sugar
def sun(direction: Any = (-0.5, -1, -0.3), color: Any = None, intensity: float = 1.0, shadows: bool = True) -> Entity:
    """Add a directional sun: `torsion.sun(direction=(-1,-1,0))`"""
    _, scene = _ensure_window()
    d = _coerce_vec3(direction) if not isinstance(direction, Vec3) else direction
    c = _coerce_color(color) or Color.WHITE
    return scene.add(DirectionalLight(direction=d, color=c, intensity=intensity, cast_shadows=shadows))


def light(pos: Any = None, y: Any = None, z: Any = None, *, color: Any = None, intensity: float = 1.0, radius: float = 10.0, shadows: bool = False, **kw) -> Entity:
    """Point light: `torsion.light((0,3,0), color='#ffffaa', radius=15)`"""
    vec = _coerce_vec3(pos, y, z) if pos is not None or y is not None else Vec3(0, 3, 0)
    c = _coerce_color(color) or Color.WHITE
    _, scene = _ensure_window()
    return scene.add(PointLight(position=vec, color=c, intensity=intensity, radius=radius, cast_shadows=shadows), **kw)


def spot_light(pos: Any = None, direction: Any = (0, -1, 0), **kw) -> Entity:
    _, scene = _ensure_window()
    p = _coerce_vec3(pos) if pos is not None else Vec3.zero()
    d = _coerce_vec3(direction) if not isinstance(direction, Vec3) else direction
    col = _coerce_color(kw.pop("color", None)) or Color.WHITE
    return scene.add(SpotLight(position=p, direction=d, color=col, intensity=kw.pop("intensity", 1.0)), **kw)


def camera(pos: Any = None, y: Any = None, z: Any = None, *, look_at: Any = None, fov: float = 75, **kw) -> Entity:
    """
    Place camera: `torsion.camera((6,5,8), look_at=(0,0,0))`
    Also: `torsion.camera(6, 5, 8)` or `torsion.camera(x=6, y=5, z=8)`
    """
    if look_at is None and "target" in kw:
        look_at = kw.pop("target")
    # handle named xyz
    if "x" in kw or "y" in kw or "z" in kw:
        pos = Vec3(float(kw.pop("x", 0)), float(kw.pop("y", 0)), float(kw.pop("z", 0)))
    else:
        vec = _coerce_vec3(pos, y, z) if pos is not None or y is not None else Vec3(6, 5, 8)
        pos = vec
    _, scene = _ensure_window()
    cam = PerspectiveCamera(fov=fov, position=pos)  # type: ignore
    if look_at is not None:
        tgt = _coerce_vec3(look_at) if not isinstance(look_at, Vec3) else look_at
        cam.look_at(tgt)
    # replace default cam if present
    for e in list(scene.entities):
        if e.camera is not None and e.name == "__default_cam":
            scene.remove(e)
            break
    return scene.add(cam, **kw)


def set_camera(*a, **kw) -> Entity:
    return camera(*a, **kw)


def clear() -> None:
    """Clear all entities from default scene (keeps camera/light defaults if you want — use clear(clear_all=False) later)."""
    _, scene = _ensure_window()
    scene.clear()
    # re-add defaults
    scene.set_ambient("#ffffff", 0.35)
    scene.add(DirectionalLight(direction=Vec3(-0.5, -1, -0.3)))


def run(max_frames: int | None = None, dt: float | None = None) -> None:
    """
    Run the default window:

        torsion.new_window()
        torsion.draw_cube((0,0,0))
        torsion.run()              # blocks until window closed
        torsion.run(max_frames=1)  # headless test — one frame then return
    """
    app, scene = _ensure_window()
    app.run(scene, max_frames=max_frames, dt=dt)


def close_window() -> None:
    global _default_app, _default_scene
    if _default_app is not None:
        _default_app.shutdown()
    _default_app = None
    _default_scene = None


def screenshot(path: str) -> None:
    app, _ = _ensure_window()
    if app.renderer:
        app.renderer.screenshot(path)
    else:
        print(f"[Torsion] screenshot('{path}') — no renderer yet, call new_window() first")


# -- extra aliases so discovery is REALLY easy --
draw_model = draw_mesh
load_model = draw_mesh
cube = draw_cube
sphere = draw_sphere
plane = draw_plane
ground = draw_ground
quit = close_window
exit = close_window
set_camera = camera  # already, keep
sky = lambda color="#87ceeb", **kw: get_scene().set_ambient(color, kw.get("intensity", 0.35))
