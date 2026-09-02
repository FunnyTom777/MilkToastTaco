# Patch Notes — 02 September 2026

Release date: 2026-09-02

Summary
- Added multi-player support via player_manager refactor (PR #4)
- Cleaned README to remove premature technical/hardware specs (PR #2)
- Added XML loading system + Documentation for it. ([#6](https://github.com/FunnyTom777/MilkToastTaco/issues/6))

Merged PRs

- PR #4 — Refactor player_manager to support multiple players (merged 2026-09-01) by @FunnyTom777
  - Replaced single hardcoded player storage with dict-backed storage.
  - Added API: add_player(player_id, pos), update_player_pos(player_id, pos), get_player_pos(player_id), remove_player(player_id).
  - Kept compatibility for player 1 and added unit tests (tests/test_player_manager.py).
  - More robust error handling for missing players.
  - Link: https://github.com/FunnyTom777/MilkToastTaco/pull/4

- PR #2 — Fix technical issues in README (merged 2026-09-01) by @FunnyTom777
  - Removed inaccurate hardware and resolution requirements and overly specific rendering targets.
  - Replaced with a flexible rendering configuration statement to avoid premature commitments.
  - Link: https://github.com/FunnyTom777/MilkToastTaco/pull/2

Notes
- Unit tests were added for the player_manager changes; run the test suite locally to validate.
