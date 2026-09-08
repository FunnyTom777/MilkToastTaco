"""
torsion.examples.easy — the REALLY easy API demo.

This is what MTT gameplay code will actually look like:

    import torsion

    torsion.new_window("Milk Toast Taco", 1280, 720)
    torsion.draw_mesh("assets/models/truck.glb", (0, 0, 0))
    torsion.draw_cube((2, 0, 0), size=1.5, color="#ff4422")
    torsion.draw_sphere((0, 3, 0), radius=0.5, color="skyblue")
    torsion.draw_ground(size=30, color="#3a7d44")
    torsion.camera((6, 5, 8), look_at=(0, 0, 0))
    torsion.sun(direction=(-0.5, -1, -0.3))
    torsion.run()

Run:
    python -m torsion.examples.easy              # headless 3 frames if no Panda3D
    TORSION_BACKEND=headless python -m torsion.examples.easy
    python -m torsion.examples.easy --panda      # force Panda window (needs panda3d)
"""

import sys
import torsion

# allow --panda to force real window even in test env
force_panda = "--panda" in sys.argv
backend = None if force_panda else "headless"

# 1-liner window — no App/Scene boilerplate
torsion.new_window("MTT — Easy Demo", 1280, 720, backend=backend)

# drop meshes — file or primitive, any xyz format works
torsion.draw_mesh("cube", (0, 0.5, 0), size=1, color="#cc4444")
torsion.draw_mesh("cube", 2, 0.5, 0, size=1, color="skyblue")  # x,y,z as args
torsion.draw_mesh("assets/models/truck.glb", ( -2, 0, 0))  # would load glTF when wired
torsion.draw_sphere((0, 2, 0), radius=0.5, color="#ffaa00")
torsion.draw_ground(size=30, color="#3a7d44")

# lights + camera — also one-liners
torsion.sun(direction=(-0.5, -1, -0.3), intensity=1.2)
torsion.light((0, 3, 0), color="#ffffaa", radius=15)
torsion.camera((6, 5, 8), look_at=(0, 0, 0))

print(f"[easy] scene has {len(torsion.get_scene())} entities")
print(f"[easy] backend={torsion.get_backend().value if backend is None else backend}")

if backend == "headless":
    print("[easy] running headless 3 frames (pass --panda for real window)")
    torsion.run(max_frames=3, dt=1 / 60)
else:
    torsion.run()

print("[easy] done")
