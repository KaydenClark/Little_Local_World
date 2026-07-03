# Local Agent Town - Claude Instructions

@AGENTS.md

Use this file only for Claude-specific workflow notes that cannot live in the
shared `AGENTS.md`. Keep shared project rules in `AGENTS.md` so Codex, Claude,
and other agents follow the same source of truth.

## Claude-Specific Notes

- `.claude/settings.json` mechanically enforces the edit scope described in
  prose in `AGENTS.md`. If you change the edit scope in one, change it in both.
- Open PRs with `gh`, targeting `integration` (never `main`) per `BRANCHING.md`.
  The owner promotes `integration -> main`.
- The frozen contract in `src/agent_town/core.py` changes only through the
  one-file-PR process, never a unilateral edit.
