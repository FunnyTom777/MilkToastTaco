"""
Gametime package — re-exports manager API for convenience.

    from core.systems.gametime import get_datetime, advance_minutes
    from core.systems.gametime.manager import get_datetime
"""

from core.systems.gametime.manager import *  # noqa: F401,F403
