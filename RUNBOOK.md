# Local Agent Town - Runbook

**Last reviewed:** 2026-06-28
**Runtime owner:** Kayden  
**Environment:** local desktop

This file explains how to operate the project.

## Prerequisites

Required tools:

- Windows PowerShell.
- Python 3.11 or newer.

Required accounts or services:

- None for the base prototype.
- Optional: a local OpenAI-compatible LLM server such as LM Studio or Ollama.

Required local files:

- None before setup. `setup.ps1` creates `.venv`.

## Environment Configuration

No `.env` file is required for the base prototype.

Required variables:

| Variable | Purpose | Secret | Example or notes |
|---|---|---|---|
| `SDL_VIDEODRIVER` | Optional Pygame smoke-test override | no | `dummy`, set automatically by `--smoke-test` |

Optional local model variables:

| Variable | Purpose | Secret | Example or notes |
|---|---|---|---|
| `AGENT_TOWN_LLM_MODEL` | Optional explicit model override | no | `google/gemma-4-e4b`, or the exact model id loaded in LM Studio/Ollama |
| `AGENT_TOWN_LLM_BASE_URL` | OpenAI-compatible local endpoint | no | `http://localhost:1234/v1` for LM Studio, `http://localhost:11434/v1` for Ollama |
| `AGENT_TOWN_LLM_TIMEOUT` | Per-request timeout in seconds | no | default `4.0` |
| `AGENT_TOWN_LLM_MAX_TOKENS` | Max tokens for compact decision JSON | no | default `180` |
| `AGENT_TOWN_LLM_AUTO_DISCOVER` | Controls startup model discovery when no model is set | no | default `1`; set `0` to keep local model disabled unless `AGENT_TOWN_LLM_MODEL` is set |

Rules:

- Do not commit real `.env` files, tokens, local databases, logs, or private data.
- Keep future LLM provider credentials local-only.
- Prefer a visible degraded state over fake external data when a future provider is unavailable.
- If no model variable is set, the app briefly checks the configured `/models` endpoint and selects the first non-embedding local model it finds.

## Install

```powershell
.\setup.ps1
```

Expected result:

- `.venv` exists.
- The package installs editable into `.venv`.
- Pygame is available inside `.venv`.

## Asset Preparation

The colony viewer uses runtime sprites under `src\agent_town\assets\colony`.

When adding a new free asset:

- Verify the source URL, license, author, and attribution requirements before download.
- Prefer CC0 or public domain. Use CC-BY only when attribution is recorded next to the imported files.
- Keep the original download or source zip untouched and generate runtime files from it.
- Update nearby asset notes and asset tests when the runtime asset set changes.
- If no license-safe asset fits, use the smallest temporary placeholder and record that it should be replaced.

## Run Locally

```powershell
.\run.ps1
```

Double-click launcher:

```text
Launch Local Agent Town.cmd
```

Open:

- A local Pygame desktop window titled `Local Agent Town`.

Expected result:

- A colony map appears.
- The engine advances simulated hours over time.
- Colony sprites appear for terrain, buildings, resources, and pawns.
- The desktop window is resizable.
- In-map overlays show colonist portraits, names, mood dots, selected-pawn
  details, colony resources, and command buttons.
- Mouse wheel, `+`, and `-` zoom.
- `WASD` or arrow keys pan.
- Clicking a pawn, or pressing `Tab`, updates the pawn sheet with status,
  assignment, needs, skills, and traits.
- Pressing `L` connects to or disconnects from LM Studio/Ollama while the game is running.
- The footer shows local model state: disabled, idle, thinking, offline, or invalid.
- The in-map command strip is a visual placeholder in the current build. The
  `Architect`, `Work`, `Assign`, `Research`, `History`, and `Menu` buttons do
  not perform actions yet.

## Test And Build

Workbench validation:

```powershell
.\scripts\validate-workbench.ps1
```

Fast check:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Full verification:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m agent_town --smoke-test
.\scripts\validate-workbench.ps1
```

Expected result:

- Core tests pass.
- Smoke test exits without import or display errors.
- Workbench validation passes.
- Asset checks prove the colony runtime sprites and provenance notes exist.

Scaling benchmark:

```powershell
.\.venv\Scripts\python.exe .\scripts\benchmark_scaling.py --agents 100 500 1000
```

Expected result:

- A CSV-style table reports engine step time, governor context build time, dummy draw time, final applied action count, and completed-building count.
- Use this before increasing default population size or deciding whether Pygame is the scaling blocker.

## Data Operations

There is no colony save/load UI or persistence model yet.

Safety rules:

- Do not wire persistent local databases into automatic viewer behavior without updating `BLUEPRINT.md`, `RUNBOOK.md`, and tests.
- Do not store real private data in future pawn or governor memory unless the user explicitly approves that use.

## Deployment Or Startup

There is no deployment target. The project runs locally through PowerShell.

## Troubleshooting

| Symptom | Likely cause | Check | Fix |
|---|---|---|---|
| `ModuleNotFoundError: pygame` | Setup was not run or wrong Python is being used | `.\.venv\Scripts\python.exe -c "import pygame"` | Run `.\setup.ps1` |
| Double-click does nothing visible | Windows did not execute the PowerShell script directly | Open `Launch Local Agent Town.cmd` | Use the `.cmd` launcher, which calls the PowerShell launcher with the right policy |
| Window does not open | Display or Pygame issue | `.\.venv\Scripts\python.exe -m agent_town --smoke-test` | Reinstall through `.\setup.ps1`; check local graphics environment |
| Local model shows disabled | The in-game toggle is off, no local chat model was found, or `AGENT_TOWN_LLM_AUTO_DISCOVER=0` | Inspect the HUD governor row | Start LM Studio/Ollama, load a model, then press `L`; or set `AGENT_TOWN_LLM_MODEL` exactly as the local server expects it |
| Local model shows offline | LM Studio/Ollama server is not running or URL is wrong | Check `AGENT_TOWN_LLM_BASE_URL` | Start the local server or change the URL |
| Local model shows invalid reply | Model returned malformed JSON, unknown action, or the server rejected the request payload | Inspect the HUD governor row | Use a smaller/faster instruct model and keep max tokens low |
| Workbench validation fails | Required docs missing headings or unresolved placeholders | `.\scripts\validate-workbench.ps1` | Update the named doc and rerun validation |

## Recovery And Rollback

If a change fails:

1. Identify the touched files and the failing command.
2. Revert only the smallest change needed, preserving user work.
3. Rerun the failing verification command.
4. Append the result to `ROADMAP.md` if durable state changed.

Do not delete data, reset repositories, rewrite history, or rotate secrets unless the user explicitly approves that action.

## Operational Proof

If a command in this runbook changed durable project state, append a row to the `ROADMAP.md` Verification Log. For routine local runs that do not change state, a final response note is enough.
