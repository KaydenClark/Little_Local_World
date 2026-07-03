# Local Agent Town - Runbook

> Generated from LLM Workbench v2.1. See Upgrading The Harness below.

**Last reviewed:** 2026-07-02
**Runtime owner:** Kayden
**Environment:** local desktop (Windows and macOS; no server)

This file explains how to operate, verify, recover, and evaluate the project. It
is boring, exact, and executable.

The project runs on both Windows (PowerShell launchers) and macOS/Linux (Unix
venv). Commands below give both. The macOS/Linux path plus a headless
`SDL_VIDEODRIVER=dummy` run were verified in the v2.1 adoption on 2026-07-02
(262 tests + smoke green on Python 3.10; the project targets 3.11+ and CI/gates
use 3.12).

## Prerequisites

Required tools:

- Python 3.11 or newer (macOS gates use 3.12; do not use system Python 3.9).
- Windows PowerShell, or a POSIX shell on macOS/Linux.

Required accounts/services:

- None for the base prototype.
- Optional: a local OpenAI-compatible LLM server (LM Studio or Ollama).

Required local files:

- None before setup. `setup.ps1` (Windows) or a manual venv (below) creates
  `.venv`.

## Environment Configuration

No `.env` file is required for the base prototype.

| Variable | Purpose | Secret? | Example / Notes |
|---|---|---|---|
| `SDL_VIDEODRIVER` | Headless Pygame smoke/test override | no | `dummy` (set automatically by `--smoke-test`; set manually for headless test runs) |
| `AGENT_TOWN_LLM_MODEL` | Explicit model override | no | `google/gemma-4-e4b`, or the exact id loaded in LM Studio/Ollama |
| `AGENT_TOWN_LLM_BASE_URL` | OpenAI-compatible endpoint | no | `http://localhost:1234/v1` (LM Studio), `http://localhost:11434/v1` (Ollama), `https://api.openai.com/v1` (opt-in hosted only) |
| `AGENT_TOWN_LLM_TIMEOUT` | Per-request timeout (s) | no | default `8.0` |
| `AGENT_TOWN_LLM_MAX_TOKENS` | Max tokens for decision JSON | no | default `320` |
| `AGENT_TOWN_LLM_AUTO_DISCOVER` | Startup model discovery when no model is set | no | default `1`; `0` keeps the local model off unless `AGENT_TOWN_LLM_MODEL` is set |
| `OPENAI_API_KEY` | Hosted OpenAI bearer token (only when base URL is hosted OpenAI) | yes | Keep in an ignored local env file; never commit |

Rules:

- Do not commit real `.env` files, tokens, local databases, logs, or private
  data.
- Keep LLM provider credentials local-only. Hosted OpenAI runs are opt-in
  operator tests, not the default runtime.
- Prefer a visible degraded state over fake external data when a provider is
  unavailable.
- If no model variable is set, the app briefly checks the configured `/models`
  endpoint and selects the first non-embedding local model it finds.

## Install

Windows:

```powershell
.\setup.ps1
```

macOS/Linux (manual venv, mirrors what the Mac gates run):

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e .
```

Expected result: `.venv` exists, the package installs editable, Pygame is
available inside `.venv`.

## Run Locally

Windows:

```powershell
.\run.ps1
```

Double-click launcher: `Launch Local Agent Town.cmd`.

macOS/Linux:

```bash
.venv/bin/python -m agent_town
```

Open: a local Pygame window titled `Local Agent Town`.

Expected result: a civilization map appears; the engine advances simulated hours;
sprites render terrain, buildings, resources, and pawns; the top pawn roster,
right pawn sheet, Civ stats panel, resource HUD, Governor card, and exception
stack are visible.

Controls: pan `WASD`/arrows; zoom mouse wheel / `+` / `-`; select pawn click or
`Tab`; local model toggle `L`; quit `Esc`/`Q`. The **Work** button opens the
work-priority grid; the **History** button opens the live event feed. `Architect`,
`Assign`, `Research`, `Menu` are still placeholders.

## Test And Build

Fast check (headless). macOS/Linux:

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=src .venv/bin/python -m unittest discover -s tests
```

Windows:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Full verification:

