#!/usr/bin/env python3
"""
Milk Toast Taco - XMB Desktop Application Entry Point.

This module initializes and runs the Milk Toast Taco game using the XMB
dashboard interface with pywebview for desktop integration.
"""

import os
import sys
from pathlib import Path

try:
    import webview
except ImportError:
    print(
        "Error: pywebview is not installed.\n"
        "Install it with: pip install -e '.[xmb]'\n"
        "Or: pip install pywebview"
    )
    sys.exit(1)

from core.renderer.main_menu.xmb import XMBDashboardAPI


def get_xmb_html_path():
    """Get the absolute path to the XMB HTML dashboard.
    
    Returns:
        str: Path to milk_toast_taco_xmb.html
    """
    # HTML now lives next to xmb.py: core/renderer/main_menu/static/
    # Keep resolution via XMBDashboardAPI to avoid duplication.
    from core.renderer.main_menu.xmb import get_xmb_html_path as _get_path

    html_path = Path(_get_path())

    if not html_path.exists():
        raise FileNotFoundError(
            f"XMB HTML dashboard not found at {html_path}\n"
            f"Please ensure core/renderer/main_menu/static/milk_toast_taco_xmb.html exists."
        )
    
    return str(html_path)


def run(debug: bool | None = None):
    """Initialize and run the Milk Toast Taco XMB application.

    DevTools are now opt-in: pass --debug or set MTT_DEBUG=1.
    Previously this always used debug=True which forced Edge DevTools
    to open on every launch.
    """
    # Debug is opt-in — check explicit arg, CLI flag, and env var
    if debug is None:
        debug = "--debug" in sys.argv or os.environ.get("MTT_DEBUG") == "1"
    else:
        debug = bool(debug)

    try:
        # Get the path to the XMB HTML dashboard
        html_path = get_xmb_html_path()
        
        # Create the API instance
        api = XMBDashboardAPI()

        # Load XMB settings for fullscreen preference
        try:
            from core.renderer.main_menu.xmb_settings import load_settings
            _xmb_settings = load_settings()
            _fullscreen = bool(_xmb_settings.get("fullscreen", False))
        except Exception:
            _fullscreen = False
        
        # Create and show the pywebview window
        webview.create_window(
            title="Milk Toast Taco",
            url=f"file://{html_path}",
            js_api=api,
            min_size=(1200, 800),
            fullscreen=_fullscreen,
        )
        
        # Start the webview event loop (debug=False hides Edge DevTools)
        webview.start(debug=debug)
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error starting Milk Toast Taco: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    import argparse

    _p = argparse.ArgumentParser(description="Milk Toast Taco — XMB (Edge DevTools hidden unless --debug)")
    _p.add_argument("--debug", action="store_true", help="Enable pywebview debug / Edge DevTools")
    _args = _p.parse_args()
    run(debug=_args.debug)
