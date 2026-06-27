# Little Local World - Runbook

**Last reviewed:** 2026-06-27
**Runtime owner:** Kayden
**Environment:** local desktop

This file explains how to operate and verify the project during the colony-builder refactor.

## Prerequisites

Required tools on this checkout:

- Python 3.11 or newer.
- A local virtual environment at `.venv`.
- Pygame installed inside `.venv`.
- PowerShell 7 or newer for `scripts/validate-workbench.ps1`.

Optional local services:

- A local OpenAI-compatible LLM server such as LM Studio or Ollama.

Required accounts or hosted services:

- None.

## Environment Configuration

No `.env` file is required for the base deterministic simulation.

Required variables:

| Variable | Purpose | Secret | Example or notes |
|---|---|---|---|
| `SDL_VIDEODRIVER` | Optional Pygame smoke-test override | no | `dummy`, set automatically by `--smoke-test` |

Optional local model variables:

| Variable | Purpose | Secret | Example or notes |
|---|---|---|---|
| `AGENT_TOWN_LLM_MODEL` | Optional explicit local model override | no | `google/gemma-4-e4b`, or the exact model id loaded in LM Studio or Ollama |
| `AGENT_TOWN_LLM_BASE_URL` | OpenAI-compatible local endpoint | no | `http://localhost:1234/v1` for LM Studio, `http://localhost:11434/v1` for Ollama |
| `AGENT_TOWN_LLM_TIMEOUT` | Per-request timeout in seconds | no | default `4.0` |
| `AGENT_TOWN_LLM_MAX_TOKENS` | Max tokens for compact decision JSON | no | default `180` |
| `AGENT_TOWN_LLM_AUTO_DISCOVER` | Controls startup model discovery when no model is set | no | default `1`; set `0` for deterministic non-LLM runs |

Rules:

- Do not commit real `.env` files, tokens, local databases, logs, or private data.
- Keep local model use local-only.
- The LLM layer must fall back to deterministic behavior on unavailable, slow, or invalid model output.

## Install

On this macOS checkout, verify the existing environment:

```bash
./.venv/bin/python --version
./.venv/bin/python -m pip show pygame
```

If the venv is missing, recreate it with Python 3.11 or newer and install the package in editable mode:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -e .
```

Windows launch/setup scripts still exist:

```powershell
.\setup.ps1
```

## Run Locally

Current smoke path:

```bash
./.venv/bin/python -m agent_town --smoke-test
```

Interactive desktop viewer:

```bash
./.venv/bin/agent-town
```

Windows launcher paths still exist:

```powershell
.\run.ps1
```

```text
Launch Local Agent Town.cmd
```

Expected current result:

- The legacy Pygame viewer opens and exits for the smoke test.
- Existing social-sim viewer behavior remains available until the colony state is wired in integration.
- The viewer is not yet the source of truth for colony-builder behavior.

## Test And Build

Targeted Phase 0 contract test:

```bash
./.venv/bin/python -m unittest tests.test_colony_contract
```

Fast check:

```bash
./.venv/bin/python -m unittest discover -s tests
```

Workbench validation:

```bash
pwsh -File scripts/validate-workbench.ps1
```

Full verification:

```bash
./.venv/bin/python -m unittest discover -s tests
./.venv/bin/python -m agent_town --smoke-test
pwsh -File scripts/validate-workbench.ps1
```

Expected result:

- Core and contract tests pass.
- Pygame smoke test exits without import or display errors.
- Workbench validation passes.

Scale benchmarks from the old prototype are not a Build 1 priority. Do not use scale benchmark results to justify architecture changes before the 12-pawn economy and Governor loop exist.

## Data Operations

SQLite snapshot helpers still exist for tests and future tools:

- `agent_town.persistence.save_snapshot(path, sim)` writes serializable simulation state and replay events.
- `agent_town.persistence.load_snapshot(path, snapshot_id)` reads a `WorldState`.
- `agent_town.persistence.load_simulation(path, snapshot_id)` restores a `Simulation`.

Current rule:

- Treat the old snapshot helper as dormant for Build 1 unless a later task explicitly repoints it to the colony state.

Safety rules:

- Do not store snapshots in committed paths.
- Do not store real private data in pawn memories, Governor context, or model logs without explicit approval.
- Do not persist Pygame surfaces, raw model prompts, model credentials, or renderer objects.

## Deployment Or Startup

There is no deployment target. The project runs locally on the desktop.

Do not add hosted deployment, browser runtime, telemetry, or external persistence without explicit approval.

## Troubleshooting

| Symptom | Likely cause | Check | Fix |
|---|---|---|---|
| `ModuleNotFoundError: agent_town` | Running system Python instead of the venv | `./.venv/bin/python --version` | Use `./.venv/bin/python`, or reinstall with `./.venv/bin/python -m pip install -e .` |
| `ModuleNotFoundError: pygame` | Pygame missing from the active interpreter | `./.venv/bin/python -m pip show pygame` | Install through the venv |
| Smoke test does not open | Display or Pygame issue | `./.venv/bin/python -m agent_town --smoke-test` | Reinstall dependencies and retry with `SDL_VIDEODRIVER=dummy` |
| Colony behavior raises `NotImplementedError` | Phase 0 stubs are being called before Track A or Track B is implemented | Read the exception message | Implement the named milestone with a failing test first |
| Local model shows disabled or offline | No local model is configured or running | Check `AGENT_TOWN_LLM_MODEL` and `AGENT_TOWN_LLM_BASE_URL` | Start LM Studio or Ollama, or leave deterministic fallback active |
| Workbench validation fails | Required docs missing headings or unresolved placeholders | `pwsh -File scripts/validate-workbench.ps1` | Update the named doc and rerun validation |

## Recovery And Rollback

If a change fails:

1. Identify the touched files and the failing command.
2. Revert only the smallest change needed, preserving user work.
3. Rerun the failing verification command.
4. Append the result to `ROADMAP.md` if durable state changed.

Do not delete data, reset repositories, rewrite history, or rotate secrets unless the user explicitly approves that action.

## Operational Proof

If a command in this runbook changed durable project state, append a row to the `ROADMAP.md` Verification Log. For routine local runs that do not change state, a final response note is enough.
