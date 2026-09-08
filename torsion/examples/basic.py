"""
torsion.examples.basic — minimal Torsion3D demo.

Run with:
    python -m torsion.examples.basic
    python torsion/examples/basic.py

No Panda3D required — runs headless and prints scene info.
With Panda3D installed, opens a real window (TORSION_BACKEND=panda3d).
"""

import torsion
from torsion import Vec3, Color


def main():
    print(f"Torsion {torsion.__version__} — backend={torsion.get_backend()}")

    app = torsion.App(title="MTT — Torsion3D Demo", width=1280, height=720)
    scene = torsion.Scene(name="demo")

    # ground
    scene.add(torsion.Ground(size=30, color="#3a7d44"))

    # a few cubes — stand-ins for MTT vehicles/buildings
    for i in range(3):
        cube = torsion.Mesh.cube(size=1, material=torsion.Material.albedo(Color.from_hex("#cc4444")))
        scene.spawn(cube, name=f"crate_{i}", position=Vec3(i * 2 - 2, 0.5, 0))

    # lights
    scene.add(torsion.DirectionalLight(direction=Vec3(-0.5, -1, -0.3), intensity=1.2))
    scene.set_ambient("#ffffff", 0.35)

    # camera
    cam = torsion.PerspectiveCamera(fov=75, position=Vec3(6, 5, 8))
    cam.look_at(Vec3(0, 0, 0))
    scene.add(cam, name="main_cam")

    print(f"Scene: {scene} — main_camera={scene.main_camera}")

    # headless demo runs 3 frames then exits; real Panda window runs until closed
    backend = torsion.get_backend()
    if backend.value == "headless":
        print("Running headless (3 frames) — install Panda3D for a real window:")
        print("    pip install panda3d")
        app.run(scene, max_frames=3, dt=1 / 60)
    else:
        app.run(scene)


if __name__ == "__main__":
    main()
