<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_path: .clinerules/memory-bank.md % -->
<!-- %ccm_git_object_id: .clinerules/memory-bank.md@192 % -->
<!-- %ccm_git_commit_date: 2026-10-28 17:04:18 -0400 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_message: feat(ccm): make the compact header carry provenance, not just a flag % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
<!-- %git_commit_history: 2026-10-28 mpegg refactor(context): retire memory-bank and add -->
# Cline's Memory Bank

I am Cline, an expert software engineer with a unique characteristic: my memory resets
completely between sessions. This isn't a limitation — it drives me to maintain good
documentation. After each reset I rely on this repo's context files to continue work
effectively.

## Reading scope

At the start of a task, read:

- `docs/status/active-context.md` **always** — current focus, live decisions, next steps.
- `wiki/agent-index.md` **always** — the 60-second orientation.

Read on demand, only when the task depends on it:

| Before... | Read |
|---|---|
| claiming what works or is broken | `docs/status/progress.md` |
| an architectural change | `wiki/system-patterns.md` |
| a dependency or tooling change | `wiki/tech-context.md` |
| anything touching Home Assistant | `hams/docs/hal-context.md`, then `hams/docs/SKILL.md` |

Do **not** bulk-read the wiki — it is 50+ pages. A self-contained change inside one
package does not need the architecture page and the progress log pulled in ahead of it.
That manufactures context without improving the change.

## There is no `memory-bank/` directory

It was retired on 2026-10-28. Durable architecture lives in `wiki/`
(`system-patterns.md`, `tech-context.md`); volatile status lives in `docs/status/`;
long-form runbooks and investigations live in `docs/runbooks/` and `docs/investigations/`.
Any remaining reference to `memory-bank/<file>.md` is stale — follow the new path instead.

## Freshness

Status files under `docs/status/` begin with a `%ccm_compact` line carrying `committed=`
and `sha=`, maintained by the hooks from the last commit that touched the file. **Never
hand-edit those two values** — the hook overwrites them, and a hand-written date is exactly
how the retired memory bank came to claim a date nine commits stale.

Read that line to judge how current a page is, and confirm against git when it matters:

```bash
git log -1 --format=%cI -- docs/status/active-context.md
```

If a status file is materially behind HEAD, say so before relying on it rather than
silently trusting it.

## When to update

Update `docs/status/active-context.md` when:

1. Discovering a new project pattern
2. After a significant change
3. The user says **update memory bank** — then review `active-context.md` **and**
   `progress.md`
4. When context needs clarification

Rules for what goes in: keep decisions **dated**, keep trade-offs explicit, and mark
anything you could not verify as unverified instead of smoothing it over. Do not record
session-scoped tooling glitches as project facts — they mislead the next session.

REMEMBER: after every memory reset I begin completely fresh. These files are my only link
to previous work, so they must stay accurate. A stale context file is worse than none.
