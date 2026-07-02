# Branching Methodology

This repo uses a three-tier branch model so that many automated agents (Claude,
Codex, and future ones) can work in parallel without turning the branch list into
a graveyard, and so cleanup never feels like it destroys evidence.

## The three tiers

```
feature branches   →   integration (the "root")   →   main
codex/<task>           agents branch FROM and          only Kayden merges here
claude/<task>          merge BACK INTO integration     promote integration → main
feat/<slice>           via pull request                = a watched, known-good state
docs/<thing>
fix/<thing>
```

- **`main`** — stable and human-owned. Only Kayden merges into it, and only from
  `integration`. Every commit on `main` represents a state that has actually been
  watched running (see the "watchability is part of done" rule). Agents never
  target `main` directly.

- **`integration`** — the shared trunk (the "root" Kayden asked for). Every agent
  forks from it and merges back into it. It accumulates all in-flight work between
  promotions to `main`. **Deleting a spent feature branch never loses history,
  because its commits are preserved inside `integration`'s merge history.** This is
  the branch Kayden reviews and promotes in batches.

- **feature branches** — one per task, short-lived. Branched from `integration`,
  merged back into `integration` via PR, then deleted once merged.

## Naming

| Prefix         | Use                                              |
| -------------- | ------------------------------------------------ |
| `codex/<task>` | work done by the Codex agent                     |
| `claude/<task>`| work done by the Claude agent                    |
| `feat/<slice>` | a product slice / feature (either agent or human)|
| `fix/<thing>`  | a targeted bug fix                               |
| `docs/<thing>` | docs-only changes                                |

Keep the `<task>` slug short, kebab-case, and specific: `codex/water-need`,
`feat/slice2-market`, not `codex/stuff`.

## Lifecycle

**Starting work (every agent, every task):**

```bash
git fetch origin
git switch integration
git pull --ff-only            # get the latest root
git switch -c codex/<task>    # fork a feature branch
```

**Finishing work:**

```bash
git push -u origin codex/<task>
# open a pull request whose BASE is `integration` (never `main`)
```

Merge the PR into `integration` with a **merge commit** (do not squash). The merge
commit is what preserves the per-task shape of the history — that is the "evidence"
Kayden does not want flattened away. After the merge, delete the feature branch
(local and remote); its commits live on inside `integration`.

**Promotion (Kayden only):**

When a batch of work on `integration` has been watched and is good, Kayden merges
`integration → main`. Squash-vs-merge for this promotion is Kayden's call; the
default is a normal merge so `main` shows which integration batch it came from.

## Cleanup rules

- A feature branch **merged into `integration`** is safe to delete immediately.
- A branch **merged into `main`** is safe to delete from both local and remote; its
  commits are permanently in `main`'s history.
- Never delete `main` or `integration`.
- Never force-push `main` or `integration`.
- When in doubt about whether a branch is dead, check
  `git branch --merged integration` and `git branch --merged main`. Anything listed
  there is prunable. Anything under `--no-merged` still holds unique commits — keep
  it or rebase it onto `integration` before merging.

## Why this shape

The failure mode we are fixing: dozens of branches forked from different points,
never converging, so the only "safe" place to look was `main` — and pruning
anything felt like erasing work. With a single `integration` root:

- every agent has one current base to fork from and one place to converge;
- history is never lost on delete, because it is captured in `integration`'s merges;
- `main` stays a clean record of watched-good states, promoted in deliberate batches.