```bash
# macOS/Linux
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=src .venv/bin/python -m unittest discover -s tests
PYTHONPATH=src .venv/bin/python -m agent_town --smoke-test
pwsh -NoProfile -File scripts/validate-workbench.ps1
```

```powershell
# Windows
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m agent_town --smoke-test
.\scripts\validate-workbench.ps1
```

Expected result: the unittest suite passes (262 tests as of 2026-07-02; the count
grows with new slices - do not hardcode a stale number), the smoke test exits
without import/display errors, and `validate-workbench.ps1` passes the
control-doc structure check. `validate-workbench.ps1` requires `pwsh`; if
PowerShell is unavailable, treat the doc-structure check as skipped and record
that in the proof row.

### Test Coverage Policy

Treat tests as the specification. The suite should be strong enough that deleting
a meaningful line, branch, data contract, or workflow step fails at least one
test or documented manual check. Prefer red/green TDD: write the failing test
first, confirm the expected failure, then implement the smallest fix. Keep tests
that prove behavior a user, operator, or future maintainer depends on; improve
tests that hide failures or rely on stale fixtures; remove pure bloat. If behavior
cannot be tested in the current harness, record the exact reason and use the
strongest concrete manual check.

## Manual Checks (per shipped slice)

Run the viewer and confirm:

- **Work arbiter:** open the `Work` grid, click a cell to cycle a pawn's priority
  (`1` highest .. `4` lowest .. blank off); the pawn re-routes within a step or
  two. No two pawns occupy the same single-slot building; the `Idle N` count
  rises when a work type is disabled. Headless proof: `unittest tests.test_work`.
- **Research spine:** a staffed Laboratory advances `research_points`; completing
  `efficient_baking` raises Bakery output from 4 to 5 bread/cycle. Headless proof:
  `unittest tests.test_research_spine`.
- **Water:** the default civ has a Water Well, a Water HUD chip, and a Water row
  in Civ stats; `Water` is a work type. Headless proof: `unittest tests.test_water`.
- **Storage caps:** the HUD shows `Storage N%`; with a Storehouse and >=80% full
  the chip turns amber, >=95% red with a Storehouse world badge. Headless proof:
  `unittest tests.test_storage_caps`.
- **Money loop:** day rollover pays assigned pawns; a staffed Market sells bread
  to wallets above reserve, records sales tax, exports the surplus; unmet buyers
  surface as `market_service_pressure`. Headless proof: `unittest tests.test_money_loop`.
- **Map readability:** hover uses a thin outline, selection a double outline,
  danger rings draw above selection; idle pawns get an overhead `!`; active
  construction sites render as ghosts with progress bars.

## Monitoring A Run

Live viewer: the `History` button shows recent structured events newest-first
(completed buildings, staple depletion, supply stalls, breaks, mass idle, mood
dips, dropped LLM decisions, invariant violations); warn/critical events light a
HUD alert chip and glow the button. The Governor card and exception stack are
observer surfaces, not command editors. Live viewer runs also write a JSONL log
under `logs/` (git-ignored).

Headless run + analyzer (post-run health gate):

```bash
.venv/bin/python scripts/llm_governor_run.py --hours 24
.venv/bin/python scripts/analyze_run.py logs/run-YYYYMMDD-HHMMSS.jsonl --events
```

Expected result: the runner prints each hour's applied actions and the JSONL path,
then a one-line health verdict; the analyzer prints run metadata, health summary,
flagged events, and `RESULT: GREEN|AMBER|RED`, exiting non-zero on a red
condition (invariant violation, staple depletion, mood collapse, high
dropped-decision rate). A run with no local model logs cleanly as deterministic
fallback and is not counted as dropped decisions.

Scaling benchmark:

```bash
.venv/bin/python scripts/benchmark_scaling.py --pawns 100 500 1000 --steps 24 --context-repeats 8 --draw-frames 3
```

Reports engine step time, governor context build time, dummy draw time, applied
action count, and completed-building count. Use it before raising default
population or deciding whether Pygame is the scaling blocker. Scale guidance lives
in `BLUEPRINT.md` -> Scale architecture and `research_papers/7.scalable-sim-report.md`.

## Evaluation And Benchmarking

