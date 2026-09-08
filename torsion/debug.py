"""
torsion.debug — DearPyGui debug overlay (lazy).

Plan per torsion_engine.md:
  - Panda3D for rendering (done via renderer.py)
  - DearPyGUI for debug/tool UI (here)

This module is intentionally lazy — `import torsion` never requires dearpygui.
When available it exposes a tiny overlay API MTT can call from App.on_update.

    from torsion.debug import DebugOverlay
    dbg = DebugOverlay()
    dbg.text("fps", f"{1/dt:.1f}")
    dbg.show()  # opens DPG window if installed, else logs

If dearpygui is not installed, all calls are no-ops with a console fallback.
"""

from __future__ import annotations

from typing import Any


def is_available() -> bool:
    try:
        import importlib.util

        return importlib.util.find_spec("dearpygui") is not None
    except Exception:
        return False


class DebugOverlay:
    """Minimal key/value overlay. Swap to real DPG later."""

    def __init__(self, title: str = "Torsion Debug"):
        self.title = title
        self._fields: dict[str, Any] = {}
        self._dpg = None
        self._enabled = False

    def text(self, key: str, value: Any) -> None:
        self._fields[str(key)] = value

    def clear(self) -> None:
        self._fields.clear()

    def show(self) -> None:
        if not is_available():
            # fallback: log once
            if self._fields:
                print(f"[Torsion:debug] {self.title} — dearpygui not installed, fields={self._fields}")
            return
        # lazy import
        try:
            import dearpygui.dearpygui as dpg  # type: ignore

            if not self._enabled:
                dpg.create_context()
                dpg.create_viewport(title=self.title, width=400, height=300)
                with dpg.window(label=self.title):
                    for k, v in self._fields.items():
                        dpg.add_text(f"{k}: {v}", tag=f"dbg_{k}")
                dpg.setup_dearpygui()
                dpg.show_viewport()
                self._dpg = dpg
                self._enabled = True
            else:
                for k, v in self._fields.items():
                    try:
                        self._dpg.set_value(f"dbg_{k}", f"{k}: {v}")
                    except Exception:
                        pass
            self._dpg.render_dearpygui_frame()
        except Exception as e:
            print(f"[Torsion:debug] failed to show overlay: {e}")

    def hide(self) -> None:
        if self._dpg is not None:
            try:
                self._dpg.destroy_context()
            except Exception:
                pass
        self._enabled = False
        self._dpg = None
