**Torsion 3D Game Engine**

`Version 0.1.0` — now scaffolded! See `torsion/` package at repo root.

### REALLY Easy Quickstart (procedural — no boilerplate)

```python
import torsion

torsion.new_window("Milk Toast Taco", 1280, 720)
torsion.draw_mesh("assets/models/truck.glb", (0, 0, 0))
torsion.draw_cube((2, 0, 0), size=1.5, color="#ff4422")
torsion.draw_sphere((0, 3, 0), radius=0.5, color="skyblue")
torsion.draw_ground(size=30, color="#3a7d44")
torsion.camera((6, 5, 8), look_at=(0, 0, 0))
torsion.sun(direction=(-0.5, -1, -0.3))
torsion.run()  # blocks; headless if panda3d not installed

# even shorter aliases:
# torsion.cube((0,1,0)) / torsion.sphere(...) / torsion.ground() / torsion.draw_model(...)
# torsion.light((0,3,0), color="#ffffaa") / torsion.quit()
```

### Classic OOP Quickstart

```python
import torsion

app, scene = torsion.quick_start("Milk Toast Taco")
scene.add(torsion.Ground(size=30, color="#3a7d44"))
scene.spawn(torsion.Mesh.cube(size=1), position=(0, 0.5, 0), name="crate")
scene.add(torsion.DirectionalLight(direction=( -0.5, -1, -0.3 )))

cam = torsion.PerspectiveCamera(fov=75, position=(6, 5, 8))
cam.look_at((0, 0, 0))
scene.add(cam)

app.run(scene)  # Panda3D window if installed, else headless
```

Also works as `import torsion3d` (alias).

Headless / test mode (no window):

```python
app = torsion.App(backend="headless")
app.run(scene, max_frames=1)
# or: TORSION_BACKEND=headless python -m torsion.examples.basic
```

### Stack

- **Panda3D** for rendering — lazy import, auto-falls back to `headless` if not installed (`pip install -e ".[torsion]"`)
- **DearPyGUI** for debug/tool UI — `from torsion.debug import DebugOverlay` (also lazy)
- Pure-Python math (`Vec3`, `Quat`, `Mat4`, `Color`, `Transform`) — no deps

### Package Layout

```
torsion/
  __init__.py        # public API — `import torsion` / `import torsion3d`
  _version.py
  math.py            # Vec2/3/4, Color, Quat, Mat4
  transform.py       # Transform (position/rotation/scale)
  scene.py           # Scene + Entity
  assets.py          # Mesh / Material / Texture
  camera.py          # PerspectiveCamera / OrthographicCamera
  light.py           # Directional / Point / Spot
  primitives.py      # Cube / Sphere / Ground sugar
  renderer.py        # Backend abstraction (panda3d ↔ headless)
  app.py             # App + WindowConfig + main loop
  easy.py            # REALLY easy sugar: new_window / draw_mesh / draw_cube / camera / sun / run
  debug.py           # DearPyGUI overlay (lazy)
  examples/basic.py  # `python -m torsion.examples.basic`  (OOP)
  examples/easy.py   # `python -m torsion.examples.easy`   (one-liners)
```

### Design Goal

VERY easy for MTT (and future WoofWorks games) to use — gameplay code never imports `panda3d` or `dearpygui` directly.

### Install

```bash
pip install -e ".[torsion]"       # rendering + debug UI
# or minimal (already works headless, no extra deps):
pip install -e .
python -m torsion.examples.basic  # headless 3 frames; with panda3d opens window
```

### MTT Integration Sketch

```python
# core/systems/world3d.py (future)
import torsion
from torsion import Vec3

class MTTWorld:
    def __init__(self):
        self.app = torsion.App(title="Milk Toast Taco", width=1280, height=720)
        self.scene = torsion.Scene("farm")
        self.scene.add(torsion.Ground())
        self.camera = torsion.PerspectiveCamera(position=Vec3(0, 8, 12))
        self.camera.look_at(Vec3(0, 0, 0))
        self.scene.add(self.camera)
        # load glTF truck later:
        # self.truck = self.scene.spawn(torsion.Mesh.from_file("assets/models/truck.glb"))

    def run(self):
        self.app.run(self.scene)
```
