# Local Agent Town - Critical Review Protocol (Fable 5, multi-pass)

**Status:** proposed, not yet run.
**Supersedes:** the single-pass "adversarial reviewer" prompt used before Fable 5 was available.
**Purpose:** a repeatable, evidence-forced protocol for running critical passes on this repo with Fable 5, producing a dated file in `docs/reviews/` each time so future reviews can diff against it.

## Assumptions and constraints (confirmed by recon on 2026-07-01)

- **Working tree is dirty.** `git status --short` shows modifications to `AGENTS.md`, `BLUEPRINT.md`, `ROADMAP.md`, `RUNBOOK.md`, `README.md`, `VISUAL_DESIGN.md`, `pyproject.toml`, `.gitignore`, two `docs/run_reports/*` files, all eight `research_papers/*` files, `scripts/analyze_run.py`, and `Local_little_world_refactor1.md`. HEAD is `65eed44` ("Add observer decision audit"). Every pass must state whether it is reviewing HEAD or the working tree, because right now they differ across nearly every top-level doc.
- **The test suite is runnable headlessly in this environment, contrary to RUNBOOK.md's Windows-only framing.** Verified directly: `pip install pygame --break-system-packages && SDL_VIDEODRIVER=dummy PYTHONPATH=src python3 -m unittest discover -s tests` ran 277 tests in ~4s, result `OK`. `SDL_VIDEODRIVER=dummy PYTHONPATH=src python3 -m agent_town --smoke-test` exited 0. A review that only reads test *files* and trusts RUNBOOK's claimed result is throwing away free, cheap, real verification.
- **No prior review exists.** `find . -iname "*review*"` (excluding `.git`) returns nothing. This run is the baseline; it must be saved somewhere diffable, not left in chat.
- **`docs/proof/` has 5 slice folders** (`governor_decision_audit`, `llm_verify`, `slice0`, `slice1`, `ui_navigation`) but **`docs/screenshots/` has only 2 PNGs** (`current-state.png`, `work-grid.png`, last touched 2026-07-01 and 2026-06-29). Thin relative to a 705-line `ROADMAP.md` with daily commits.
- **AGENTS.md already defines a self-audit contract** nearly identical in spirit to the old review prompt: authority order (code beats docs), red/green/refactor, an explicit "Watchability Is Part Of Done" section with a concrete headless-render recipe, an append-only `ROADMAP.md` Verification Log, and a "What Not To Do" list (no invented APIs/files/behavior/results). The review should partly grade the project against *its own stated rules*, not a generic external rubric.
- **`tests/test_civilization_contract.py`** (146 lines) and **`tests/test_track_a_current_contract.py`** (181 lines) exist, but sampled test names read as structural (`test_all_civilization_modules_import`, `test_effective_work_signature_is_frozen`), not numeric. Whether the conservation law is tested as a real invariant anywhere, or only asserted in prose in `BLUEPRINT.md`/`ROADMAP.md`, is unverified and is Pass 3's job to determine, not assumed here.

## Why the old prompt was weaker

| Problem in the old single-pass prompt | Consequence | Fix in this protocol |
|---|---|---|
| One agent, one context, covers product + engineering + process + verification-gap-hunting at once | Whichever finding lands first anchors the rest; product opinions bleed into engineering severity | Split into 4 independent passes, each with a narrow rubric and its own context |
| Says "inspect tests" but never says "run them" | Reviewer trusts RUNBOOK's claimed result instead of real output - the exact false-confidence failure section 4 asked it to catch elsewhere | Pass 0 mandates running the suite and smoke test and quoting real output |
| Reading order is docs first (`AGENTS.md`...`README.md`), code second | Primes the reviewer with the project's own language before it forms an independent read; also contradicts AGENTS.md's own authority order (code > docs) | Pass 0 gathers facts from code/tests/git first; doc claims are cross-checked against that, not read as ground truth |
| "Watchable, understandable, compelling" has no operational definition | Verdict #1 is graded on vibes | Pass 1 scores against AGENTS.md's own watchability bar (signal wired to exception stack / Governor card / civ stat / world badge) |
| P0-P3 requested but never defined | Two runs of the same prompt would disagree on severity | Severity rubric below, defined against the four contract rules |
| No adversarial cross-check on the reviewer's own claims | Section 7 ("counterarguments") is self-graded homework from the pass that made the claims | Pass 4 runs in a separate context and only sees raw findings, not the framing that produced them |
| No fixed output location | Findings evaporate into chat, nothing to diff next time | Output lands in `docs/reviews/<date>-fable5-critical-review.md`, matching the existing `docs/run_reports/` dated-file convention |
| No git-state pinning | Can't reproduce or trust a review against a tree that's dirty across nearly every doc | Pass 0 records `git rev-parse HEAD` + full `git status --short` and the review states which state it covers |
| No time bound | Contradicts `UNATTENDED_WORK_POLICY.md`'s existing 60-minute default + checkpoint cadence for agent work in this repo | Each pass is time-boxed (see below) |
| Screenshots "if available" | With only 2 stale PNGs on disk, an "if available" reviewer skips the one check AGENTS.md calls most important | Pass 0 renders a fresh proof frame using AGENTS.md's own recipe before any product judgment happens |

## Severity rubric

