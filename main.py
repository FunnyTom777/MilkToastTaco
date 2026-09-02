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
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.absolute()
    html_path = script_dir / "static" / "milk_toast_taco_xmb.html"
    
    if not html_path.exists():
        raise FileNotFoundError(
            f"XMB HTML dashboard not found at {html_path}\n"
            f"Please ensure static/milk_toast_taco_xmb.html exists."
        )
    
    return str(html_path)


def run():
    """Initialize and run the Milk Toast Taco XMB application."""
    try:
        # Get the path to the XMB HTML dashboard
        html_path = get_xmb_html_path()
        
        # Create the API instance
        api = XMBDashboardAPI()
        
        # Create and show the pywebview window
        webview.create_window(
            title="Milk Toast Taco",
            url=f"file://{html_path}",
            js_api=api,
            min_size=(1200, 800),
        )
        
        # Start the webview event loop
        webview.start(debug=True)
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error starting Milk Toast Taco: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    run()
