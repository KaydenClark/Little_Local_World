# Local Agent Town — Critical Review (Multi-Pass Synthesis)

- **Date:** 2026-07-01
- **Reviewer:** Claude Fable 5, multi-pass protocol per `docs/reviews/REVIEW_PROTOCOL.md` (Pass 0 proof/smoke, Pass 1 product/watchability, Pass 2 engineering/contract, Pass 3 verification integrity, Pass 4 synthesis + steelman)
- **Git state covered:** working tree of `E:\GPTCode\local-agent-town` at HEAD `65eed44` ("Add observer decision audit"). Working tree dirty across 67 files; verified independently by Pass 2 (`git diff HEAD --stat` = 67 files, 16203 insertions / 16203 deletions; `--ignore-cr-at-eol` empty; no `.gitattributes`; `core.autocrlf` unset) and Pass 3 to be **100% CRLF line-ending churn, content-identical to HEAD**. All findings therefore apply equally to HEAD `65eed44`.
- **Confirmed runnable baseline (Pass 0):** 277 tests OK in 4.1s; smoke test exit 0.
- **Evidence packet:** raw findings of Passes 1–3 (embedded in this review's commission; finding IDs F1.x / F2.x / F3.x below refer to them). **Proof frame:** [`./2026-07-01-pass0-proof-frame.png`](./2026-07-01-pass0-proof-frame.png).
- **Grading note:** every finding was re-graded from the rubric by Pass 4. Pass self-grades were disregarded. Rubric: **P0** breaks determinism, the conservation law, or the Governor/pawn autonomy boundary, or crashes the confirmed-runnable suite/smoke; **P1** an autonomous consequence exists but is invisible/misattributed on screen, or a "contract"-named test asserts structure not the behavior its name implies; **P2** watchable-but-confusing, doc claim vs observed behavior mismatch, missing/stale shipped-slice proof; **P3** cosmetic/naming/process friction with no behavioral risk.

---

## 1. Verdict

Local Agent Town is a well-engineered deterministic simulation wearing the clothes of an autonomous-civilization game it does not yet play. At the pawn level it is genuinely watchable — named workers, a goods strip, and a standout "Why this job" panel deliver real causality — but at the town level a first-time viewer is actively taught wrong rules: the same five exceptions scream for five days while bread rises, the governor claims "Unblock production | 72%" while applying nothing in 120 hours, grain and flour read zero as bread accumulates, and the mood/civ-stats surfaces are dead code. The compelling version of the game exists only in engineered 20x crisis proofs a default viewer never reaches. The verification story is better than most but not yet trustworthy end-to-end: the sim core's determinism and ~90%-behavioral test suite are real strengths, yet the review found two P0 holes the suite cannot see — a demonstrated labor-conservation break via forced assign_pawn and a model-safety filter that silently approves four of six action kinds — plus a conservation "law" that exists only as prose, an analyzer that awards GREEN to runs where the model applied zero actions, and a Verification Log citing test counts that match no commit and run logs absent from the tree. Trust the core; do not yet trust the governor boundary or the green stamps around the model path.

---

## 2. Top 10 product findings (ranked)

### P-1. The exception stack cries wolf (F1.2) — **P1**
- **Evidence:** Pass 0 proof frame (Day 1 13:00, Exceptions 5, Bread 100) vs `pass1_longrun_default.png` (Day 5 07:00 after 120 `step_hour` calls): the identical five warn exceptions ("Missing inputs: Bakery … blocked on flour", "Missing inputs: Mill") verbatim, while Bread rose 100 → 140. FACT.
- **Pass grade check:** correctly graded — this is the loudest watcher signal misattributing sim state on screen.
- **Counterargument:** the exceptions may be truthful instantaneous states — the bakery could be blocked most hours and produce in bursts, so both "blocked" and "bread rising" are honest.
- **Post-steelman:** **P1 stands.** Five days of word-for-word identical warnings alongside a visibly improving outcome destroys the signal's credibility regardless of instantaneous truth; there is no aging, latching-to-resolution, or reconciliation with the outcome. The viewer's takeaway is "warnings are decorative."

### P-2. Production chain invisible — bread from nothing (F1.5) — **P1**
- **Evidence:** Grain 0 and Flour 0 in every current-layout frame including healthy Day 5 with Bread 140; audit claims Farm→Mill→Bakery. Slice-era frames showed Grain 3 / Flour 1 at best. FACT.
- **Pass grade check:** correctly graded.
- **Counterargument:** just-in-time consumption legitimately yields zero standing stock; the numbers are honest snapshots, not lies.
- **Post-steelman:** **P1 stands.** Even if the zeros are accurate, the autonomous consequence (a functioning three-stage chain) is invisible — the screen shows no flow, only stocks — and it directly contradicts the on-screen "blocked on flour" exceptions (P-1). The chain needs a flow/throughput signal, not a stock readout.

### P-3. Governor card and civ stats panel are dead code; mood has no surface (F1.1, cross-ref F1.12) — **P1**
- **Evidence:** `civilization_view.py:_draw_civ_stats` (line 1014) and `_draw_governor_card` (line 1649) defined with zero call sites (grep-verified); `render_civilization` (745–770) draws macro strip, roster, right column, command panel/strip only; macro-strip chip list (1152–1159) has no Mood chip. Both surfaces visible in old slice proofs, absent from every 04:02+ frame and fresh renders. FACT.
- **Pass grade check:** correctly graded for the mood/needs invisibility; the dead code itself is a P3 cleanup nit riding on a P1 product hole.
- **Counterargument:** the 65eed44 layout rewrite intentionally superseded the on-map card with the top-strip governor summary plus the decision audit panel; the card is legacy, not lost functionality.
- **Post-steelman:** **P1 stands for mood/needs.** The governor got replacement surfaces (however flawed — see P-6); civ mood and needs got none. Mood drives `effective_work` and taxation, i.e., autonomous consequences exist with no readable on-screen carrier (the only remnant is unlabeled 3px dots, P-10).

### P-4. Default watch session shows an inert autonomous layer (F1.3) — **P2**
- **Evidence:** 120 hours from default start: History is a wall of identical "decision fallback: no change" rows; audit detail Proposed: none / Applied: none; event kinds `Counter()`; zero warn/critical events in 5 days (`pass1_longrun_history.png` + script output). FACT.
- **Pass grade check:** Pass 1 treated this as near-fatal; by rubric it is P2 (watchable but confusing — nothing is invisible or misattributed; there genuinely is nothing).
- **Counterargument:** a healthy town at equilibrium *should* be calm; the drama lives in crisis scenarios, which the 20x proofs show working (Bread 0 chip, red "Bread depleted", "Built farm-1").
- **Post-steelman:** **P2 stands, ranked top of its band.** Calm is fine; a governor that proposes literally nothing for five days while displaying an active plan is not calm, it is inert — and for a game whose premise is "watch an autonomous governor," the default experience failing the premise is the single biggest compellingness problem even if no rubric clause elevates it.

### P-5. "Causality map" is static boilerplate (F1.4) — **P2** (downgraded from P1)
- **Evidence:** identical three lines for every decision in every run — placement, no-change, and crisis decisions all show the same text (`governor_decision_audit/history_decision_detail.png`, `crisis_20x_history.png`, `pass1_longrun_history.png`). FACT.
- **Pass grade check:** over-graded by Pass 1 if read as misattribution; it attributes nothing, it's a legend.
- **Counterargument:** it is a static schema of the decision pipeline, useful as orientation; it never claims to be per-decision.
- **Post-steelman:** **P2.** It is *labeled* "Causality map" and sits in a per-decision detail view, so viewers will read it as an explanation of THIS decision. Mislabeled static content in the audit's hero position — confusing, not lying.

### P-6. The one surviving governor surface truncates away model-vs-fallback attribution (F1.8) — **P2** (downgraded from P1)
- **Evidence:** "…| fallback (autopilot) | paw…" at 1280px (`pass1_longrun_default.png`); "Governor: Grow the food supply | 54…" at 942px in the shipped crisis proof (`crisis_20x_history.png`). FACT.
- **Counterargument:** attribution is redundantly available — the audit History rows say "decision fallback: no change" per decision, so nothing is unrecoverable.
- **Post-steelman:** **P2.** The always-on surface losing exactly the who-is-driving field at the proofs' own window widths is a real legibility bug, but the audit panel carries the fact, so it is confusion, not invisibility.

### P-7. Menu claims critical badges that never appear (F1.11) — **P2**
- **Evidence:** `pass1_menu.png` Overlays line claims "current map shows critical badges"; no critical badge visible on any building/pawn in any crisis frame — during Bread 0 / "Low food" critical, blocked Bakeries show only occupancy labels (`crisis_20x_history.png`). FACT.
- **Counterargument:** the badge class may be reserved for building-level criticals (e.g., broken/unstaffed) that these scenarios never triggered; the claim could be technically true and merely never exercised.
- **Post-steelman:** **P2 stands.** In-app doc vs observed behavior mismatch at the exact moment (crisis) the feature is for; either the badge is broken or the claim is misleading — both are P2, and the map staying silent during a civ-critical is the deeper design gap.

### P-8. Governor confidence reads as fake precision (F1.9) — **P2**
- **Evidence:** 72% at hour 13 and hour 120 with zero actions applied between; plan text "Unblock production" persists 5 days (Pass 0 frame vs `pass1_longrun_default.png`; run output confidence=72). FACT for constancy; INFERENCE that the number is not computed per-situation.
- **Counterargument:** it is plausibly the fallback plan's honest static confidence; a static plan legitimately has static confidence.
- **Post-steelman:** **P2 stands.** A percentage displayed in a live HUD implies a live quantity; five unchanging days teach the viewer the number is decorative — same cry-wolf failure mode as P-1, smaller blast radius.

### P-9. Same-frame contradiction: "Idle 0" chip vs "State idle" pawn sheet (F1.10) — **P2** (downgraded from P1)
- **Evidence:** `pass1_longrun_default.png`, Day 5 07:00. FACT.
- **Counterargument:** almost certainly a definition mismatch (macro chip counts unassigned pawns; pawn state machine reports momentary idleness), not a data error.
- **Post-steelman:** **P2.** Two on-screen surfaces disagreeing in the same frame is exactly "watchable but confusing"; fix is a shared definition or renamed chip.

### P-10. Mood carried only by unlabeled 3px dots (F1.12) — **P2**
- **Evidence:** `civilization_view.py` 926–929/1287; dots undecodable in all current frames; the old status line explaining them is gone from the current layout. FACT.
- **Counterargument:** the legend loss is rewrite fallout; dot color conventions become learnable over time.
- **Post-steelman:** **P2 stands.** With the civ stats panel dead (P-3), this is the *sole* mood carrier in the product, and it is undecodable without reading the source. Not cosmetic while it's the only channel.

**Below the top 10:** F1.6 menu speed-buttons drawn over "Plan" row text ("ox watch speed") — **P2** (fresh render `pass1_menu.png`, 1280x900); F1.13 no day/night/sleep visualization, sleeping pawns upright in a field at 03:00 — **P3** (state is inspectable on the pawn sheet); F1.14 label truncation "Wellkee…", "+2"/"+4" overflow chips at the proofs' own window sizes — **P3**.

---

## 3. Top 10 process/engineering findings (ranked)

### E-1. assign_pawn double-staffs a pawn — labor conservation broken (F2.1) — **P0**
- **Evidence:** `governor.py:328-336` — forced override appends to `building.staffed_by` and rewrites `pawn.assignment` without releasing the previous slot; `economy.py:45-48` counts the pawn's `effective_work` in both buildings. **Empirically demonstrated** in sandbox: after `apply_actions([assign_pawn("pawn00","waterwell1",...)])` on a stepped default civ, `{'forester1': ['pawn00'], 'waterwell1': ['pawn00']}` and post-step violations `['pawn pawn00 staffed in 2 buildings at once']`; the arbiter (`work.py:313-321`) never prunes the stale entry, so it persists across engine steps. FACT (double-staffing + persistence demonstrated; double production is direct code reading).
- **Pass grade check:** correctly graded.
- **Counterargument:** the only trigger is forced-override `assign_pawn`, which the fallback governor may never emit; the prompt discourages it (`governor.py:533-534`); no shipped run has exhibited it.
- **Post-steelman:** **P0 stands.** It was demonstrated through the public action API on a default civ; the health check flags it but nothing heals it; and E-2 shows the model path can reach it unguarded. One pawn's labor counted twice is a conservation-law break by the rubric's letter.

### E-2. Model safety filter silently approves 4 of 6 action kinds (F2.2 + F2.3, merged) — **P0**
- **Evidence:** `governor.py:614-627` — `_model_action_safe` handles `ACTION_SET_SCHEDULE` and `ACTION_SET_WORK_PRIORITY`, then `return True` for everything else. Consequences: (a) `set_production_target(bakery, bread, 0)` passes guard and validation (`governor.py:300-301` allows amount 0; `economy.py:211-215` → building idles) — essential-shutdown by another lever, the very class of action the filter exists to stop; (b) `assign_pawn` — the E-1 trigger — is fully model-reachable with only prompt-level discouragement. The commit-history guard is real for `set_work_priority` (`governor.py:620-621`) but the fall-through defeats the pattern. FACT for code paths; consequence requires a model emission (INFERENCE).
- **Pass grade check:** correctly graded.
- **Counterargument:** parameter validation still bounds-checks everything; the prompt discourages misuse; blocking-mode gate runs (96/96) surfaced no harmful emissions; local models mostly emit no-ops (F3.4).
- **Post-steelman:** **P0 stands.** The Governor/pawn autonomy boundary is supposed to be *enforced* by this filter; a default-allow fall-through means the boundary is enforced by prompt etiquette. Rubric: boundary broken. That no model has yet walked through the open door is luck, not a control.

### E-3. The conservation law is prose: no ledger in code, no ledger in tests (F2.4 + F3.6 + F3.7, merged) — **P1**
- **Evidence:** `health.py:85-86` docstring claims the "nothing from nothing" law; `health.py:105-107` implements only negative-stock (count<0) plus staffing shape. No test in `tests/` asserts goods_in − goods_out == delta, no long-run no-negative sweep (Pass 3 grep: nothing); `check_invariants` is called only from `telemetry.py:330` and unit-tested only on fresh + hand-mutated state (`test_health.py:34-44`); no test asserts invariants stay empty across a multi-day engine run. BLUEPRINT.md line 90 states the law in prose. FACT.
- **Pass grade check:** Passes graded this correctly in spirit; the rubric's P1 clause (a named guard asserting structure, not the behavior its name implies) is the exact shape — a function whose docstring claims the law and whose body checks a shadow of it.
- **Counterargument:** conservation is enforced by construction — Pass 2 traced goods flows clean (adds only at seeding + recipe outputs; `Stockpile.remove` raises on deficit, `core.py:114-115`), and Slice 0/1 escape paths were verified conservation-clean (F2.13).
- **Post-steelman:** **P1 stands.** Enforcement-by-construction failed exactly once already — E-1 is a live conservation break that only a telemetry-time shape check notices and no test exercises mid-run. The law the project is named for has no executable statement.

### E-4. Analyzer awards GREEN to runs where the model applied nothing (F3.4 + F3.5, merged) — **P1**
- **Evidence:** `analyze_run.py logs/run-20260701-024743.jsonl` → "model=google/gemma-4-e4b … LLM decisions : 115 (uptime 44%, dropped 0) applied actions: (none) … RESULT: GREEN"; all 115 decision records have `"outcome": ""`. Separately, `run-20260701-031223.jsonl`: "LLM decisions : 257" while applied = `{'set_work_priority': 5}`; llm_source all "scheduler" — the count conflates scheduler-attached hours with model output. This is the exact "green run proves nothing about the model path" hazard AGENTS.md itself warns about. FACT.
- **Pass grade check:** correctly graded.
- **Counterargument:** GREEN measures pipeline health (uptime, drops), not model efficacy, and the analyzer prints "applied actions: (none)" honestly right on the report; the details don't lie.
- **Post-steelman:** **P1 stands.** The verdict word is what Verification Log rows cite ("96/96 model decisions"), and the headline count demonstrably measures scheduler attachment, not model behavior. A verification instrument whose label implies behavior while asserting structure is the P1 clause applied to the gate itself.

### E-5. Verification Log rows claim green states that match no commit (F3.1) — **P2**
- **Evidence:** per-commit `def test_` counts: abf2251=245, 806b482=249, 1b26467=249, 937e033=259, 5f56638=260, 65eed44=277; `ROADMAP.md:703-704` rows claim "267 tests" and "271 tests" green; all four 2026-07-01 UI rows were appended in the single commit 65eed44. FACT.
- **Pass grade check:** reasonable; by rubric this is a ROADMAP claim vs observed state mismatch → P2, not fabrication-grade P1, given the steelman.
- **Counterargument:** 267 and 271 plausibly existed transiently in the dirty working tree between commits during the day's work; batch-appending rows at day's end records real intermediate runs that simply never got their own commits.
- **Post-steelman:** **P2 stands.** Even under the innocent reading, the log's core value — "this row is re-verifiable against this state" — is broken: the claimed states are unreachable. Honest sloppiness still poisons an audit trail.

### E-6. Every gate-cited run JSONL is absent from the tree (F3.3) — **P2**
- **Evidence:** rows cite `logs/run-20260630-031923/-034953/-041958.jsonl` and `logs/run-20260701-033736.jsonl`; none exist (28 other JSONLs do); `analyze_run.py` on a cited log → "No such log", exit 2. FACT.
- **Counterargument:** gate runs execute on the Mac gate machine; its logs living there is a storage decision, not concealment — and 28 other logs *are* shipped.
- **Post-steelman:** **P2 stands.** Combined with E-8 (wall-clock scheduler), the cited gate evidence is unreproducible *and* unavailable: the "96/96" claims are trust-based from this tree. Ship what you cite.

### E-7. Five state-changing commits appended zero Verification Log rows (F3.2) — **P2**
- **Evidence:** `git show` empty of log changes for abf2251 (Slice 0), 806b482, 1b26467, 937e033 (Slice 1), 5f56638 (live LLM verify); Slice 0/1 and llm_verify have proof folders but no log rows at all, violating AGENTS.md "append when state changes". FACT.
- **Counterargument:** the proof folders themselves are the verification artifacts; the rows were an afterthought formalism the team back-filled later (E-5's four batched rows).
- **Post-steelman:** **P2 stands.** The project chose the rule; the two biggest slices shipped without it. A rule honored only after the fact is not a control (mitigated by F3.11: the append-only property itself was never violated).

### E-8. LLM-enabled runs are wall-clock dependent by construction (F2.7) — **P2** (downgraded from determinism-P0 territory)
- **Evidence:** decision scheduler gates model calls on `time.monotonic` cooldowns (`governor.py:762, 862`), so 96-hour proof runs are unreproducible even with the same seed; documented as an accepted nondeterministic layer at `engine.py:28-30`. FACT.
- **Pass grade check:** Pass 2 flagged it under determinism; that over-reads the rubric — the sim core got an explicit ALL-CLEAR (only randomness is string-seeded `random.Random(f"{seed}:{pawn}:{day}:{tod}")`, `engine.py:227`), and the layer is documented.
- **Counterargument:** layered determinism is the stated architecture; an LLM layer is inherently nondeterministic and the design says so.
- **Post-steelman:** **P2.** Accepted design, but it converts every model-path claim into a one-shot observation — which is exactly why E-6 (missing logs) matters so much.

### E-9. Primary production mints goods ex nihilo while the resource-node system sits dead (F2.5; cross-ref F2.6 coin faucet) — **P2** (downgraded)
- **Evidence:** Forester/Farm/Well/Quarry recipes have `inputs={}` (`buildings.py:30,44,65,72`); `world.harvest_node` (`world.py:71-77`) has zero call sites in the sim loop; drift acknowledged at `civilization.py:18-19` while `world.py:4-5` still advertises the node list. Coin similarly minted by `apply_daily_tax` (`economy.py:158,164`) with construction the only sink (`construction.py:58`). FACT.
- **Counterargument:** every colony sim has primary-producer faucets; "nothing from nothing" governs the *chain* (no duplication, no leaks), and the drift away from nodes is explicitly acknowledged in code.
- **Post-steelman:** **P2.** Acknowledged design drift, so not a conservation break — but BLUEPRINT prose, the advertised node list, and the `check_invariants` docstring (E-3) all still describe the un-shipped world. Docs/claims vs behavior: P2. Coin faucet (F2.6): **P3** under the same steelman.

### E-10. Stale slice proofs + newest slice proven only by smoke tests and PNGs (F1.7 + F3.10 merged; F3.14) — **P2**
- **Evidence:** slice0/slice1 proof PNGs (timestamps 01:17/01:44, commits 806b482/937e033) show a layout — bottom macro strip with Mood/Sites chips, on-map Civilization panel, on-map Governor card — that the working-tree renderer cannot produce (dead-code grep, F1.1); `civilization_view.py` was rewritten at 04:01 by 65eed44; `ui_navigation/menu.png` lacks the speed buttons current code draws. Meanwhile 8 of 49 viewer tests are render-no-crash smokes (`test_civilization_view.py` lines 83–571) including the decision-detail panel of the newest slice; its rendered content is proven only by PNG + hit-test/click tests. FACT (staleness); materiality INFERENCE.
- **Counterargument:** proof frames are commit-time historical records, not living documentation; sim behavior is separately pinned by `test_food`/`test_dig_out`; behavioral companions for the audit panel exist (click-selects-decision line 634, alert ack 624, 20x stepping 656).
- **Post-steelman:** **P2 stands.** The crisis proofs are the repo's *current* evidence that crisis visibility works, and the current renderer cannot produce those screens — rubric names this case explicitly (stale proof frame on a shipped slice).

**Below the top 10:** F2.10 coin spent at placement but goods never reserved, no cancel/refund → strandable sites (`engine.py:126,139-141`, `construction.py:58`) — **P2**; F2.9 no tile-occupancy check, governor dig-out coordinates can in principle stack a ghost on a building (`construction.py:41-42`, `governor.py:400-402`) — **P2** (collision-in-practice undemonstrated); F3.15 only local LM Studio evidence is one untracked console log; Mac gate transcripts uncorroborated in-tree — **P2**; F2.8 `test_effective_work_placeholder_returns_float` asserts `isinstance(result, float)` against the fully implemented 5-factor frozen seam (`tests/test_civilization_contract.py:115-121`, `mood.py:125-138`) — **P2** (not P1: the file's docstring honestly declares itself a shape/import proof, F3.13, and the test name accurately states its weak assertion; the "placeholder" label is stale); F2.11 superlinear step cost, measured 2.865→16.664 ms/hour at 100→500 pawns (`work.py:233,391-392` rescan) — **P3** (real numbers, no risk at current scale; quadratic projection is inference); F2.12+F3.9 67-file CRLF-only dirty tree, no `.gitattributes` — **P3** (zero behavioral delta; the risk is the next `git add -A` committing a repo-wide rewrite and destroying blame); F2.15 dead `stockpile_add` wrapper — **P3**; F3.8 the required survival-staple viewer-priority test is real and behavioral but lives in `test_food.py` instead of the viewer test file — **P3** (placement nit on a green-verified test).

---

## 4. Top 5 verification gaps

1. **No executable conservation law.** No ledger check in `check_invariants` despite its docstring, no goods_in−goods_out test, no multi-day invariants-stay-empty test. A mid-run conservation break (E-1 is one) surfaces only as an untested telemetry record. (E-3; F2.4/F3.6/F3.7)
2. **The model-path gate can go GREEN on zero model efficacy.** Analyzer verdict requires no applied actions; "LLM decisions" counts scheduler-attached hours. Every "96/96" claim is only as strong as a human reading past the headline. (E-4; F3.4/F3.5)
3. **Gate evidence is neither in-tree nor reproducible.** All four cited run JSONLs absent; wall-clock scheduling makes reruns non-comparable even with the seed; local-LLM corroboration is one untracked console log. Model-path honesty is trust-based from this tree. (E-6, E-8; F3.3/F2.7/F3.15)
4. **The Verification Log cannot be replayed.** Rows cite test counts (267, 271) matching no commit; five state-changing commits have no rows; rows were batch-appended in 65eed44. Append-only discipline held (F3.11) but row-to-state traceability did not. (E-5, E-7; F3.1/F3.2)
5. **Shipped-slice UI evidence is stale or shallow.** Slice 0/1 proofs depict a renderer two revisions gone; the newest slice's decision-detail content is covered by render-no-crash smokes and PNGs, not content assertions. Nothing currently proves the shipped crisis *screen*. (E-10; F1.7/F3.10/F3.14)

---

## 5. Stop / Keep / Change

**Stop**
- Stop treating prompt discouragement as the Governor boundary — `_model_action_safe`'s `return True` fall-through must go before any further model-enabled runs are cited as evidence. (E-2)
- Stop citing run logs and test counts that are not in the tree; a gate row without its artifact is an anecdote. (E-5, E-6)
- Stop batch-appending Verification Log rows after the fact; the row lands in the commit that changed the state, or the rule is theater. (E-5, E-7)
- Stop presenting slice0/slice1 PNGs as current crisis evidence; mark them historical or re-render. (E-10)
- Stop any `git add -A` until a `.gitattributes` normalizes line endings — one reflexive commit destroys blame across 67 files. (F2.12)

**Keep**
- Keep the string-seeded deterministic sim core exactly as is — Pass 2's determinism audit was ALL-CLEAR, and telemetry wall-clock/uuid is provably out of the sim path. (F2.14, checklist 2)
- Keep the per-pawn "Why this job" panel — the best surface in the product, genuinely answering pawn-level causality including what was passed over. (Pass 1 scorecard)
- Keep the ~90%-behavioral test culture and its strong oracles (25-day dig-out recovery, LLM-vs-fallback 96-hour determinism, input-consumption checks). (Pass 3 taxonomy)
- Keep the log's honesty about failure — the PR34 fail row and the RED→AMBER→GREEN progression are exactly what a trustworthy log looks like. (F3.16)
- Keep the frozen `effective_work` seam signature discipline — verified intact. (Pass 2 checklist 4)

**Change**
- Make `assign_pawn` release the previous slot and make the arbiter prune stale `staffed_by` entries — the demonstrated P0. (E-1)
- Invert `_model_action_safe` to an explicit per-kind allowlist with default-deny. (E-2)
- Implement the ledger in `check_invariants` and add a multi-day invariants-empty engine test — turn the law from prose into an oracle. (E-3)
- Make the analyzer's GREEN require applied model actions (or emit AMBER "pipeline-only"), and split "LLM decisions" into scheduler-hours vs model-emissions. (E-4)
- Give the town-level story a screen: a Mood chip, aging/resolving exceptions, and a chain-flow indicator so bread stops appearing from nothing. (P-1, P-2, P-3)
- Fix the truncating governor summary and the menu overlap at the proofs' own window sizes. (P-6, F1.6)

---

## 6. Next 3 roadmap slices (smallest correct change each)

**Slice A — "One pawn, one job" (labor conservation).**
`assign_pawn` releases the pawn's previous `staffed_by` slot on forced override; the arbiter additionally prunes any pawn appearing in two buildings' `staffed_by` at step start.
- **Test:** `test_assign_pawn_releases_previous_slot` — apply a forced `assign_pawn` to an already-staffed pawn on a stepped default civ, step once, assert the pawn appears in exactly one `staffed_by` and `check_invariants(state) == []`.
- **Proof frame:** `docs/proof/slice_labor/01_reassigned_pawn_single_building.png` — roster + both buildings' occupancy labels showing the pawn in the new building only.

**Slice B — "Default-deny model guard."**
Rewrite `_model_action_safe` as an explicit allowlist over all 6 action kinds; unknown or unlisted kinds return False; add essential-target floor for `set_production_target` and forbid model-issued forced `assign_pawn`.
- **Test:** `test_model_guard_default_denies` — feed the guard a model-attributed `set_production_target(bakery, bread, 0)` and a forced `assign_pawn`, assert both rejected and rejection reason recorded in the decision audit.
- **Proof frame:** `docs/proof/slice_guard/01_audit_rejected_model_action.png` — decision-detail panel showing a model proposal with a visible "rejected: guard" outcome.

**Slice C — "The law, executable."**
`check_invariants` gains a per-hour goods ledger: for every good, delta == recipe outputs − recipe inputs − eat/drink − construction spend − hauling in transit; wire an every-N-hours assertion into the engine test harness.
- **Test:** `test_conservation_ledger_holds_10_days` — run the default civ 240 hours, assert `check_invariants` empty at every hour.
- **Proof frame:** `docs/proof/slice_ledger/01_health_zero_violations_day10.png` — the health/telemetry surface at Day 10 showing violations: 0 alongside nonzero production.

---

## 7. Counterarguments summary — the 3 strongest defenses, and what they do not excuse

1. **"The core is clean."** Fully deterministic sim core (string-seeded RNG only), telemetry provably out of the sim path, goods flows traced clean through the chain, and the slice 0/1 escape paths verified conservation-clean with the free-food leak explicitly removed. Largely true — and it does **not** excuse the two P0s, because both live precisely in the governor-action layer the clean core hands control to and the test suite doesn't watch.
2. **"The verification culture is real."** ~90% behavioral tests, zero vacuous tests found, strong long-horizon oracles, append-only log honored, failures recorded honestly (RED→AMBER→GREEN in the log's own rows). True — and it does **not** excuse a log citing states that never existed, gate logs missing from the tree, an analyzer whose GREEN is achievable with zero model-applied actions, or a conservation law with no executable form. Good culture plus unreproducible headline claims still yields trust-based verification.
3. **"The drama works — see the 20x crisis proofs."** The engineered crisis frames show real teaching moments: Bread 0 chip, red "Bread depleted", "Built farm-1", and pawn-level causality is delivered today. True — and it does **not** excuse that a default viewer never reaches any of it, that those proof frames depict a UI the current renderer cannot produce, and that what the default viewer *does* see (permanent warnings, a 72%-confident governor doing nothing, bread from nothing) teaches the wrong rules.

---

## Appendix A — Verified fact vs inference, per finding

| ID | Core claim | Verified fact | Inference component |
|---|---|---|---|
| P-1 (F1.2) | Exceptions identical 5 days while bread rises | Frame-to-frame verbatim match; Bread 100→140 | None |
| P-2 (F1.5) | Chain invisible; Grain/Flour 0 always | All inspected frames | "Teaches bread from nothing" (viewer effect) |
| P-3 (F1.1) | Governor card / civ stats dead code; no Mood chip | Grep zero call sites; render path lines 745–770; chip list 1152–1159 | None |
| P-4 (F1.3) | Default 120h: all fallback no-change, zero events | History frames + script output (empty Counter) | None |
| P-5 (F1.4) | Causality map identical across all decisions/runs | Three PNGs text-identical | None |
| P-6 (F1.8) | Summary truncates attribution at 1280/942px | Two frames | None |
| P-7 (F1.11) | Menu claims critical badges; none observed in crisis | Menu text vs crisis frames | Whether badges are broken vs never-triggered |
| P-8 (F1.9) | Confidence constant 72% over 107h of inaction | Frames + run output | Number not computed per-situation |
| P-9 (F1.10) | Idle 0 chip vs State idle sheet, same frame | One frame | Definition-mismatch explanation |
| P-10 (F1.12) | Mood only via unlabeled 3px dots | Code lines 926–929/1287; frames | None |
| F1.6 | Speed buttons overlap Plan row | Fresh 1280x900 render | None |
| F1.13 | Sleeping pawns upright at 03:00, no night viz | Frames | None |
| F1.14 | Label truncation/overflow chips | Frames | None |
| E-1 (F2.1) | Double-staffing, persists, arbiter never prunes | Sandbox demonstration + violations output + code lines | Double *production* (direct code reading, not run-measured) |
| E-2 (F2.2/3) | Guard fall-through `return True` for 4/6 kinds | governor.py:614-627; validation allows target 0 | A model actually emitting the harmful action |
| E-3 (F2.4/F3.6/F3.7) | Law claimed in docstring, only count<0 checked; no ledger/cross-tick tests | health.py:85-86,105-107; grep of tests/; test_health.py:34-44 | None |
| E-4 (F3.4/F3.5) | GREEN with applied actions: (none); counts = scheduler hours | Analyzer output on two named JSONLs | None |
| E-5 (F3.1) | 267/271 test counts match no commit | Per-commit def test_ counts; ROADMAP.md:703-704 | Innocent transient-count explanation |
| E-6 (F3.3) | All 4 gate-cited JSONLs absent; analyzer exit 2 | ls + analyzer run | None |
| E-7 (F3.2) | 5 state-changing commits, zero log rows | git show per commit | None |
| E-8 (F2.7) | LLM layer wall-clock gated; documented | governor.py:762,862; engine.py:28-30 | None |
| E-9 (F2.5/F2.6) | Empty-input primary recipes; harvest_node uncalled; coin minted | buildings.py/world.py/economy.py lines; grep | Materiality vs acknowledged design |
| E-10 (F1.7/F3.10/F3.14) | Slice proofs predate renderer rewrite; 8/49 render smokes | Timestamps + commit provenance + dead-code grep; test line numbers | Materiality of proof staleness |
| F2.9 | No tile-occupancy check | construction.py:41-42 | Collision occurring in practice |
| F2.10 | Goods unreserved; no cancel/refund path | engine.py/construction.py lines | Permanent stranding frequency |
| F2.11 | 5.8x cost at 5x pawns | Benchmark output (2.865→16.664 ms/hr) | Quadratic projection to 500+ |
| F2.12/F3.9 | 67-file CRLF-only diff, content==HEAD | git diff stats; --ignore-cr-at-eol empty | None |
| F2.8 | Frozen-seam test asserts isinstance only | Test + implementation lines | None |
| F3.15 | Single untracked LM Studio log; gate transcripts uncorroborated | Directory listing | None |
| F2.15 | Dead stockpile_add wrapper | Grep: definition only | None |
| F3.8 | Staple-priority test real, misplaced | Test content in test_food.py | None |
| Positives (F2.13/F2.14/F3.11/F3.12/F3.13/F3.16) | Conservation-clean escape paths; telemetry isolated; append-only honored; track-A contract genuinely behavioral; honest structural docstring; honest failure rows | All FACT per cited lines/rows | None |

---

## Appendix B — Full deduplicated finding list with pass origins

| Consolidated | Pass origin(s) | Final severity | Dedup note |
|---|---|---|---|
| P-1 Cry-wolf exceptions | F1.2 | P1 | — |
| P-2 Invisible production chain | F1.5 | P1 | — |
| P-3 Dead governor card / civ stats; mood surfaceless | F1.1 | P1 | Cross-refs P-10; dead-code aspect P3 |
| P-4 Inert default watch | F1.3 | P2 | — |
| P-5 Static causality map | F1.4 | P2 (was graded higher by Pass 1) | — |
| P-6 Truncated attribution | F1.8 | P2 (downgraded; audit rows redundant) | — |
| P-7 Phantom critical badges | F1.11 | P2 | — |
| P-8 Fake-precision confidence | F1.9 | P2 | — |
| P-9 Idle 0 vs State idle | F1.10 | P2 (downgraded) | — |
| P-10 Unlabeled mood dots | F1.12 | P2 | Only mood carrier given P-3 |
| Menu overlap bug | F1.6 | P2 | — |
| No night/sleep viz | F1.13 | P3 | — |
| Label truncation/overflow | F1.14 | P3 | — |
| E-1 Double-staffing | F2.1 | **P0** | F2.3 is its model-path trigger |
| E-2 Guard fall-through | F2.2 + F2.3 | **P0** | Merged: same `return True` root cause |
| E-3 Law is prose | F2.4 + F3.6 + F3.7 | P1 | Merged: code claim + missing tests, one gap |
| E-4 Analyzer GREEN | F3.4 + F3.5 | P1 | Merged: verdict + count conflation |
| E-5 Log counts match no commit | F3.1 | P2 | — |
| E-6 Gate JSONLs absent | F3.3 | P2 | — |
| E-7 Missing log rows | F3.2 | P2 | — |
| E-8 Wall-clock LLM layer | F2.7 | P2 (Pass 2 over-flagged vs documented design) | — |
| E-9 Ex nihilo primary production; dead nodes | F2.5 (+F2.6 coin, P3) | P2 | Coin faucet split out at P3 |
| E-10 Stale slice proofs; smoke-only newest slice | F1.7 + F3.10 + F3.14 | P2 | Merged: Pass 1 layout evidence + Pass 3 provenance + smoke census |
| Unreserved construction goods | F2.10 | P2 | — |
| No tile-occupancy check | F2.9 | P2 | — |
| Untracked/absent LLM corroboration | F3.15 | P2 | — |
| Stale "placeholder" seam test | F2.8 | P2 (not P1: honest docstring per F3.13) | — |
| Superlinear scaling | F2.11 | P3 | — |
| CRLF dirty tree | F2.12 + F3.9 | P3 | Merged: identical verification, Pass 2 has fullest git evidence |
| Dead stockpile_add | F2.15 | P3 | — |
| Misplaced staple test | F3.8 | P3 | Test itself green-verified |
| Positives: conservation-clean escapes; telemetry isolation; append-only honored; behavioral track-A contract; honest structural docstring; honest failure rows | F2.13, F2.14, F3.11, F3.12, F3.13, F3.16 | n/a (credits) | Recorded to balance the ledger |

**Final severity distribution: P0 = 2, P1 = 5, P2 = 19, P3 = 7** (33 consolidated findings; 6 additional positive/credibility notes ungraded).
