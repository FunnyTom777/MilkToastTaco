from direct.gui.OnscreenText import OnscreenText
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    AmbientLight,
    DirectionalLight,
    Material,
    NodePath,
    Vec4,
)


class SpinningCubeApp(ShowBase):
    def __init__(self):
        super().__init__()

        # Optional: Set background color to dark gray
        self.win.setClearColor(Vec4(0.1, 0.1, 0.1, 1))

        # Position the camera so the cube is in clear view
        self.disableMouse()  # Disable default mouse camera control
        self.camera.setPos(0, -7, 2)
        self.camera.lookAt(0, 0, 0)

        # -------------------------------------------------------------
        # 1. Load the Cube Model
        # -------------------------------------------------------------
        # Panda3D includes basic built-in primitive models (like 'models/box')
        self.cube = self.loader.loadModel("models/box")
        self.cube.reparentTo(self.render)

        # Center the pivot point (built-in box model origin is at one corner)
        self.cube.setPos(-0.5, -0.5, -0.5)

        # Create a parent node so we can spin around the true center cleanly
        self.cube_pivot = NodePath("cube_pivot")
        self.cube_pivot.reparentTo(self.render)
        self.cube.reparentTo(self.cube_pivot)

        # -------------------------------------------------------------
        # 2. Material Setup (for realistic light reflection)
        # -------------------------------------------------------------
        material = Material()
        material.setDiffuse(Vec4(0.2, 0.6, 1.0, 1))  # Cyan/blue tint
        material.setSpecular(Vec4(1, 1, 1, 1))  # White shiny highlights
        material.setShininess(32.0)  # Glossiness strength
        self.cube.setMaterial(material)

        # -------------------------------------------------------------
        # 3. Lighting Setup
        # -------------------------------------------------------------
        # Ambient light (soft fill light so dark sides aren't pitch black)
        ambient_light = AmbientLight("ambient_light")
        ambient_light.setColor(Vec4(0.15, 0.15, 0.2, 1))
        ambient_np = self.render.attachNewNode(ambient_light)
        self.render.setLight(ambient_np)

        # Directional light (main sun-like light source)
        dir_light = DirectionalLight("dir_light")
        dir_light.setColor(Vec4(0.9, 0.9, 0.8, 1))
        dir_np = self.render.attachNewNode(dir_light)
        # Point the light downward and toward the cube
        dir_np.setHpr(45, -45, 0)
        self.render.setLight(dir_np)

        # -------------------------------------------------------------
        # 4. Spin Animation Task
        # -------------------------------------------------------------
        # Add a recurring task to rotate the cube every frame
        self.taskMgr.add(self.spin_cube_task, "SpinCubeTask")

        # Overlay text
        OnscreenText(
            text="Panda3D - Spinning Illuminated Cube",
            pos=(0, 0.85),
            scale=0.07,
            fg=(1, 1, 1, 1),
        )

    def spin_cube_task(self, task):
        # Rotate speed: degrees per second
        degrees_per_second = 50.0

        # task.time gives elapsed seconds since app start
        angle = task.time * degrees_per_second

        # Rotate around Heading (Z), Pitch (Y), and Roll (X)
        self.cube_pivot.setHpr(angle, angle * 0.5, 0)

        return task.cont  # Continue task next frame


if __name__ == "__main__":
    app = SpinningCubeApp()
    app.run()
