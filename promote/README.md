<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_path: promote/README.md % -->
<!-- %ccm_git_object_id: promote/README.md@218 % -->
<!-- %ccm_git_commit_date: 2026-11-13 14:50:44 -0500 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_message: changes 261113 % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
<!-- %git_commit_history: 2026-11-09 mpegg promote: two artifacts only — manifest and record; inventory removed (D20) -->
# promote/

Promotion artifacts for this repository. The model is specified in
[`docs/design/promotion-model.md`](../docs/design/promotion-model.md); this file is the
operating instruction.

## Two artifacts, and only two

| | authored by | may contain a ref? | lives in |
|---|---|---|---|
| **manifest** — what you chose | you, by hand | **yes** | `packages/` |
| **record** — what it resolved to | `build` | **never** | `records/` |

There is **no inventory**. A committed list of everything an app owns has no consumer
here: `build` reads a manifest and nothing else. The questions an inventory used to
answer are queries over two refs:

```bash
git diff --diff-filter=D origin/prd...dev1    # what should be deleted
git diff --name-status origin/prd...dev1      # what changed at all
```

`--diff-filter=D` is the one to keep in the habit: nothing will remind you that a file
must be *removed*, and a file that is never deleted stays on the target and in its run
area forever. If a build or packaging step needs a file list, that list is an input to
that step and is expressed as a manifest like any other selection.

## Writing a manifest

```
package:  2026-11-09-docs
app:      internal-docs
from:     dev1
to:       uat1
reason:   why this selection exists, for whoever reads the record later

+ docs/design/promotion-model.md          # copy or update, identity mapping
+ wiki/ports.md -> docs/ports.md          # remapped destination
+ infra/docker/x.yml@7c77ce9              # pinned to its own commit
- memory-bank/host-deploy-runbook.md      # delete, file only
```

`from:` accepts a branch, a tag, a SHA, or `latest` — and it is the **only** place a
ref is allowed. `build` resolves it once; the record carries the commit.

Size is a style choice. Five lines is normal. Two hundred is fine when a packaging step
wants the whole list, because only real changes land: the apply writes each blob, and an
identical blob produces no diff, so a large manifest still yields a small commit.

Deliberately absent: globs, directory entries and exclude patterns. Any of the three
makes the promoted set unbounded, which destroys reproducibility and review.

## Cross-repo sources

A manifest may take a file from **another repository**. Tier branches in `from:` and `to:`
are always branches of the **target** app's repo, and every entry pins its own
`source_repo`, `source_commit` and `blob` — so a record with two sources has no single
global commit and needs none.

`app:` is not a label. It resolves through the engine's repo map in `apps.txt`, and a name
that resolves to no repository fails the build. Policy (`deny.txt`, `privileged.txt`) is
read from the **target** app's `promote/policy`, because it states what that repo may not
do; a source repo's policy does not travel with its bytes. Packages and records stay in the
target app's repo.

The model is §4.5 and §4.6 of
[`docs/design/promotion-model.md`](../docs/design/promotion-model.md). **The shipped `build`
is single-repo** — it takes one `--repo-root` — and that is an implementation limit, not the
design. Do not infer the model from the CLI.

## Building

```bash
python3 scripts/promote/tt-promote.py build \
  --repo-root . \
  --package promote/packages/2026-11-09-docs.pkg \
  --out promote/records/2026-11-09-docs.yaml
```

`--target-ref` overrides the manifest's `to:` — useful for rehearsing against a branch
that exists. `--require-change` turns an empty result into an error instead of a warning.

## What build refuses

Structural refusals are reported **together, before any ref is resolved**, so a bad
manifest is not unmasked one error at a time.

- a glob, a directory, an absolute path, or `..`
- two entries with the same destination
- a source absent at the pinned commit
- a symlink source
- a path on `policy/deny.txt`
- a privileged path without `!`, and `!` on a path that is not privileged

That last pair is bidirectional on purpose. The tool knows which prefixes are
privileged and the human must type `!`; a missing marker fails, and a stray marker also
fails, so typed approval cannot drift out of sync with the classification in either
direction.

```
+ ! .github/workflows/deploy-uat1.yml
```

## policy/

| file | job |
|---|---|
| `privileged.txt` | prefixes whose **presence** is behaviour: workflows, units, vhosts, logrotate |
| `deny.txt` | paths a manifest may never name: env files, keys, encrypted material |

They are files rather than constants so that adding a forbidden path or a new privileged
class is a diff someone can review.

`deny.txt` stops a manifest from *naming* a secret. It does not stop a secret living
inside a legitimately promoted file — that is the secret scanner's job, and the reason
`.gitignore` keeps `infra/docker/env/*.env` out of every checkout.
