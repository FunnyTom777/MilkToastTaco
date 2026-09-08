"""
torsion.math — pure-Python math primitives (no dependencies).

Designed to be easy for MTT gameplay code:
    from torsion import Vec3
    pos = Vec3(0, 1, 0) + Vec3(1, 0, 0)

All types are mutable-ish dataclasses with operator overloads.
Panda3D interop helpers (to_panda / from_panda) are optional.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


# ------------------------------------------------------------------ Vec2
@dataclass(slots=True)
class Vec2:
    x: float = 0.0
    y: float = 0.0

    def __post_init__(self):
        self.x = float(self.x)
        self.y = float(self.y)

    # -- operators --
    def __add__(self, other: Vec2) -> Vec2:
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vec2) -> Vec2:
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, s: float) -> Vec2:
        return Vec2(self.x * s, self.y * s)

    __rmul__ = __mul__

    def __truediv__(self, s: float) -> Vec2:
        return Vec2(self.x / s, self.y / s)

    def dot(self, other: Vec2) -> float:
        return self.x * other.x + self.y * other.y

    def length(self) -> float:
        return math.hypot(self.x, self.y)

    def normalized(self) -> Vec2:
        l = self.length()
        return Vec2(self.x / l, self.y / l) if l else Vec2()

    def to_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)

    def __iter__(self):
        yield self.x
        yield self.y

    def __repr__(self) -> str:
        return f"Vec2({self.x:.3f}, {self.y:.3f})"


# ------------------------------------------------------------------ Vec3
@dataclass(slots=True)
class Vec3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __post_init__(self):
        self.x = float(self.x)
        self.y = float(self.y)
        self.z = float(self.z)

    # -- factories --
    @staticmethod
    def zero() -> Vec3:
        return Vec3(0, 0, 0)

    @staticmethod
    def one() -> Vec3:
        return Vec3(1, 1, 1)

    @staticmethod
    def up() -> Vec3:
        return Vec3(0, 1, 0)

    @staticmethod
    def forward() -> Vec3:
        return Vec3(0, 0, -1)

    @staticmethod
    def right() -> Vec3:
        return Vec3(1, 0, 0)

    # -- operators --
    def __add__(self, other: Vec3) -> Vec3:
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vec3) -> Vec3:
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, s: float) -> Vec3:
        if isinstance(s, Vec3):
            return Vec3(self.x * s.x, self.y * s.y, self.z * s.z)
        return Vec3(self.x * s, self.y * s, self.z * s)

    __rmul__ = __mul__

    def __truediv__(self, s: float) -> Vec3:
        return Vec3(self.x / s, self.y / s, self.z / s)

    def __neg__(self) -> Vec3:
        return Vec3(-self.x, -self.y, -self.z)

    # -- vector ops --
    def dot(self, other: Vec3) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vec3) -> Vec3:
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def length_squared(self) -> float:
        return self.x * self.x + self.y * self.y + self.z * self.z

    def normalized(self) -> Vec3:
        l = self.length()
        return Vec3(self.x / l, self.y / l, self.z / l) if l else Vec3()

    def distance_to(self, other: Vec3) -> float:
        return (self - other).length()

    def lerp(self, other: Vec3, t: float) -> Vec3:
        return Vec3(
            self.x + (other.x - self.x) * t,
            self.y + (other.y - self.y) * t,
            self.z + (other.z - self.z) * t,
        )

    def to_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def to_list(self) -> list[float]:
        return [self.x, self.y, self.z]

    def __iter__(self):
        yield self.x
        yield self.y
        yield self.z

    def __repr__(self) -> str:
        return f"Vec3({self.x:.3f}, {self.y:.3f}, {self.z:.3f})"


# ------------------------------------------------------------------ Vec4
@dataclass(slots=True)
class Vec4:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    w: float = 0.0

    def __post_init__(self):
        self.x = float(self.x)
        self.y = float(self.y)
        self.z = float(self.z)
        self.w = float(self.w)

    def to_tuple(self) -> tuple[float, float, float, float]:
        return (self.x, self.y, self.z, self.w)

    def __iter__(self):
        yield self.x
        yield self.y
        yield self.z
        yield self.w

    def __repr__(self) -> str:
        return f"Vec4({self.x:.3f}, {self.y:.3f}, {self.z:.3f}, {self.w:.3f})"


# ------------------------------------------------------------------ Color
@dataclass(slots=True)
class Color:
    r: float = 1.0
    g: float = 1.0
    b: float = 1.0
    a: float = 1.0

    def __post_init__(self):
        self.r = float(self.r)
        self.g = float(self.g)
        self.b = float(self.b)
        self.a = float(self.a)

    @staticmethod
    def from_hex(hex_str: str) -> Color:
        h = hex_str.lstrip("#")
        if len(h) == 6:
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return Color(r / 255, g / 255, b / 255, 1.0)
        if len(h) == 8:
            r, g, b, a = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(h[6:8], 16)
            return Color(r / 255, g / 255, b / 255, a / 255)
        raise ValueError(f"Invalid hex color: {hex_str}")

    def to_tuple(self) -> tuple[float, float, float, float]:
        return (self.r, self.g, self.b, self.a)

    def to_vec4(self) -> Vec4:
        return Vec4(self.r, self.g, self.b, self.a)

    def __repr__(self) -> str:
        return f"Color({self.r:.2f}, {self.g:.2f}, {self.b:.2f}, {self.a:.2f})"


# Preset palette for quick prototyping
Color.WHITE = Color(1, 1, 1, 1)
Color.BLACK = Color(0, 0, 0, 1)
Color.RED = Color(1, 0, 0, 1)
Color.GREEN = Color(0, 1, 0, 1)
Color.BLUE = Color(0, 0, 1, 1)
Color.SKY = Color(0.53, 0.81, 0.98, 1)


# ------------------------------------------------------------------ Quat
@dataclass(slots=True)
class Quat:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    w: float = 1.0

    def __post_init__(self):
        self.x = float(self.x)
        self.y = float(self.y)
        self.z = float(self.z)
        self.w = float(self.w)

    @staticmethod
    def identity() -> Quat:
        return Quat(0, 0, 0, 1)

    @staticmethod
    def from_euler_deg(x_deg: float, y_deg: float, z_deg: float) -> Quat:
        """XYZ Euler in degrees -> quaternion (intrinsic XYZ order)."""
        rx, ry, rz = math.radians(x_deg), math.radians(y_deg), math.radians(z_deg)
        cx, sx = math.cos(rx / 2), math.sin(rx / 2)
        cy, sy = math.cos(ry / 2), math.sin(ry / 2)
        cz, sz = math.cos(rz / 2), math.sin(rz / 2)
        # XYZ order
        w = cx * cy * cz - sx * sy * sz
        x = sx * cy * cz + cx * sy * sz
        y = cx * sy * cz - sx * cy * sz
        z = cx * cy * sz + sx * sy * cz
        return Quat(x, y, z, w)

    @staticmethod
    def from_axis_angle(axis: Vec3, angle_deg: float) -> Quat:
        n = axis.normalized()
        half = math.radians(angle_deg) / 2
        s = math.sin(half)
        return Quat(n.x * s, n.y * s, n.z * s, math.cos(half))

    def normalized(self) -> Quat:
        l = math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z + self.w * self.w)
        return Quat(self.x / l, self.y / l, self.z / l, self.w / l) if l else Quat.identity()

    def __mul__(self, other: Quat) -> Quat:
        # Hamilton product
        return Quat(
            self.w * other.x + self.x * other.w + self.y * other.z - self.z * other.y,
            self.w * other.y - self.x * other.z + self.y * other.w + self.z * other.x,
            self.w * other.z + self.x * other.y - self.y * other.x + self.z * other.w,
            self.w * other.w - self.x * other.x - self.y * other.y - self.z * other.z,
        )

    def to_tuple(self) -> tuple[float, float, float, float]:
        return (self.x, self.y, self.z, self.w)

    def __repr__(self) -> str:
        return f"Quat({self.x:.3f}, {self.y:.3f}, {self.z:.3f}, {self.w:.3f})"


# ------------------------------------------------------------------ Mat4 (column-major, OpenGL style)
class Mat4:
    """Minimal 4x4 matrix for Transform -> matrix conversion."""

    def __init__(self, data: list[float] | None = None):
        if data is None:
            # identity
            self.m = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
        else:
            assert len(data) == 16
            self.m = [float(v) for v in data]

    @staticmethod
    def identity() -> Mat4:
        return Mat4()

    @staticmethod
    def translate(v: Vec3) -> Mat4:
        m = Mat4.identity()
        m.m[12], m.m[13], m.m[14] = v.x, v.y, v.z
        return m

    @staticmethod
    def scale(v: Vec3) -> Mat4:
        m = Mat4.identity()
        m.m[0], m.m[5], m.m[10] = v.x, v.y, v.z
        return m

    @staticmethod
    def from_quat(q: Quat) -> Mat4:
        x, y, z, w = q.x, q.y, q.z, q.w
        xx, yy, zz = x * x, y * y, z * z
        xy, xz, yz = x * y, x * z, y * z
        wx, wy, wz = w * x, w * y, w * z
        return Mat4([
            1 - 2 * (yy + zz), 2 * (xy + wz), 2 * (xz - wy), 0,
            2 * (xy - wz), 1 - 2 * (xx + zz), 2 * (yz + wx), 0,
            2 * (xz + wy), 2 * (yz - wx), 1 - 2 * (xx + yy), 0,
            0, 0, 0, 1,
        ])

    def __matmul__(self, other: Mat4) -> Mat4:
        # column-major multiply: self @ other
        a, b = self.m, other.m
        r = [0.0] * 16
        for row in range(4):
            for col in range(4):
                s = 0.0
                for k in range(4):
                    s += a[k * 4 + row] * b[col * 4 + k]
                r[col * 4 + row] = s
        return Mat4(r)

    def to_list(self) -> list[float]:
        return list(self.m)

    def __repr__(self) -> str:
        rows = []
        for row in range(4):
            rows.append(f"[{self.m[0*4+row]:.2f} {self.m[1*4+row]:.2f} {self.m[2*4+row]:.2f} {self.m[3*4+row]:.2f}]")
        return "Mat4(\n  " + "\n  ".join(rows) + "\n)"
