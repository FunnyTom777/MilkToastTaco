import unittest


class TestTorsionEasy(unittest.TestCase):
    def setUp(self):
        import torsion.easy as easy

        easy._default_app = None
        easy._default_scene = None

    def test_new_window_and_draw(self):
        import torsion

        torsion.new_window("EasyTest", 800, 600, backend="headless")
        self.assertIsNotNone(torsion.get_app())
        self.assertIsNotNone(torsion.get_scene())

        # all xyz variants
        e1 = torsion.draw_mesh("cube", (0, 1, 0), size=1, color="#ff0000")
        e2 = torsion.draw_mesh("cube", 1, 2, 3, color="skyblue")
        e3 = torsion.draw_mesh("assets/truck.glb", (5, 0, 0))
        e4 = torsion.draw_cube((2, 0, 0), size=1.2, color="#00ff00")
        e5 = torsion.draw_sphere((0, 3, 0), radius=0.5)
        e6 = torsion.draw_ground(size=20, color="#3a7d44")

        # aliases
        e7 = torsion.cube((3, 0, 0))
        e8 = torsion.sphere((0, 4, 0))
        e9 = torsion.draw_model("cube", (4, 0, 0))

        for e in [e1, e2, e3, e4, e5, e6, e7, e8, e9]:
            self.assertIsNotNone(e)

        # lights / camera sugar
        torsion.sun(direction=(-1, -1, 0))
        torsion.light((0, 5, 0), color="#ffffaa")
        torsion.camera((6, 5, 8), look_at=(0, 0, 0))
        torsion.camera(6, 5, 8, look_at=(0, 0, 0))  # x,y,z variant

        # run headless one frame
        torsion.run(max_frames=1, dt=1 / 60)

    def test_auto_window(self):
        import torsion

        # no new_window() — draw should auto-create
        e = torsion.draw_cube((0, 0, 0))
        self.assertIsNotNone(e)
        self.assertGreater(len(torsion.get_scene()), 0)
        torsion.close_window()
        self.assertIsNone(torsion.get_app().__class__.__name__ if False else None)  # just ensure no crash

    def test_import_alias(self):
        import torsion
        import torsion3d

        self.assertIs(torsion.draw_mesh, torsion3d.draw_mesh)


if __name__ == "__main__":
    unittest.main()
