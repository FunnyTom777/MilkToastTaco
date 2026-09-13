# Patch Notes — 13 September 2026

Release date: 2026-09-13

Summary
- Big catch-up release covering ~100 direct commits since 03_09_2026 (444 files changed, ~34k insertions).
- No PRs merged in this window — direct commits only. Repo now carries a "No Pull Requests at this time" notice in `README.md`.
- Dashboard evolution: V2 overhaul (bank / economy / real estate / vehicle shop / game-time UI) + V3/V4 prototypes + new V5 with command prompt.
- ASCII renderer overhaul: sprite mode, zoom config, new tiles/biomes (dense forest, mesa/badlands), minimap, fog-of-war, controller support, LAN multiplayer with UDP room scan, nametags, colored sprites + bugfixes.
- New core systems: central `state.py`, `police.py`, player ownership, game-time manager with sleep/timescales, command registry with autodetect, universal output bus, inventory/save managers.
- New MTT Launcher (`Launcher/launcher.py` + `main.py` auto-install deps, settings + recent-updates-from-GitHub menu).
- XMB overhaul: sub-menus, Settings/Config overhaul, Dev Mode toggle, local icons (no CDN).
- Engine experiments: Torsion3D foundation laid then deprecated for now, Panda3D render test.
- DevEx: `test_all.py` + `scan_reports/`, `tools/new_feature.py` + `FEATURE_IDEAS.md`.
- New static `website/` (Milk Toast Taco site), new `data/jobs.xml`, docs (`docs/INSTALL_GUIDE.md`, `docs/TEST_ALL_GUIDE.md`), README rewrite with install guide / roadmap / story art.

Merged PRs
- None in this window. All changes are direct commits (see below). Previous patchnote baseline was `3fb4616` (refactor: move static assets under core/renderer/main_menu).

Changes (direct commits since 03_09_2026)

- Dashboard / Economy (`08e4f77`, `fabe685`, `71797f7`, `5670fd9`, `93900d4`, `007bb4c`, `eaafac7`, `cbaaa05`, `b66d179`, `c6e0e11`, `5ea349b`, `1c57982`, `dfddaaa`, `bc128bb`, `bb8d36b`, `e47103b`, `427dda3`, `805a4f5`, `78df46d`, `0331d47`, `6bbe0e1`)
  - Created Dashboard V2 (`08e4f77`), later V3/V4 prototypes (`dfddaaa`), removed buggy V4 (`bc128bb`), prototyped PyQT6 V4 (`bb8d36b`, `427dda3`), stripped custom styling (`805a4f5`), created Dashboard V5 + command prompt (`6bbe0e1`, `0331d47` in `core/renderer/dashboard_v5/`).
  - Command registry + autodetect fixes (`fabe685`, `71797f7`), attribute autocomplete/builder (`5670fd9`), universal output bus `output.py` (`fa4f5f2`).
  - Economy to Dashboard + `Bank.py` payment on purchase (`93900d4`), vehicle shop system `core/systems/shop/vehicle_shop.py` (`007bb4c`), real-estate system `core/systems/realestate/realestate.py` (~1400 lines, `eaafac7`), payment-menu z-index fix (`351e217`), bigger real-estate cards (`1c57982`).
  - Bank membership system + friendlier UI + landing page (`cbaaa05`), fake-cards-with-0-memberships fix (`b66d179`), join-confirm dialog (`c6e0e11`), money-transfer UI + card-to-card transfers + auto-loan (`5ea349b`).
  - Local icons (drop CDN): icon pack locally (`e81f633`), Dashboard V2 local icons (`d1b93f3`), XMB local icons (`34d045b`, `core/renderer/main_menu/static/local-icons.js`).
  - Time/sleep display in Dashboard V2 (`78df46d`).

- Game Time (`ada45ad`, `4ea665b`)
  - Implemented Game Time system `core/systems/gametime/manager.py` (~1000 lines, `ada45ad`).
  - Added Sleep + Timescales (`4ea665b`).

- Player / Ownership / State / Police / Wallet (`f443bbf`, `4547fb3`, `8a50a27`)
  - Player Ownership system `core/systems/player/ownership.py` (`f443bbf`).
  - Central state manager `core/systems/state.py` + new Police system `core/systems/police/police.py` (`4547fb3`).
  - Migrated `wallet.py` + `police.py` to central `state.py` (`8a50a27`).

- Phone / Orchestrator (`df71835`, `2a6c03f`)
  - Basic phone system placeholder `core/systems/phone/` (`df71835`).
  - `thisdoesnothing()` marker in `orchestrator.py` + expanded phone + phone-apps system (`2a6c03f`).

- Inventory / Save (`core/systems/inventory/`, `core/systems/save/`, `core/tests/test_inventory.py`, `core/tests/test_save_manager.py`)
  - Inventory loader/manager + tests, save manager/registry/xml_codec + tests (new in this window, see diff vs `3fb4616`).

