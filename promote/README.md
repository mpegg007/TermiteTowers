# promote/

The promotion artifacts for this repository. The model is specified in
[`docs/design/promotion-model.md`](../docs/design/promotion-model.md); this file is the
operating instruction.

## Three artifacts, three jobs

| | authored by | may contain a ref? | changes |
|---|---|---|---|
| `inventory/` — what an app owns, one file per app | generated | no | rarely |
| `packages/` — what you chose for one promotion | **you, by hand** | **yes** | every promotion |
| `records/` — what resolved | generated from a package | **never** | every promotion |

`latest` exists only in a package. `build` resolves it once, and the record carries the
commit. A record that resolved at apply time would make the dry run meaningless and
rollback impossible.

## Authoring a package

```
package:  2026-11-09-docs
app:      termitetowers-core
from:     dev1
to:       uat1
reason:   why this package exists, for whoever reads the record later

+ docs/design/promotion-model.md              # identity mapping
+ wiki/ports.md -> docs/ports.md              # remapped destination
+ infra/docker/x.yml@7c77ce9                  # pinned to its own commit
- memory-bank/host-deploy-runbook.md          # tombstone, file only
```

`from:` accepts a branch, a tag, a SHA, or `latest`. Deliberately absent: globs,
directories and exclude patterns — any of them makes the promoted set unbounded, which
destroys reproducibility and review.

## Building

```bash
python3 scripts/promote/tt-promote.py build \
  --repo-root . \
  --package promote/packages/2026-11-09-docs.pkg \
  --out promote/records/2026-11-09-docs.yaml
```

`--target-ref` overrides the package's `to:` — use it to rehearse against an existing
branch before the real one exists. `--require-change` makes an empty result an error
rather than a warning.

## What build refuses

All structural refusals are reported **together, before any ref is resolved**, so a bad
package is not unmasked one error at a time.

- a glob, a directory, an absolute path, or `..`
- two entries with the same destination
- a source absent at the pinned commit
- a symlink source
- a path on `policy/deny.txt`
- a privileged path without `!`, and `!` on a path that is not privileged

That last pair is bidirectional on purpose. The tool knows which prefixes are
privileged and the human must type `!`; a missing marker fails, and a stray marker also
fails. Typed approval cannot drift out of sync with the classification in either
direction, which a tool-computed flag cannot guarantee.

```
+ ! .github/workflows/deploy-uat1.yml
```

## policy/

| file | job |
|---|---|
| `privileged.txt` | prefixes whose **presence** is behaviour: workflows, units, vhosts, logrotate |
| `deny.txt` | paths a package may never name: env files, keys, encrypted material |
| `ignore.txt` | paths excluded from the residual report |

They are files rather than constants so that adding a forbidden path or a new privileged
class is a diff someone can review.

`deny.txt` stops a package from *naming* a secret. It does not stop a secret from
living inside a legitimately promoted file — that is the secret scanner's job, and the
reason `.gitignore` keeps `infra/docker/env/*.env` out of every checkout.

## apps.txt — the ownership boundary

There are many apps in this repository, not one. `promote/apps.txt` maps each app to the
path prefixes it owns, and `inventory/` holds **one file per app**. A single inventory
covering the whole tree is not an ownership record; it is a repo snapshot with an app's
name on it, and it makes every app appear to own every other app's files.

```bash
# every app's inventory, seeded from the target so source-deleted paths stay owned
python3 scripts/promote/tt-promote.py inventory-all \
  --repo-root . --apps-file promote/apps.txt \
  --out-dir promote/inventory --ref dev1 --seed-ref origin/prd

# the global check: anything owned by no app, or by two
python3 scripts/promote/tt-promote.py coverage \
  --repo-root . --apps-file promote/apps.txt --ref dev1
```

`coverage` is the check that matters most, and it is silent when it is not run:

- **UNCOVERED** — a path belonging to no app is never promoted and, more dangerously,
  never deleted. It persists on the target forever.
- **AMBIGUOUS** — a path claimed by two apps makes ownership, and therefore deletion,
  depend on which app you happen to be promoting.

Run it against the **target** as well as the source. `memory-bank/` is the worked
example: it exists on `prd`, was retired on `dev1`, and until it was given an owner it
could not be deleted by any package.

`--seed-ref` is not optional. Ownership is a **persistent record**, not a snapshot of
one branch: a path that exists on `prd` but has been deleted from `dev1` is still owned,
and is exactly what becomes a `-` entry. Regenerating without the seed silently drops
ownership of every source-deleted path.

Each inventory carries `# tt-hooks.skip-post-commit` because a CCM header would rewrite
branch and blob fields on every commit, making the file look changed when nothing of
consequence changed.
