# `.claude/settings.json` - mechanical scope enforcement

`AGENTS.md` describes the edit scope in prose (honor system). This file makes
the boundary mechanical for Claude Code: the harness enforces it instead of
trusting the agent to remember. Other agents still read `AGENTS.md`; this is
the belt to that suspenders.

| Scope idea (from `AGENTS.md`) | Bucket | Effect |
|---|---|---|
| Writable roots (`src/agent_town/`, `tests/`, `scripts/`, `docs/`, control docs incl. `BRANCHING.md`) | `allow` | edits run without a prompt |
| Forbidden paths (secrets, `.venv/`, `logs/`, `saves/`, build output, asset zips) | `deny` | hard-blocked; takes precedence over `allow` |
| Requires review (`git push`, `rm -rf`, `core.py` frozen contract, dependency manifests, `research_papers/`) | `ask` | pauses for owner confirmation |

Notes:

- `deny` wins over `allow`, so the secret/build rules hold even when a broad
  `allow` glob would otherwise match.
- `core.py`, `pyproject.toml`, `requirements.txt`, and `research_papers/` are in
  `ask` because they carry the frozen-contract, dependency, and design-input
  boundaries `AGENTS.md` calls out.
- `saves/` holds local autosave state (`save.py`); it is denied the same way as
  `logs/` so an agent cannot silently overwrite the owner's running civilization.
- The `Bash(...)` allow entries assume `PYTHONPATH=src` and the project venv;
  see `RUNBOOK.md` for the exact per-platform invocation.
- Delete this file if the project stops using Claude Code; the prose scope in
  `AGENTS.md` remains the source of truth for every agent.
