"""
torsion.camera — Camera components.

    cam = PerspectiveCamera(fov=75, near=0.1, far=1000, position=(0,5,10))
    cam.look_at(Vec3(0,0,0))
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .math import Vec3, Quat
from .transform import Transform


@dataclass
class Camera:
    transform: Transform = field(default_factory=Transform)
    near: float = 0.1
    far: float = 1000.0
    # Filled by Scene.add() — not set manually
    _entity_id: int | None = field(default=None, repr=False)

    def look_at(self, target: Vec3 | tuple, up: Vec3 | None = None) -> None:
        if not isinstance(target, Vec3):
            target = Vec3(*target)
        self.transform.look_at(target, up or Vec3.up())

    @property
    def position(self) -> Vec3:
        return self.transform.position

    @position.setter
    def position(self, v: Vec3 | tuple) -> None:
        self.transform.position = v if isinstance(v, Vec3) else Vec3(*v)


@dataclass
class PerspectiveCamera(Camera):
    fov: float = 75.0  # vertical degrees
    aspect: float = 16 / 9

    def __init__(
        self,
        fov: float = 75.0,
        aspect: float = 16 / 9,
        near: float = 0.1,
        far: float = 1000.0,
        position: Vec3 | tuple | None = None,
        rotation: Quat | tuple | None = None,
    ):
        super().__init__(transform=Transform(position=position, rotation=rotation), near=near, far=far)
        self.fov = float(fov)
        self.aspect = float(aspect)

    def __repr__(self) -> str:
        return f"PerspectiveCamera(fov={self.fov}, aspect={self.aspect:.2f}, pos={self.position})"


@dataclass
class OrthographicCamera(Camera):
    left: float = -10
    right: float = 10
    bottom: float = -10
    top: float = 10

    def __init__(
        self,
        left: float = -10,
        right: float = 10,
        bottom: float = -10,
        top: float = 10,
        near: float = 0.1,
        far: float = 1000.0,
        position: Vec3 | tuple | None = None,
    ):
        super().__init__(transform=Transform(position=position), near=near, far=far)
        self.left = float(left)
        self.right = float(right)
        self.bottom = float(bottom)
        self.top = float(top)

    def __repr__(self) -> str:
        return f"OrthographicCamera(l={self.left}, r={self.right}, pos={self.position})"
