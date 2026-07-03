# Pass 0 — Ground Truth Recon Evidence Packet

Date: 2026-07-01. Role: non-judgmental fact gathering for a multi-pass review of Local Agent Town.
All commands were run in the Linux sandbox at `/sessions/tender-affectionate-pasteur/mnt/local-agent-town`
(same tree as `E:\GPTCode\local-agent-town`). Facts only; no opinions or severity labels.

## 1. Git state

Command: `git rev-parse HEAD && git status --short` and `git log --oneline -20`.

HEAD:

```
65eed44d2abaad631e4da593c8d12f93b283bd24
```

`git status --short` (verbatim):

```
 M .gitignore
 M AGENTS.md
 M BLUEPRINT.md
 M Local_little_world_refactor1.md
 M README.md
 M ROADMAP.md
 M RUNBOOK.md
 M VISUAL_DESIGN.md
 M docs/run_reports/2026-06-30-pr23-mac-lm-gate.md
 M docs/run_reports/2026-07-01-pr34-mac-lm-gate.md
 M pyproject.toml
 M research_papers/1.rimworld_mood-system-report.md
 M research_papers/2.rimworld_hunger-system-report.md
 M research_papers/3.rimworld_autonomous-pawn-report.md
 M research_papers/4.townsmen_economy-loop-report.md
 M research_papers/5.aoe_civ-readability-report.md
 M research_papers/6.ui-report.md
 M research_papers/7.scalable-sim-report.md
 M research_papers/8.little-local-world-research-synthesis.md
 M scripts/analyze_run.py
 M scripts/benchmark_scaling.py
 M scripts/llm_governor_run.py
 M scripts/prepare-kenney-assets.ps1
 M src/agent_town/__init__.py
 M src/agent_town/__main__.py
 M src/agent_town/assets/__init__.py
 M src/agent_town/assets/colony/README.md
 M src/agent_town/assets/kenney/README.md
 M src/agent_town/buildings.py
 M src/agent_town/civilization.py
 M src/agent_town/civilization_view.py
 M src/agent_town/construction.py
 M src/agent_town/core.py
 M src/agent_town/economy.py
 M src/agent_town/engine.py
 M src/agent_town/governor.py
 M src/agent_town/health.py
 M src/agent_town/llm.py
 M src/agent_town/mood.py
 M src/agent_town/pawns.py
 M src/agent_town/schedule.py
 M src/agent_town/telemetry.py
 M src/agent_town/work.py
 M src/agent_town/world.py
 M tests/test_assets.py
 M tests/test_buildings.py
 M tests/test_civ_stats.py
 M tests/test_civilization.py
 M tests/test_civilization_contract.py
 M tests/test_civilization_governor.py
 M tests/test_civilization_view.py
 M tests/test_engine.py
 M tests/test_health.py
 M tests/test_integration_i1.py
 M tests/test_llm.py
 M tests/test_llm_governor.py
 M tests/test_movement.py
 M tests/test_package_runtime.py
 M tests/test_step2_hunger_mood.py
 M tests/test_telemetry.py
 M tests/test_track_a_current_contract.py
 M tests/test_track_b_b1.py
 M tests/test_track_b_b2.py
 M tests/test_track_b_b3.py
 M tests/test_track_b_b4.py
 M tests/test_water.py
 M tests/test_work.py
?? docs/lmstudio_logs/
?? docs/reviews/
```

`git log --oneline -20` (verbatim):

```
65eed44 Add observer decision audit
f95aaf9 docs: add Mac LM gate proof for PR #34
5f56638 Verify the LLM governor path live against google/gemma-4-e4b
937e033 Slice 1: the dig-out - governor grows more food during a shortage
1b26467 Codify "watchability is part of done" in the agent harness
806b482 Make the food crisis actually visible to the watcher (Slice 0 follow-up)
abf2251 Make the starvation spiral escapable + give the governor food-sight (Slice 0)
c04649a docs: add Mac LM gate proof for PR #23
edf828e Retry malformed LLM JSON once
a04be56 docs: add Mac LM gate proof for PR #23
f6834ee Guard LLM priorities from flattening specialization
a06ddcf docs: add Mac LM gate proof for PR #23
017834e Guard LLM policy survival priorities
0bf314d docs: add Mac LM gate proof for PR #23
c4ce58a Guard LLM policy against essential shutdown
ef20415 docs: add Mac LM gate proof for PR #23
032afc7 Fix covered intermediate stall warnings
643303f docs: add Mac LM gate proof for PR #23
88715b9 Record PR 23 status gate
aecce57 Honor set_production_target in production_tick (truth-loop slice 1)
```

