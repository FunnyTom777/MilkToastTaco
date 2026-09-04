"""Project-root shim for the universal output bus.
Canonical implementation: core/output.py
Allows `import output` or `from output import print_to_user`.
"""
from core.output import *  # noqa: F403,F401
from core.output import (
    emit,
    print_to_user,
    info,
    success,
    warning,
    error,
    debug,
    system,
    get_messages,
    get_output,
    poll_output,
    clear,
    subscribe,
    unsubscribe,
)
__all__ = [
    "emit","print_to_user","info","success","warning","error","debug","system",
    "get_messages","get_output","poll_output","clear","subscribe","unsubscribe",
]