- ASCII Renderer (`03c5522`, `a54371c`, `91730b3`, `e3cb64f`, `3ec32f0`, `c73fde9`, `3d268ea`, `efffa7b`, `3f70718`, `a6bcc8b`, `9e8ac4f`, `a565247`, `44fa7e5`, `e965624`, `4e45281`, `c1c75c8`, `017145f`, `1af2633`, `8975505`, `d060f54`, `f4def08`, `2f2ee6e`, `3314934`, `3f8a2bf`)
  - New ASCII renderer test (`03c5522`), generation + basic biome system (`a54371c`), sprite mode via `config.xml` + placeholder sprites + less water (`91730b3`), black-tile-under-player fix + more tile art (`e3cb64f`), tile assets update (`3ec32f0`).
  - Zoom setting in `config.xml` (`c73fde9`), dense forest tile (`3d268ea`), less-terrifying player sprite (`efffa7b`), wheat clumps to fields (`3f70718`), forest variety (`a6bcc8b`), default zoom 1.5 → 2.0 → 2.5 (`9e8ac4f`, `a565247`).
  - Minimap + new UI/controls + experimental fog-of-war (`44fa7e5`), updated fog system (`3f8a2bf`), house tile + `config.xml` (`e965624`), Merriweather-Italic font (`4e45281`).
  - Launcher now launches ASCII renderer (`017145f`), mesa/badlands biome + tile art (`d060f54`), controller support + menu navigation (`8975505`).
  - Multiplayer: LAN multiplayer with UDP broadcast room scan (`3f8a2bf`), different colored sprites (`f4def08`), sprites + nametags (`2f2ee6e`), random bugfixes (`3314934`), graceful disconnect + spawn-inside-collision fix (`1af2633`).

- XMB / Main Menu (`8293080`, `215712a`, `xmb.py`, `core/renderer/main_menu/xmb.py`, `core/renderer/main_menu/xmb_settings.py`)
  - Major XMB overhaul: sub-menus for Dashboard, overhauled Settings/Config, Dev Mode toggle (`8293080`).
  - Moved XMB from `main.py` to `xmb.py` so `main.py` can change (`215712a`).

- Launcher / Entry Point (`2e19e65`, `9fac891`, `a961d61`, `4e26791`, `c6c53f8`, `f2946f4`, `75951e4`, `9fab4bf`)
  - New central MTT Launcher `Launcher/launcher.py` (`2e19e65`), settings + recent-updates menu fetching commits from GitHub (`9fac891`), `install_new_update()` placeholder (`4e26791`), launcher updates (`a961d61`), launcher work + regenerated `requirements.txt` (`c6c53f8`), `Main.py` updates (`f2946f4`), launcher actually launches Dashboard V2 (`75951e4`).
  - `main.py` now auto-installs required libraries (`9fab4bf`, +415 lines vs baseline).

- Engine / 3D experiments (`75d1723`, `bb64348`, `cd64d88`, `bf2553c`, `8c6029f`, `c1c75c8`)
  - Torsion3D foundation (`75d1723`), plan (`bb64348`), basic functions (`cd64d88`), easy-to-use functions (`torsion/easy.py`, `bf2553c`), then deprecated for now (`8c6029f` in `engine/Torsion/torsion_engine.md`).
  - Panda3D 3D rendering test (`c1c75c8`).

- DevEx / Tools (`7754069`, `b8669f7`, `3bc1b09`, `01c90cc`)
  - `test_all.py` repo-wide scanner + `scan_reports/` (`7754069`, see `docs/TEST_ALL_GUIDE.md`).
  - `FEATURE_IDEAS.md` + `tools/new_feature.py` feature-creation tool (`b8669f7`), new entries: Forestry/Logging, Fishing, Job/Contract, Modding Framework, Proper 3D rendering (`3bc1b09`), README link (`01c90cc`).

- Website / Data (`7346c82`, `8cfddf1`, `dd32f9c`)
  - New Milk Toast Taco website `website/` (`index.html`, `doc.html`, `styles/main.css`, `assets/js/markdown.js`, `7346c82`).
  - New `data/jobs.xml` (`8cfddf1`), update to it (`dd32f9c`). Also touched: `banks.xml`, `config.xml`, `generation.xml`, `items.xml`, `npc.xml`, `phone_apps.xml`, `properties.xml`, `realestate_agents.xml`, `vehicles.xml`.

- Docs / README (`f05aa10`, `4981f00`, `d47d9c8`, `d53b09f`, `af3a28e`, `f2be099`, `de31cec`, `4ed73ba`, `8eff575`, `9f64868`, `985b905`, `fa5f3c6`, `a76b1a9`, `docs/INSTALL_GUIDE.md`)
  - New logo (`f05aa10`), Current Progress section (`4981f00`), full rewrite to be *better* (`d47d9c8`), Discord link (`d53b09f`) / badge (`4ed73ba`) then removed (`8eff575`), install guide (`af3a28e`, `docs/INSTALL_GUIDE.md`), `python --version` tip (`f2be099`), banner image (`de31cec`), Roadmap section (`9f64868`), Story image + non-clickable images (`985b905`), No-PRs notice sign (`fa5f3c6`, `a76b1a9`).
  - Note: `d68a35f` revamped dashboard + removed dev tools, `dfb676b` removed duplicate dashboard file, `da5b39b` Bank card system + license-plate system (`core/systems/vehicles/data/license_plates.py`).

Notes
- To run: `python main.py` (launcher auto-installs deps per `9fab4bf`). Windows + Python 3.11+ per README install guide.
- To run repo-wide checks: `python test_all.py` — see `docs/TEST_ALL_GUIDE.md` and `scan_reports/`.
- Verify XMB path still resolves after `215712a`: `python -c "from core.renderer.main_menu.xmb import get_xmb_html_path; print(get_xmb_html_path())"`.
- Baseline for next notes: `dd32f9c` (Update jobs.xml, 2026-09-13).
