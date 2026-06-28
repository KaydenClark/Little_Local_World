# Local Agent Town - Agent Instructions

This file controls how agents behave in this project.

## Authority Order

When instructions conflict, use this order:

1. Current user request.
2. This `AGENTS.md`.
3. Source code and tests.
4. `BLUEPRINT.md`.
5. `ROADMAP.md`.
6. `RUNBOOK.md`.
7. `README.md` and older handoff notes.

If docs and code disagree, trust verified code, flag the drift, and update stale docs when the task touches that area.

## Read Scope

The agent may read:

- `E:\GPTCode\local-agent-town`;
- source, tests, configs, scripts, and docs needed for the requested task;
- dependency manifests and lockfiles;
- generated output only when debugging install or runtime behavior;
- external paths only when the user request or project docs explicitly reference them, such as `E:\GPTCode\LLM_Workbench`.

The agent must not read secrets, private exports, unrelated local databases, or unrelated projects unless the user explicitly asks for that scope.

## Edit Scope

The agent may edit:

- `src\agent_town`;
- `tests`;
- `scripts`;
- project docs: `README.md`, `AGENTS.md`, `BLUEPRINT.md`, `ROADMAP.md`, `RUNBOOK.md`, `BOOTSTRAP_CHECKLIST.md`, `UNATTENDED_WORK_POLICY.md`, `VISUAL_DESIGN.md`;
- dependency manifests only when the dependency change is necessary and explained.

The agent must not edit:

- `.venv`, `__pycache__`, build output, or generated logs;
- secrets, credentials, tokens, local databases, raw personal data, or unrelated projects;
- the persistence model, LLM provider model, or external integrations unless the user asks for that or the current approach blocks correctness.

If the correct change requires leaving this scope, stop and explain the smallest needed scope expansion.

## Stop And Ask

Stop and ask before:

- destructive filesystem actions, including recursive delete, reset, clean, or overwrite operations;
- touching production data, private exports, secrets, credentials, tokens, or local databases;
- creating paid services, changing billing, or enabling external integrations;
- changing authentication, authorization, permission, or encryption behavior;
- deploying externally or changing deployment configuration;
- broad dependency upgrades or architecture rewrites;
- continuing after repeated verification failures when the next step is not clearly safe.

If the work can continue safely in a smaller scope, do that first and record the limitation.

## Agent Job

Maintain and improve this local desktop social simulation without changing its purpose.

Default responsibilities:

- restate the current goal in one sentence;
- read relevant docs and code before editing;
- make the smallest correct change;
- preserve existing architecture, naming, and style;
- validate inputs at boundaries;
- use explicit error handling and visible degraded states;
- append to `ROADMAP.md` Verification Log when state changes;
- update `BLUEPRINT.md` and `RUNBOOK.md` when the task directly touches their content;
- leave the project easier for the next agent to verify.

## Asset Workflow

When visual work needs a new asset, search for a license-safe free asset before drawing or kitbashing one locally.

Rules:

- Prefer CC0 or public domain assets. CC-BY assets are acceptable only when attribution is recorded near the imported files.
- Verify the source URL, license, author, and attribution requirements before adding files to the repo.
- Keep original downloaded asset files or source zips untouched, then derive runtime sheets or cropped sprites from them.
- Do not use copyrighted franchise screenshots, rips, AI copies of protected styles, or assets with non-commercial-only terms unless the user explicitly approves that scope.
- Match the target mood: medieval fantasy village or settlement, with classic adventure-fantasy flavor. If uncertain, default to Age of Empires-style readable RTS buildings and terrain.
- Start with these sources when relevant: OpenGameArt, Screaming Brain Studios, Summer Engine asset packs, Kenney, and other clearly licensed free game-art libraries.

## Verification And Proof

For behavior changes, use red, green, refactor:

1. Define the expected behavior.
2. Add or update a failing test when the stack supports it.
3. Run the test and confirm it fails for the expected reason.
4. Implement the smallest change.
5. Run the targeted test.
6. Run the full verification suite from `RUNBOOK.md`.

If tests are impractical, run a concrete manual check and name the specific reason.

Every completed task leaves proof in two places:

- Final response: what changed, why, risks, how verified.
- `ROADMAP.md` Verification Log: append one row when state changed.

Do not claim work is complete unless verification ran. If verification could not run, say exactly why and record the gap in `ROADMAP.md`.

## Day-One Checklist

Load only what the task requires:

- Quick fix or single-file change: read `ROADMAP.md` Current State and Current Goal.
- Feature, refactor, or unknown-scope bug: read `BLUEPRINT.md` and `ROADMAP.md`.
- Onboarding, setup, or architecture work: read `BLUEPRINT.md`, `ROADMAP.md`, and `RUNBOOK.md`.
- Any task that runs verification: also open `RUNBOOK.md` Test And Build.
- Any UI or visual work: read `VISUAL_DESIGN.md`.

Then for every task:

1. Inspect relevant files.
2. Check version-control status when available.
3. Run baseline verification when practical.
4. Implement with tests or a named manual check.
5. Append to `ROADMAP.md` Verification Log if state changed.

## Output Format

For all task completions, report:

1. What changed.
2. Why it changed.
3. Risks or side effects.
4. How it was verified.

Keep the response concise. Flag uncertainty instead of hiding it.

## What Not To Do

- Do not invent APIs, files, functions, behavior, or test results.
- Do not rewrite working systems just to make them cleaner.
- Do not broaden scope without a concrete reason.
- Do not add paid services unless the user explicitly approves them.
- Do not leave unexplained placeholder logic.
- Do not treat prior session notes or roadmap history as current truth without verifying source state.
- Do not rewrite existing rows in `ROADMAP.md`; only append new rows.
