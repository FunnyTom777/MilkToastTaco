import unittest


class TestTorsionImport(unittest.TestCase):
    def test_import(self):
        import torsion
        import torsion3d

        self.assertEqual(torsion.__version__, "0.1.0")
        self.assertIs(torsion, torsion3d)

    def test_math(self):
        from torsion import Vec3, Quat, Mat4, Color

        a = Vec3(1, 0, 0)
        b = Vec3(0, 1, 0)
        self.assertEqual((a + b).to_tuple(), (1, 1, 0))
        self.assertAlmostEqual(a.cross(b).z, 1.0)
        q = Quat.from_euler_deg(0, 90, 0)
        self.assertAlmostEqual(q.y, 0.707, places=2)
        c = Color.from_hex("#ff0000")
        self.assertEqual(c.r, 1.0)
        m = Mat4.translate(Vec3(1, 2, 3))
        self.assertEqual(m.m[12], 1.0)

    def test_scene(self):
        import torsion

        scene = torsion.Scene("test")
        e = scene.spawn(torsion.Mesh.cube(), position=(1, 2, 3), name="box")
        self.assertEqual(len(scene), 1)
        self.assertEqual(e.transform.position.x, 1)
        cam = torsion.PerspectiveCamera(position=(0, 5, 10))
        scene.add(cam)
        self.assertIsNotNone(scene.main_camera)
        scene.add(torsion.DirectionalLight())
        self.assertEqual(len(scene), 3)

    def test_headless_app(self):
        import torsion

        app, scene = torsion.quick_start("headless_test")
        scene.add(torsion.Ground())
        app2 = torsion.App(backend="headless")
        # run exactly 1 frame without opening window
        app2.run(scene, max_frames=1, dt=1 / 60)
        # should not raise

    def test_primitives(self):
        import torsion

        scene = torsion.Scene()
        scene.add(torsion.Cube(position=(0, 1, 0), color="#ff0000"))
        scene.add(torsion.Sphere(radius=1, color="#00ff00"))
        scene.add(torsion.Ground(size=10))
        self.assertEqual(len(scene), 3)


if __name__ == "__main__":
    unittest.main()