The tree is DIRTY (nearly every tracked source, test, script, and doc file shows `M`; `docs/lmstudio_logs/`
and `docs/reviews/` are untracked). **This review covers the WORKING TREE, with HEAD at `65eed44`.**
Note: `tests/test_dig_out.py`, `tests/test_food.py`, and `tests/test_production_target.py` exist on disk
but do not appear in `git status --short`, i.e. they are tracked and unmodified relative to HEAD.

## 2. Test suite and smoke test

Command: `pip install pygame --break-system-packages -q 2>&1 | tail -2; SDL_VIDEODRIVER=dummy PYTHONPATH=src python3 -m unittest discover -s tests 2>&1 | tail -15`

Output (verbatim, last 15 lines; leading ALSA lines are sandbox audio-device noise):

```
.ALSA lib confmisc.c:855:(parse_card) cannot find card '0'
ALSA lib conf.c:5178:(_snd_config_evaluate) function snd_func_card_inum returned error: No such file or directory
ALSA lib confmisc.c:422:(snd_func_concat) error evaluating strings
ALSA lib conf.c:5178:(_snd_config_evaluate) function snd_func_concat returned error: No such file or directory
ALSA lib confmisc.c:1334:(snd_func_refer) error evaluating name
ALSA lib conf.c:5178:(_snd_config_evaluate) function snd_func_refer returned error: No such file or directory
ALSA lib conf.c:5701:(snd_config_expand) Evaluate error: No such file or directory
ALSA lib pcm.c:2664:(snd_pcm_open_noupdate) Unknown PCM default
.....................................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 277 tests in 4.132s

OK
pygame 2.6.1 (SDL 2.28.4, Python 3.10.12)
Hello from the pygame community. https://www.pygame.org/contribute.html
```

Result: 277 tests, OK, 4.132s, Python 3.10.12 / pygame 2.6.1.

Command: `SDL_VIDEODRIVER=dummy PYTHONPATH=src python3 -m agent_town --smoke-test 2>&1 | tail -15; echo "EXIT=$?"`

Output (verbatim, last lines):

```
ALSA lib pcm.c:2664:(snd_pcm_open_noupdate) Unknown PCM default
pygame 2.6.1 (SDL 2.28.4, Python 3.10.12)
Hello from the pygame community. https://www.pygame.org/contribute.html
EXIT=0
```

(Full tail was 8 ALSA lines + the two pygame lines; nothing else printed. `EXIT=0` reflects the exit
status of the final command in the pipeline.)

## 3. Inventories

### 3a. `src/agent_town` modules (`wc -l`)

```
     6 src/agent_town/__init__.py
     4 src/agent_town/__main__.py
   122 src/agent_town/buildings.py
    94 src/agent_town/civilization.py
  2572 src/agent_town/civilization_view.py
   107 src/agent_town/construction.py
   363 src/agent_town/core.py
   222 src/agent_town/economy.py
   239 src/agent_town/engine.py
   901 src/agent_town/governor.py
   383 src/agent_town/health.py
   271 src/agent_town/llm.py
   230 src/agent_town/mood.py
   293 src/agent_town/pawns.py
   133 src/agent_town/schedule.py
   410 src/agent_town/telemetry.py
   449 src/agent_town/work.py
    84 src/agent_town/world.py
  6883 total
```

(There is also an `assets/` subpackage: `src/agent_town/assets/__init__.py` plus `assets/colony/` and
`assets/kenney/` asset directories with READMEs.)

### 3b. `tests/` (`wc -l`)