Prove the project process is improving with evidence, not taste. The Mac/hosted
LM acceptance gate is the project's main end-to-end evaluation: install, smoke,
full unit discovery, `validate-workbench.ps1`, an LM ping, a booted
`CivilizationViewer` with a blocking `LLMGovernor`, ~96 simulated viewer hours,
and `analyze_run.py` returning `RESULT: GREEN`, with the run report saved under
`docs/run_reports/`. A slice is not "ready to merge" until that gate is GREEN
(AMBER/RED are not GREEN). Real hosted runs spend budget; record model,
conditions, hours, cost, and the result path before making claims.

## Research Intake

Papers in `research_papers/` are design inputs and source leads, not proof that
the code behaves that way. When using a paper: keep the raw file intact unless the
user asks to reorganize it; read it before editing docs/code; extract only the
project rule, affected files, tests, risks, and deferrals; if it conflicts with
the current implementation, record the conflict as a `TASKBOARD.md` task instead
of silently changing the design; verify cited constants against the source or mark
them research-derived.

## Data Operations

There is no civilization save/load or persistence model yet. Do not wire a
persistent local database into automatic viewer behavior without updating
`BLUEPRINT.md`, `RUNBOOK.md`, and tests. Do not store real private data in future
pawn/governor memory without explicit user approval.

## Deployment Or Startup

There is no deployment target. The project runs locally through the launchers
above.

## Version Control

- Branch from the default branch; do not commit directly to it. Branch names:
  `type/short-description` (for example `codex/repair-debt`).
- Commit messages: imperative subject <= 72 chars, the why in the body; one
  logical change per commit. Run `git status` before committing.
- Never commit secrets, `.env`, local databases, `logs/`, build output, `.venv`,
  or generated artifacts.
- Open a pull request with `gh` when the task is verified; the PR states what
  changed, why, risks, and how it was verified. The owner merges; self-merges are
  blocked by the permission layer.
- Do not rewrite published history or force-push shared branches unless the user
  approves.

## Upgrading The Harness

These control docs were generated from LLM Workbench v2.1 (see the stamp at the
top of each doc). To upgrade: check the LLM Workbench repo changelog for changes
since v2.1; re-copy only the changed template sections, keeping this project's
filled-in specifics (never let bracketed template placeholders leak back in);
update each doc's version stamp; re-run the full verification suite and record the
upgrade as a `TASKBOARD.md` proof-log row. Treat it like any other change:
smallest correct diff, verified, with proof. Lessons that should flow back to the
harness go in `HARNESS_FEEDBACK.md`.

## Troubleshooting

| Symptom | Likely cause | Check | Fix |
|---|---|---|---|
| `ModuleNotFoundError: pygame` | Setup not run or wrong Python | `.venv/bin/python -c "import pygame"` | Reinstall via `setup.ps1` or the manual venv install |
| Headless test import errors on pygame | No display / no dummy driver | rerun with `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy` | Set the dummy drivers for headless runs |
| macOS picks Python 3.9 | System Python selected | `python3 --version` | Use `python3.12` (e.g. `/opt/homebrew/bin/python3.12`) |
| Window does not open | Display or Pygame issue | `python -m agent_town --smoke-test` | Reinstall; check local graphics environment |
| Local model shows disabled/offline/invalid | Toggle off, no model found, server down, or malformed JSON | inspect the HUD governor row | Start LM Studio/Ollama, load a model, press `L`; set `AGENT_TOWN_LLM_MODEL`/`AGENT_TOWN_LLM_BASE_URL`; use a smaller instruct model |
| `validate-workbench.ps1` fails | Required control doc missing a heading, or `pwsh` unavailable | `pwsh -File scripts/validate-workbench.ps1` | Update the named doc; install PowerShell or record the check as skipped |

## Recovery And Rollback

If a change fails: identify the touched files and failing command; revert only the
smallest change needed, preserving user work; rerun the failing command; update
`TASKBOARD.md` with the result and remaining gap. Do not delete data, reset
repositories, rewrite history, or rotate secrets unless the user approves.

## Operational Proof

If a command here changed durable project state, append a row to the
`TASKBOARD.md` proof log. For routine local runs that do not change state, a final
response note is enough.
