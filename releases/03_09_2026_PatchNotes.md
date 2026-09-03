# Patch Notes — 03 September 2026

Release date: 2026-09-03

Summary
- Hooked up XMB dashboard as main menu via pywebview with `XMBDashboardAPI` bridge (PR #10)
- Implemented dynamic XMB menu system with `@menu_option` decorators and `get_menu_structure()` (PR #12)
- Updated XMB menu options to Game Modes / Options / Misc categories
- Co-located static assets next to `xmb.py` at `core/renderer/main_menu/static/`

Merged PRs

- PR #10 — Hook up XMB dashboard as main menu with pywebview (merged 2026-09-02) by @FunnyTom777
  - Added `XMBDashboardAPI` class in `core/renderer/main_menu/xmb.py` with methods `start_game`, `load_player`, `get_game_status`, `quit_game` (later evolved to career/sandbox/military etc.).
  - Created `main.py` entry point that initializes pywebview window, exposes `js_api=api`, and loads `milk_toast_taco_xmb.html`.
  - Added `pywebview>=5` to `pyproject.toml` optional dependencies and `milk-toast-taco` CLI entry point.
  - Added `handleMenuSelection()` in XMB HTML to call Python via `pywebview.api.*`.
  - Link: https://github.com/FunnyTom777/MilkToastTaco/pull/10

- PR #12 — Implement dynamic XMB menu system with decorators (merged 2026-09-02) by @FunnyTom777
  - Added `@menu_option(category_id, category_title, category_icon, item_name, description)` decorator with global `_menu_registry`.
  - Support creating new categories dynamically on-the-fly and multiple items per category.
  - Added `get_menu_structure()` API method returning `xmbData`-compatible structure.
  - Updated `static/milk_toast_taco_xmb.html` (now `core/renderer/main_menu/static/milk_toast_taco_xmb.html`) to fetch menu via `pywebview.api.get_menu_structure()` with fallback to hardcoded `fallbackXmbData`.
  - Decorated existing API methods and kept navigation/selection routing intact.
  - Link: https://github.com/FunnyTom777/MilkToastTaco/pull/12

Additional Changes (direct commits since 02_09_2026)

- `395c489` — update xmb with updated menu options (2026-09-03)
  - Replaced placeholder `overview`/`industries` categories with `game_modes` (Play Career Mode, Play Sandbox Mode, View Military Campaigns), `options` (Mod Browser, Game Options), and `misc` (Quit).
  - Extended `game_state` with `mode` field and updated `handleMenuSelection()` / fallback data in HTML to match new names/descriptions.
  - Commit: `395c4898894bb5245c8ed2a9cb8d549f9187210c`

- `3fb4616` — refactor: move static assets under core/renderer/main_menu (2026-09-03)
  - Renamed `static/milk_toast_taco_xmb.html` → `core/renderer/main_menu/static/milk_toast_taco_xmb.html` so HTML lives next to `xmb.py`.
  - Added `STATIC_DIR`, `XMB_HTML_PATH`, and `get_xmb_html_path()` in `core/renderer/main_menu/xmb.py:14`.
  - Updated `main.py:get_xmb_html_path()` to delegate to `xmb.get_xmb_html_path()` and fixed error message path.
  - Annotated HTML header with new location.
  - Commit: `3fb4616f4047db07a46ca406f2b4f42dd7ffdf48`

Notes
- To run the XMB desktop app: `pip install -e ".[xmb]"` then `python main.py` or `milk-toast-taco`.
- Verify path resolution: `python -c "from core.renderer.main_menu.xmb import get_xmb_html_path; print(get_xmb_html_path())"` and `python -c "from main import get_xmb_html_path; print(get_xmb_html_path())"`.