| Severity | Definition |
|---|---|
| P0 | Breaks determinism, the conservation law, or the Governor/pawn autonomy boundary; or causes a crash/unhandled exception in the confirmed-runnable suite or smoke test. |
| P1 | An autonomous consequence exists in the simulation but is invisible or misattributed on screen; or a test named as a "contract" test only asserts structure, not the behavior its name implies. |
| P2 | Watchable but confusing; a RUNBOOK/BLUEPRINT/ROADMAP claim doesn't match observed behavior; a shipped slice is missing or has a stale proof frame. |
| P3 | Cosmetic, naming, or process friction with no behavioral risk. |

## Pass structure

**Pass 0 - Ground Truth Recon** (non-judgmental, ~15 min budget, produces the shared evidence packet for Passes 1-3)

- Record `git rev-parse HEAD` and full `git status --short`; state explicitly whether the review covers HEAD, working tree, or both.
- Run and quote verbatim: `SDL_VIDEODRIVER=dummy PYTHONPATH=src python3 -m unittest discover -s tests` and `SDL_VIDEODRIVER=dummy PYTHONPATH=src python3 -m agent_town --smoke-test`.
- Inventory `src/agent_town` (module list + line counts), `tests/` (file list + line counts), `docs/proof/*` and `docs/screenshots/*` (files + last-modified dates), the last 10 `ROADMAP.md` Verification Log rows, the last 20 `git log --oneline` entries.
- Render one fresh proof frame now with the AGENTS.md recipe (`render_civilization(...)` + `pygame.image.save(...)` under `SDL_VIDEODRIVER=dummy`) so Pass 1 judges a current image, not a stale one.
- Output a single evidence-packet file; Passes 1-3 receive it as fixed shared context so they can't disagree on facts and don't waste budget re-deriving basics.

**Pass 1 - Product/Watchability** (persona: a spectator who has never read the docs or source, only the rendered frame and the on-screen HUD/inspector as described in RUNBOOK.md)

- Judges only: is autonomous causality visible right now; does watching teach the rule; would a first-time viewer understand why a pawn is doing what it's doing without reading a doc.
- Forbidden from citing BLUEPRINT/ROADMAP prose as evidence for the verdict - those are cross-check inputs only, not proof of on-screen behavior.
- Scores against AGENTS.md's watchability bar specifically (new signal wired into exception-stack rank, Governor card, a Civ stat, or a world badge - not only into data).

**Pass 2 - Engineering/Contract** (persona: a systems engineer auditing determinism and conservation, cites `file:line` for every claim)

- Checklist: anything that creates/destroys goods without a matching production/consumption path; any unseeded randomness or wall-clock dependency; whether the Governor only sets policy or also mutates pawn state directly; whether `EffectiveWork`'s "frozen" signature (per `test_effective_work_signature_is_frozen`) is actually still frozen in the current diff.
- Runs `scripts/benchmark_scaling.py` if population-affecting code changed since the last Verification Log row.

**Pass 3 - Verification Integrity** (persona: a QA lead who assumes every green check is lying until proven otherwise)

- Classifies every test in `tests/` as behavioral/invariant, structural/import-smoke, or no-op. Starts from the two known-structural examples surfaced in recon (`test_all_civilization_modules_import`, `test_effective_work_signature_is_frozen`) and determines whether real conservation-law/economic-invariant tests exist anywhere or the law is prose-only.
- Cross-checks the last 10 `ROADMAP.md` Verification Log rows against `git log`: does every row match a real commit; does every commit touching `src/agent_town` have a matching row (AGENTS.md requires this).
- Checks whether any `docs/proof/<slice>/` folder is missing for a slice RUNBOOK/AGENTS.md say requires one.

**Pass 4 - Synthesis + Steelman** (separate context; receives only Passes 1-3's raw findings, not their framing or severity labels)

- Deduplicates overlapping findings across passes.
- Re-applies the severity rubric uniformly, since each pass may self-grade inconsistently.
- For every top-10 product finding and top-10 process finding, writes the strongest good-faith counterargument before finalizing severity - this is what actually satisfies "counterarguments" instead of letting the claim's author grade its own homework.
- Assembles the final deliverable in the original 7-section format (verdict, top-10 product, top-10 process, top-5 verification gaps, stop/keep/change, next 3 roadmap slices, counterarguments), plus a verified-fact-vs-inference appendix per finding.

## Running it

- Use the `Agent` tool with `model: "fable"`, one subagent per pass.
- Sequence: Pass 0 alone first. Its evidence packet gets pasted verbatim into the prompts for Passes 1, 2, 3, which can then run in the same batch (independent, read-only, no shared mutation). Pass 4 runs last and receives only Passes 1-3's output.
- Every subagent prompt inlines: the relevant rubric section above, the AGENTS.md excerpts for watchability/authority-order/determinism, and the "do not invent APIs, files, behavior, or test results" rule verbatim.
- No pass gets Edit/Write - this is a read-only audit; nothing here should touch `src/`, `tests/`, or docs.
- Final output: `docs/reviews/<YYYY-MM-DD>-fable5-critical-review.md`, matching the existing `docs/run_reports/` dated-filename convention.

## Recurring use

This file is the protocol, not a review result. The first actual run using it produces `docs/reviews/2026-07-01-fable5-critical-review.md` (or the run date) and becomes the baseline. Every review after that should open with a short diff against the most recent prior file in `docs/reviews/`: which findings were fixed, which regressed, which are new.