```
    30 tests/test_assets.py
    45 tests/test_buildings.py
    62 tests/test_civ_stats.py
    54 tests/test_civilization.py
   146 tests/test_civilization_contract.py
   224 tests/test_civilization_governor.py
   671 tests/test_civilization_view.py
   114 tests/test_dig_out.py
   118 tests/test_engine.py
   194 tests/test_food.py
   175 tests/test_health.py
    64 tests/test_integration_i1.py
   130 tests/test_llm.py
   265 tests/test_llm_governor.py
   112 tests/test_movement.py
    19 tests/test_package_runtime.py
   127 tests/test_production_target.py
   142 tests/test_step2_hunger_mood.py
   166 tests/test_telemetry.py
   181 tests/test_track_a_current_contract.py
   130 tests/test_track_b_b1.py
    83 tests/test_track_b_b2.py
   111 tests/test_track_b_b3.py
   151 tests/test_track_b_b4.py
    76 tests/test_water.py
   256 tests/test_work.py
  3846 total
```

26 test files, 3846 lines total.

### 3c. `docs/proof/*` and `docs/screenshots/*` (`ls -laR --time-style=long-iso`, directories/sizes/dates)

```
docs/proof:                       (dirs: governor_decision_audit, llm_verify, slice0, slice1, ui_navigation)

docs/proof/governor_decision_audit:
-rwx------ 264407 2026-07-01 04:02 crisis_20x_history.png
-rwx------ 154978 2026-07-01 04:02 history_decision_detail.png

docs/proof/llm_verify:
-rwx------ 207171 2026-07-01 02:26 live_model_food_decision_h21.png

docs/proof/slice0:
-rwx------ 205897 2026-07-01 01:17 01_healthy_day3.png
-rwx------ 208070 2026-07-01 01:17 02_lowfood_crisis_day5.png

docs/proof/slice1:
-rwx------ 204847 2026-07-01 01:44 01_planting_wheat_during_low_food.png
-rwx------ 220858 2026-07-01 01:44 02_recovered.png

docs/proof/ui_navigation:
-rwx------ 160962 2026-07-01 04:02 architect.png
-rwx------ 181373 2026-07-01 04:02 assign.png
-rwx------ 164847 2026-07-01 04:02 default.png
-rwx------ 141173 2026-07-01 04:02 history.png
-rwx------ 158679 2026-07-01 04:02 inspector_bio.png
-rwx------ 159596 2026-07-01 04:02 inspector_gear.png
-rwx------ 161428 2026-07-01 04:02 inspector_health.png
-rwx------ 163893 2026-07-01 04:02 inspector_log.png
-rwx------ 160954 2026-07-01 04:02 inspector_social.png
-rwx------ 156269 2026-07-01 04:02 menu.png
-rwx------ 151851 2026-07-01 04:02 research.png
-rwx------ 150924 2026-07-01 04:02 work.png
(12 files total in ui_navigation)

docs/screenshots:
-rwx------ 164847 2026-07-01 04:02 current-state.png
-rwx------  95687 2026-06-29 23:01 work-grid.png
```

All proof images are dated 2026-07-01 (today) except `work-grid.png` (2026-06-29).
`current-state.png` and `ui_navigation/default.png` have identical byte sizes (164847).

### 3d. ROADMAP.md Verification Log — last 10 rows (verbatim, single table rows each)

