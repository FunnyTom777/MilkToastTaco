"""
engine.torsion_bridge — convenience re-export.

Allows legacy imports:
    from engine import torsion
    import engine.torsion_bridge as torsion

Canonical import remains:
    import torsion
    import torsion3d
"""

try:
    import torsion as _torsion  # noqa: F401
except ImportError:
    _torsion = None
