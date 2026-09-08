"""
torsion.transform — Transform component (position / rotation / scale).

MTT sugar:
    t = Transform(position=(0,1,0), rotation=(0,45,0), scale=(1,1,1))
    t.translate(Vec3(1,0,0))
    t.look_at(Vec3(0,0,0))
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .math import Vec3, Quat, Mat4


@dataclass
class Transform:
    position: Vec3 = field(default_factory=Vec3.zero)
    rotation: Quat = field(default_factory=Quat.identity)
    scale: Vec3 = field(default_factory=Vec3.one)

    def __init__(
        self,
        position: Vec3 | tuple[float, float, float] | None = None,
        rotation: Quat | tuple[float, float, float] | None = None,
        scale: Vec3 | tuple[float, float, float] | None = None,
    ):
        # Normalize inputs — accept tuples for DX
        if position is None:
            self.position = Vec3.zero()
        elif isinstance(position, Vec3):
            self.position = position
        else:
            self.position = Vec3(*position)

        if rotation is None:
            self.rotation = Quat.identity()
        elif isinstance(rotation, Quat):
            self.rotation = rotation
        else:
            # tuple = euler degrees
            self.rotation = Quat.from_euler_deg(*rotation)

        if scale is None:
            self.scale = Vec3.one()
        elif isinstance(scale, Vec3):
            self.scale = scale
        else:
            self.scale = Vec3(*scale)

    # -- helpers --
    def translate(self, delta: Vec3 | tuple) -> None:
        if not isinstance(delta, Vec3):
            delta = Vec3(*delta)
        self.position = self.position + delta

    def set_euler_deg(self, x: float, y: float, z: float) -> None:
        self.rotation = Quat.from_euler_deg(x, y, z)

    def rotate_axis_angle(self, axis: Vec3, angle_deg: float) -> None:
        q = Quat.from_axis_angle(axis, angle_deg)
        self.rotation = (q * self.rotation).normalized()

    def look_at(self, target: Vec3, up: Vec3 | None = None) -> None:
        """Simple yaw-only look_at for now (good enough for prototyping)."""
        if up is None:
            up = Vec3.up()
        dir_ = (target - self.position).normalized()
        if dir_.length_squared() == 0:
            return
        yaw = math.degrees(math.atan2(dir_.x, -dir_.z))
        pitch = math.degrees(math.asin(max(-1, min(1, dir_.y))))
        self.rotation = Quat.from_euler_deg(pitch, yaw, 0)

    def to_matrix(self) -> Mat4:
        t = Mat4.translate(self.position)
        r = Mat4.from_quat(self.rotation)
        s = Mat4.scale(self.scale)
        return t @ r @ s

    def copy(self) -> Transform:
        return Transform(
            position=Vec3(self.position.x, self.position.y, self.position.z),
            rotation=Quat(self.rotation.x, self.rotation.y, self.rotation.z, self.rotation.w),
            scale=Vec3(self.scale.x, self.scale.y, self.scale.z),
        )

    def __repr__(self) -> str:
        return f"Transform(pos={self.position}, rot={self.rotation}, scale={self.scale})"