```
| 2026-06-30 03:24 -06:00 | Full Mac LM acceptance gate for PR #23 `feat/production-target-honored` at `017834e9fcf4c7ebf9cf0f3df7df69f0e80af4e7` | Fresh-worktree `python3` bootstrap first failed because macOS selected Python 3.9; reran with supported `/opt/homebrew/bin/python3.12`: `.venv/bin/python -m pip install -e .`; `.venv/bin/python -m agent_town --smoke-test`; `.venv/bin/python -m unittest discover -s tests` (231 tests); `pwsh -NoLogo -NoProfile -File scripts/validate-workbench.ps1`; LM Studio ping `http://192.168.1.131:1234/v1/models` found `google/gemma-4-e4b`; Pygame `CivilizationViewer` booted with blocking `LLMGovernor`; 96 simulated viewer hours; `.venv/bin/python scripts/analyze_run.py logs/run-20260630-031923.jsonl --events`; `.venv/bin/python scripts/benchmark_scaling.py --pawns 100 500 1000 --steps 24 --context-repeats 8 --draw-frames 3`; `git diff --check` | red | Install/smoke/unit/docs/LM ping/viewer boot/scaling passed under Python 3.12 and the model was actually used for 96/96 decisions with zero drops, applying 380 `set_work_priority` actions. Analyzer returned RED: bread depleted 4x, water and flour stalled, mood 85.8 -> min 39.4 -> end 45.75, final stockpile empty, final food and water needs 0.0. Not ready to merge; no Apple Silicon-specific failure evidence. See `docs/run_reports/2026-06-30-pr23-mac-lm-gate.md`. |
| 2026-06-30 03:34 -06:00 | Fix attempt 4 for PR #23 RED Mac LM gate on `feat/production-target-honored` (clean detached worktree based on `origin/feat/production-target-honored`; model gpt-5.5 xhigh; budget metric not readable before 04:00; `.agent.lock` acquired) | PR status read: `gh pr view 23 --json ...` -> OPEN/CLEAN with latest Mac comment `NOT READY` / RED at `a06ddcf`; `gh pr checks 23` -> no checks reported. RED `$env:PYTHONPATH=(Resolve-Path src).Path; E:\GPTCode\local-agent-town\.venv\Scripts\python.exe -m unittest tests.test_llm_governor tests.test_civilization_governor` failed on model-origin `group=all` essential priority actions and reproduced empty stockpiles after 96 hours; GREEN focused tests (30 tests); deterministic 96-hour mock model with all-town water/farming/milling/baking priorities now matches fallback (`bread=16`, `water=96`, mood 82.4, food/water needs 1.0); `E:\GPTCode\local-agent-town\.venv\Scripts\python.exe -m unittest discover -s tests` (233 tests); `E:\GPTCode\local-agent-town\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1`; `git diff --check` | pass | Decision source: Paper 3 priority model / per-pawn work settings and Paper 8 autonomy-before-deeper-economy sequencing. Root cause: model-origin `set_work_priority {group: all}` flattened the seeded town's specialization while still passing the prior "essential level 1-2" guardrail, causing the exact Mac failure (empty stockpile, food/water needs 0.0). Fix: LLM-origin work-priority actions must target named pawns; all-town priority edits now fall back to the deterministic governor. Direct/player `apply_actions` semantics are unchanged. Main `E:\` checkout still has pre-existing dirty hosted-OpenAI telemetry work and was left untouched. Next: push fix attempt 4 and rerun the Mac LM acceptance gate to confirm RED -> GREEN. |
| 2026-06-30 03:55 -06:00 | Full Mac LM acceptance gate for PR #23 `feat/production-target-honored` at `f6834eefbefcb3e0ffa148d89a60d0cf0cc25bb4` | `.venv/bin/python -m pip install -e .`; `.venv/bin/python -m agent_town --smoke-test`; `.venv/bin/python -m unittest discover -s tests` (233 tests); `pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/validate-workbench.ps1`; LM Studio ping `http://192.168.1.131:1234/v1/models` found `google/gemma-4-e4b`; Pygame `CivilizationViewer` booted with blocking `LLMGovernor`; 96 simulated viewer hours; `.venv/bin/python scripts/analyze_run.py logs/run-20260630-034953.jsonl --events`; `git diff --check` | amber | Install/smoke/unit/docs/LM ping/viewer boot passed and the current game state stayed healthy: mood 85.8 -> min 72.4 -> end 82.4, idle peak 0, breaks 0, depletions 0, stalls 0. Analyzer returned AMBER because 5/96 model decision hours emitted invalid JSON and fell back; 91/96 hours used model decisions and applied 365 `set_work_priority` actions. Not ready to merge because AMBER is not GREEN; no Apple Silicon-specific failure evidence. See `docs/run_reports/2026-06-30-pr23-mac-lm-gate.md`. |
| 2026-06-30 04:03 -06:00 | Fix attempt 5 for PR #23 AMBER Mac LM gate on `feat/production-target-honored` (clean detached worktree based on `origin/feat/production-target-honored`; model scheduled gpt-5.5 xhigh; after 04:00 budget metric/safe in-run switch not readable, kept smallest safe slice; `.agent.lock` acquired in `E:\GPTCode\local-agent-town`) | PR status read: `gh pr view 23 --json ...` -> OPEN/CLEAN with latest Mac comment `NOT READY` / AMBER at `a04be56`; `gh pr checks` signal absent. RED `$env:PYTHONPATH=(Resolve-Path src).Path; E:\GPTCode\local-agent-town\.venv\Scripts\python.exe -m unittest tests.test_llm.LocalLLMClientTests.test_complete_json_retries_once_after_malformed_json` failed because malformed model content raised immediately; GREEN `tests.test_llm` (8 tests); GREEN `tests.test_llm_governor tests.test_civilization_governor` (30 tests); `E:\GPTCode\local-agent-town\.venv\Scripts\python.exe -m unittest discover -s tests` (234 tests); `E:\GPTCode\local-agent-town\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1`; `git diff --check` | pass | Latest Mac gate was healthy except fallback-covered invalid JSON hours (no depletions, no stalls, no breaks, mood recovered). Fix: `LocalLLMClient.complete_json` now retries once after malformed/non-object model JSON with a strict JSON-only reminder, preserving timeout/connection failures; the governor prompt also caps replies at 6 highest-impact actions to reduce oversized/truncated action lists. Continued on PR #23 instead of switching branches because this is the active merge blocker and the next truth-loop slices depend on it. Main `E:\` checkout remains dirty/behind with separate hosted-OpenAI telemetry work and was left untouched. Next: rerun the Mac LM acceptance gate to confirm AMBER -> GREEN. |
| 2026-06-30 04:25 -06:00 | Full Mac LM acceptance gate for PR #23 `feat/production-target-honored` at `edf828ec778d14e3e9f4b5fa1d44220910a2eadc` | `.venv/bin/python -m pip install -e .`; `.venv/bin/python -m agent_town --smoke-test`; `.venv/bin/python -m unittest discover -s tests` (234 tests); `pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/validate-workbench.ps1`; LM Studio ping `http://192.168.1.131:1234/v1/models` found `google/gemma-4-e4b`; Pygame `CivilizationViewer` booted with blocking `LLMGovernor`; 96 simulated viewer hours; `.venv/bin/python scripts/analyze_run.py logs/run-20260630-041958.jsonl --events`; completed-log proof assertion; `git diff --check` | pass | Install/smoke/unit/docs/LM ping/viewer boot passed. The current game state stayed healthy for the full 4-day LM gate: analyzer `RESULT: GREEN`, 96/96 model decisions, 0 dropped/fallback hours, 0 warnings, 0 critical events, mood 85.8 -> min 72.4 -> end 82.4, idle peak 0, breaks 0, depletions 0, stalls 0, final stockpile bread 16 / water 96, and action histogram 396 `set_work_priority` + 2 `place_building`. Ready to merge; no Apple Silicon-specific failure evidence. See `docs/run_reports/2026-06-30-pr23-mac-lm-gate.md`. |
| 2026-07-01 03:44 -0600 | Full Mac LM acceptance gate for PR #34 `feat/llm-governor-dig-out-verify` at `5f56638d69e292b8687d2f3da77c42cde224dc1a` | `.venv/bin/python -m pip install -e .`; `.venv/bin/python -m agent_town --smoke-test`; `.venv/bin/python -m unittest discover -s tests`; `pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/validate-workbench.ps1`; LM Studio ping `http://192.168.1.131:1234/v1/models` for `google/gemma-4-e4b`; Pygame `CivilizationViewer` boot; 96 simulated viewer hours; `.venv/bin/python scripts/analyze_run.py logs/run-20260701-033736.jsonl --events`; `git diff --check` | fail | install=pass-python312, smoke=pass, unit=pass, docs=pass, lm_ping=pass, viewer_boot=pass, four_day=pass, analyzer=red, model_decisions=96/96, dropped=0, optional=skipped-not-scale-pathfinding-performance, ready_to_merge=no. Platform: likely-real-repo-game-state-or-lm-gate-failure-unless-noted; python3-default-3.9-so-venv-used-python3.12. See `docs/run_reports/2026-07-01-pr34-mac-lm-gate.md`. |
| 2026-07-01 | Roadmap UI navigation/readability pull-forward from owner feedback | `Select-String` inspection of `src\agent_town\civilization_view.py` and `tests\test_civilization_view.py`; `.\scripts\validate-workbench.ps1`; `git diff --check` | pass | Corrected the roadmap's stale button status: Work and History are live; Architect, Assign, Research, and Menu remain open button surfaces. Added the UI navigation/readability baseline as the next current-line slice before Paper 7 scale foundations, trader/death follow-ups, or deeper economy. The slice requires readable main-body composition, truthful button panels/menus, panel-state tests, and rendered proof under `docs/proof/ui_navigation/`. |
| 2026-07-01 | Implement RimWorld-style UI navigation/readability baseline | `.\.venv\Scripts\python.exe -m unittest tests.test_civilization_view` (40 tests); `.\.venv\Scripts\python.exe -m unittest discover -s tests` (267 tests); `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1`; `git diff --check`; rendered and inspected `docs\proof\ui_navigation\default.png`, `architect.png`, `work.png`, `assign.png`, `research.png`, `history.png`, `menu.png`; refreshed `docs\screenshots\current-state.png` | pass | Viewer now has exclusive reserved regions (macro strip, roster, map, right inspector/alerts, command panel, command strip), active panel state for all six bottom commands, non-overlapping docked panels, Work cycling still live, History alert acknowledgement preserved, and docs updated for the new operator workflow. Remaining gap: Architect/Assign/Research/Menu expose current truth and disabled reasons, but deeper placement, assignment, and research mechanics remain future systems. |
| 2026-07-01 | Make inspector tabs and Assign panel actually interactive | `.\.venv\Scripts\python.exe -m unittest tests.test_civilization_view` (44 tests); `.\.venv\Scripts\python.exe -m unittest discover -s tests` (271 tests); `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1`; `git diff --check`; rendered and inspected `docs\proof\ui_navigation\assign.png`, `inspector_log.png`, `inspector_bio.png`, `inspector_social.png`, `inspector_gear.png`, `inspector_health.png`; refreshed `docs\screenshots\current-state.png` | pass | The right-side inspector tabs now have real hit targets and distinct content. Assign is no longer a second Work view: it has a pawn selector plus job-slot rows, can pin the selected pawn to open/current slots as a forced override, and selects the occupying worker when a slot is full. Remaining gap: Gear/social/health show honest current-state and future-system gaps until inventory, relationships, and injuries exist. |
| 2026-07-01 | Add Governor decision audit and 20x crisis watch proof | `.\.venv\Scripts\python.exe -m unittest tests.test_civilization_view tests.test_telemetry` (62 tests); `.\.venv\Scripts\python.exe -m unittest discover -s tests` (277 tests); `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1`; `git diff --check`; rendered and inspected `docs\proof\governor_decision_audit\history_decision_detail.png` and `docs\proof\governor_decision_audit\crisis_20x_history.png` | pass | History is now a selectable decisions + events audit surface: Governor decisions show source/model state, proposed/applied/rejected policy payloads, completed buildings, after-state goods/needs, and a compact goods/jobs/bottleneck causality map. Menu now exposes 1x/8x/20x watch speed, and the 20x crisis proof uses the real `CivilizationViewer` stepping path. Remaining gap: full timeline scrubber and policy editor remain deferred. |
```

The last row's test count (277) matches the count observed in Section 2.

## 4. Fresh proof frame (rendered today by this pass)

Recipe source: `AGENTS.md` "Watchability Is Part Of Done" (set `SDL_VIDEODRIVER=dummy`, build the state,
call `render_civilization(...)`, `pygame.image.save(...)`). API confirmed in
`src/agent_town/civilization_view.py:658` — `render_civilization(surface, state, assets, font, origin, *, status_line=None, camera=None, selected_pawn_id=None, hovered_pawn_id=None, show_inspector=False, show_work_grid=False, show_history=False, active_panel=None, inspector_tab="needs", events=None, selected_history_record=None, speed_multiplier=1, alert=None, governor_summary=None)`.
State construction pattern taken from `tests/test_civilization_view.py` (`civilization.create_default_civilization()` + `engine.step_hour(state)`).

Script run (inline, no repo files modified): `create_default_civilization()`, 30 `engine.step_hour(state)` calls,
`load_civilization_assets()`, 1280x820 surface, `render_civilization(..., selected_pawn_id="pawn00", show_inspector=True)`,
saved to `docs/reviews/2026-07-01-pass0-proof-frame.png`.

Script output (verbatim):

```
pygame 2.6.1 (SDL 2.28.4, Python 3.10.12)
Hello from the pygame community. https://www.pygame.org/contribute.html
saved docs/reviews/2026-07-01-pass0-proof-frame.png (1280, 820) hour None pawns 12
```

(`hour None` is from my probe `getattr(state, "hour", None)`; `FactionState` evidently has no `hour` attribute.)

### Factual description of the rendered frame (image inspected)

- **Macro strip (top-left, badge row):** `Day 1`, `13:00`, `Pop 12`, `Idle 0`, `Coin 38`, `Bread 100`,
  `Water 87`, `Grain 0`, `Flour 0`, `Logs 1`, `Planks 12`, `Stone 25`. Top-right text:
  `Governor: Unblock production | 72% | fallback autopilot`.
- **Pawn roster (second row):** 12 portrait cards with sprite + job label: Forester, Sawyer, Mason,
  Farmer, Farmer, Farmer, Miller, Miller, Baker, Baker, Hand, `Wellkee...` (truncated). Each card has a
  small green dot; the first card (Forester) is outlined as selected.
- **Map:** a grass tilemap roughly 600x330 px in the upper-left of the larger map region; the rest of the
  map region is black (grid smaller than window at 1x camera). Visible: labeled buildings `Farm 1/1` (x4),
  `Mill 1/1` (x2), `Water Well 1/1`, `Bakery 1/1` (x2), pawn sprites standing on/near buildings, stone/rock
  clusters, scattered brown and teal tiles, one tree sprite near the well, a small white circle marker on
  the selected pawn.
- **Right inspector column:** top panel `Exceptions  5` listing `Missing inputs: Bakery` ("Bakery is
  blocked on flour.") twice, `Missing inputs: Mill` ("Mill is blocked on grain."), and `+2 more`. Below:
  pawn sheet for `Forester Fen` with badges `Healthy` and `default`, `State recreating`, `Job Forester`,
  a "Why this job" block (`Lane Normal work`, `forestry priority 1, skill 19`, `Passed over Bakery:
  reserved/full`). Tab row: Log, Gear, Social, Bio, **Needs** (active, highlighted), Health. Needs bars
  with percentages: Mood 78%, Food 73%, Recreation 81%, Rest 75%, Water 82%. Thoughts list: `tough +4`,
  `optimist +8`, `Rested & recreated +11`.
- **Bottom command strip:** buttons `Architect`, `Work`, `Assign`, `Research`, `History`, `Menu`
  (left-aligned; strip spans full width).
- **Legibility:** all text listed above was readable at 1280x820 with the size-16 default font.

Render did not error. File exists at `docs/reviews/2026-07-01-pass0-proof-frame.png`
(`E:\GPTCode\local-agent-town\docs\reviews\2026-07-01-pass0-proof-frame.png`).

## 5. Prior reviews and contract test methods

### 5a. docs/reviews/ prior contents

Before this pass wrote anything, `docs/reviews/` contained exactly one file:

```
-rwx------ 11186 Jul  1 18:22 REVIEW_PROTOCOL.md
```

No prior review/evidence files exist. The directory itself is untracked (`?? docs/reviews/` in git status).

### 5b. tests/test_civilization_contract.py — exists (146 lines). `def test_` methods (grep -n, verbatim):

```
27:    def test_goods_enum_has_current_chain_goods(self):
33:    def test_faction_state_is_the_root_container(self):
43:    def test_core_entities_instantiate_with_expected_fields(self):
68:    def test_schedule_template_requires_24_blocks(self):
76:    def test_grid_map_bounds_and_lookup(self):
86:    def test_factory_methods_set_the_right_kind(self):
109:    def test_effective_work_signature_is_frozen(self):
115:    def test_effective_work_placeholder_returns_float(self):
125:    def test_all_civilization_modules_import(self):
130:    def test_track_a_modules_are_implemented(self):
```

### 5c. tests/test_track_a_current_contract.py — exists (181 lines). `def test_` methods (grep -n, verbatim):

```
19:    def test_stockpile_add_remove_has_and_validation(self):
36:    def test_world_generation_and_nodes_are_deterministic(self):
49:    def test_harvest_and_filter_resource_nodes(self):
64:    def test_building_definitions_cover_current_chains(self):
78:    def test_make_building_and_open_slots_use_current_contract_ids(self):
88:    def test_production_tick_uses_effective_work_and_recipe_inputs(self):
106:    def test_off_shift_pawns_do_not_produce(self):
119:    def test_construction_delivery_work_and_completion(self):
143:    def test_place_construction_site_blocks_low_coin_without_mutating(self):
153:    def test_food_stone_chains_tax_and_affordability(self):
```

End of Pass 0 evidence packet.
